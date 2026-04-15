from __future__ import annotations

import json
import time
import traceback
from pathlib import Path

from langgraph.types import interrupt

from app.core.config import OUTPUT_DIR, REPORT_DIR
from app.runtime.artifacts import normalize_artifacts
from app.runtime.executor import ExecutionRuntime
from app.runtime.llm import get_llm
from app.schemas.critic import CriticResult
from app.schemas.error_analysis import ErrorAnalysis
from app.schemas.plan import AnalysisPlan
from app.schemas.report import AnalysisReport
from app.schemas.schema_profile import SchemaProfile
from app.schemas.tool_selection import ToolSelection
from app.tools.registry import ToolRegistry

llm = get_llm(temperature=0)
runtime = ExecutionRuntime(output_dir=str(OUTPUT_DIR))
tool_registry = ToolRegistry()


def add_history(state: dict, msg: str) -> list[str]:
    history = list(state.get("history", []))
    history.append(msg)
    return history


def format_traceback(e: Exception) -> str:
    return "".join(traceback.format_exception(type(e), e, e.__traceback__))


def _strip_code_fence(text: str) -> str:
    content = text.strip()
    if content.startswith("```"):
        content = content.replace("```json", "")
        content = content.replace("```python", "")
        content = content.replace("```", "")
        content = content.strip()
    return content


def _extract_json_object(text: str) -> str:
    """
    从模型输出里提取最外层 JSON 对象。
    适合模型前后多说几句的情况。
    """
    content = _strip_code_fence(text)

    start = content.find("{")
    end = content.rfind("}")

    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"未找到可解析 JSON 对象。原始输出：\n{content}")

    return content[start:end + 1]


def _safe_json_loads(text: str, node_name: str) -> dict:
    """
    先直接 loads；失败后再抽取最外层 JSON。
    """
    raw = text.strip()

    try:
        return json.loads(_strip_code_fence(raw))
    except json.JSONDecodeError:
        pass

    try:
        extracted = _extract_json_object(raw)
        return json.loads(extracted)
    except Exception as e:
        raise ValueError(
            f"[{node_name}] JSON 解析失败。\n"
            f"原始输出如下：\n{raw}\n\n"
            f"解析异常：{repr(e)}"
        )


def _invoke_json_with_retry(prompt: str, node_name: str, max_attempts: int = 2) -> dict:
    """
    第一次正常要求 JSON；
    若解析失败，第二次强约束只输出合法 JSON。
    """
    last_raw = None
    last_err = None
    current_prompt = prompt

    for _attempt in range(1, max_attempts + 1):
        resp = llm.invoke(current_prompt)
        last_raw = resp.content

        try:
            return _safe_json_loads(last_raw, node_name)
        except Exception as e:
            last_err = e
            current_prompt = (
                prompt
                + "\n\n重要：你上一次输出不是合法 JSON。"
                  "这一次只允许输出一个合法 JSON 对象，不要输出任何解释、前后缀、Markdown 代码块。"
            )

    raise ValueError(
        f"[{node_name}] 连续 {max_attempts} 次未输出合法 JSON。\n"
        f"最后一次原始输出：\n{last_raw}\n\n"
        f"最后异常：{repr(last_err)}"
    )


def schema_inspector_node(state: dict) -> dict:
    file_tool = tool_registry.get("file_tool")
    stats_tool = tool_registry.get("stats_tool")

    df = file_tool.run(file_path=state["file_path"])
    basic_stats = stats_tool.run(df=df)

    prompt = f"""
你是一个数据结构分析器。
请根据下面数据摘要，只输出合法 JSON，不要输出任何解释。

数据摘要：
{json.dumps(basic_stats, ensure_ascii=False, indent=2)}

输出格式：
{{
  "columns": [...],
  "dtypes": {{...}},
  "shape": [rows, cols],
  "date_columns": [...],
  "numeric_columns": [...],
  "categorical_columns": [...],
  "missing_summary": {{...}},
  "column_aliases": {{...}},
  "observations": [...]
}}
"""

    profile_data = _invoke_json_with_retry(prompt, "schema_inspector")
    profile = SchemaProfile(**profile_data)

    return {
        "schema_profile": profile.model_dump(),
        "history": add_history(state, "[schema_inspector] 已完成数据结构分析"),
    }


def planner_node(state: dict) -> dict:
    prompt = f"""
你是资深数据分析规划器。
请只输出合法 JSON，不要输出任何解释。

用户需求：
{state["input"]}

schema profile:
{json.dumps(state["schema_profile"], ensure_ascii=False, indent=2)}

输出格式：
{{
  "objective": "...",
  "steps": ["..."],
  "expected_outputs": ["..."],
  "libraries": ["..."],
  "risk_notes": ["..."],
  "save_plot_as": "analysis.png",
  "selected_tools": ["file_tool", "python_tool"]
}}
"""

    plan_data = _invoke_json_with_retry(prompt, "planner")
    plan = AnalysisPlan(**plan_data)

    return {
        "plan": plan.model_dump(),
        "selected_tools": plan.selected_tools,
        "history": add_history(state, "[planner] 已生成分析计划"),
    }


def tool_selector_node(state: dict) -> dict:
    prompt = f"""
你是工具路由器。
请只输出合法 JSON，不要输出任何解释。

用户需求：
{state["input"]}

分析计划：
{json.dumps(state["plan"], ensure_ascii=False, indent=2)}

可用工具：
{json.dumps(tool_registry.list_tools(), ensure_ascii=False, indent=2)}

输出格式：
{{
  "selected_tools": ["file_tool", "python_tool", "chart_tool"],
  "rationale": ["..."],
  "execution_mode": "local"
}}
"""

    tool_plan_data = _invoke_json_with_retry(prompt, "tool_selector")
    tool_plan = ToolSelection(**tool_plan_data)

    return {
        "tool_plan": tool_plan.model_dump(),
        "selected_tools": tool_plan.selected_tools,
        "execution_mode": tool_plan.execution_mode,
        "history": add_history(state, "[tool_selector] 已完成工具选择"),
    }


def coder_node(state: dict) -> dict:
    retries = state.get("retries", 0)
    error_text = state.get("error", "")
    error_analysis = state.get("error_analysis", {})
    force_first_error = state.get("force_first_error", False)

    prompt = f"""
你是 Python 数据分析工程师。
请输出可直接执行的纯 Python 代码，不要 Markdown。

用户需求：
{state["input"]}

schema profile:
{json.dumps(state.get("schema_profile", {}), ensure_ascii=False, indent=2)}

分析计划：
{json.dumps(state.get("plan", {}), ensure_ascii=False, indent=2)}

工具计划：
{json.dumps(state.get("tool_plan", {}), ensure_ascii=False, indent=2)}

上次错误：
{error_text if error_text else "无"}

错误分析：
{json.dumps(error_analysis, ensure_ascii=False, indent=2) if error_analysis else "无"}

要求：
1. 数据已在变量 df 中
2. 可使用 pd / plt / OUTPUT_DIR
3. 不要重新定义或覆盖 OUTPUT_DIR
4. 保存文件时直接使用运行环境提供的 OUTPUT_DIR
5. 路径写法示例：
   plot_path = OUTPUT_DIR / "analysis.png"
6. 若涉及日期，请先 parse 再排序
7. 代码必须尽量鲁棒，兼容中英文列名
8. 若有错误分析，必须根据 fix_hint 修复
9. 若产生图表，必须保存到 OUTPUT_DIR，并把路径放入 artifacts
10. summary 必须具体，不要写“分析已完成”这种空话，必须包含：
   - 分析对象
   - 关键结论
   - 至少一个具体数字、排名或趋势描述
11. findings 必须是 2 到 5 条字符串列表，每条都要具体
12. metrics 必须尽量具体，至少包含：
   - source_row_count
   - source_column_count
   - derived_row_count
   - derived_column_count
   - task_type
   - 至少 2 个与任务相关的关键统计量
13. source_* 表示原始输入数据 df 的规模
14. derived_* 表示处理中间数据的规模
15. 不要用 try/except 吞掉异常后直接返回失败 result
16. 如果发生异常，必须 raise 重新抛出，让执行器捕获 traceback
17. 只有在分析真正成功完成时，才允许设置 result
18. 不要生成“分析失败：...”这类兜底 result
19. 不要在代码里捕获顶层 Exception 后静默失败
20. 尽量不要重复 import 已经由运行环境提供的 pd、plt、OUTPUT_DIR
21. 请特别避免：
   - 使用未定义变量
   - 在 for 循环外错误引用循环内部变量
   - 覆盖运行环境提供的变量
22.绘图前请设置：
    -plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    -plt.rcParams["axes.unicode_minus"] = False
22. 最终必须设置：
result = {{
  "summary": "...",
  "findings": ["...", "..."],
  "artifacts": ["..."],
  "metrics": {{
    "source_row_count": 0,
    "source_column_count": 0,
    "derived_row_count": 0,
    "derived_column_count": 0,
    "task_type": "...",
    "...": "..."
  }}
}}
"""

    if force_first_error and retries == 0:
        prompt += "\n附加演示要求：第一版故意使用不存在列 sale_amount。"

    resp = llm.invoke(prompt)
    code = _strip_code_fence(resp.content)

    # 防止模型覆盖运行时提供的 OUTPUT_DIR
    code = code.replace('OUTPUT_DIR = "output"', '# OUTPUT_DIR provided by runtime')
    code = code.replace("OUTPUT_DIR = 'output'", "# OUTPUT_DIR provided by runtime")

    # 为了稳定演示自愈，首轮程序化注入一个确定会报错的列名
    if force_first_error and retries == 0:
        bug_injected = False

        replacements = [
            ("['sales']", "['sale_amount']"),
            ('["sales"]', '["sale_amount"]'),
            ("['date']", "['date_typo_for_demo']"),
            ('["date"]', '["date_typo_for_demo"]'),
        ]

        for old, new in replacements:
            if old in code:
                code = code.replace(old, new, 1)
                bug_injected = True
                break

        if not bug_injected:
            forced_bug = '\n# forced demo bug\n_ = df["sale_amount"]\n'
            if "result =" in code:
                idx = code.rfind("result =")
                code = code[:idx] + forced_bug + code[idx:]
            else:
                code += forced_bug

    return {
        "code": code,
        "history": add_history(state, f"[coder] 已生成代码，第 {retries + 1} 次尝试"),
    }


def critic_node(state: dict) -> dict:
    prompt = f"""
你是代码审查器。
请只输出合法 JSON，不要输出任何解释。

分析计划：
{json.dumps(state.get("plan", {}), ensure_ascii=False, indent=2)}

schema profile:
{json.dumps(state.get("schema_profile", {}), ensure_ascii=False, indent=2)}

代码：
{state["code"]}

请特别检查：
1. 是否引用了未定义变量
2. 是否在 for 循环外错误使用了循环内变量
3. 是否存在“except 后直接返回失败 result”而不是 raise
4. 是否覆盖了运行环境提供的变量（如 OUTPUT_DIR）
5. 是否与分析计划一致
6. 是否大概率可执行

输出格式：
{{
  "is_safe": true,
  "is_consistent_with_plan": true,
  "is_executable_likely": true,
  "issues": [],
  "suggestions": [],
  "should_rewrite": false
}}
"""

    critic_data = _invoke_json_with_retry(prompt, "critic")
    critic = CriticResult(**critic_data)

    critic_rewrites = state.get("critic_rewrites", 0)
    max_critic_rewrites = state.get("max_critic_rewrites", 2)

    updates = {
        "critic_result": critic.model_dump(),
        "history": add_history(state, "[critic] 已完成代码自检"),
    }

    if critic.should_rewrite:
        critic_rewrites += 1
        updates["critic_rewrites"] = critic_rewrites
        updates["error"] = "Critic suggested rewrite before execution."

        if critic_rewrites >= max_critic_rewrites:
            forced_critic_result = critic.model_dump()
            forced_critic_result["should_rewrite"] = False
            forced_critic_result["issues"] = forced_critic_result.get("issues", []) + [
                f"达到 critic 重写上限 {max_critic_rewrites}，停止自动重写。"
            ]
            updates["critic_result"] = forced_critic_result
            updates["history"] = add_history(
                state,
                f"[critic] 达到最大重写次数 {max_critic_rewrites}，停止继续打回 coder"
            )

    return updates


def review_node(state: dict) -> dict:
    if not state.get("review_required", True):
        return {
            "approved": True,
            "history": add_history(state, "[review] 已跳过人工审核"),
        }

    decision = interrupt({
        "type": "code_review",
        "message": "请审核代码。你可以 approve/reject，也可以编辑代码后继续。",
        "code": state["code"],
        "critic_result": state.get("critic_result", {}),
    })

    approved = bool(decision.get("approved", False))
    edited_code = decision.get("edited_code")

    update = {
        "approved": approved,
        "review_decision": decision,
        "history": add_history(
            state,
            f"[review] 人工审核结果: {'通过' if approved else '拒绝'}"
        ),
    }

    if approved and edited_code:
        update["code"] = edited_code

    return update


def executor_node(state: dict) -> dict:
    if not state.get("approved", False):
        return {
            "error": "代码未通过人工审核，未执行。",
            "finished": True,
            "history": add_history(state, "[executor] 审核未通过，任务终止"),
        }

    start = time.time()

    try:
        result = runtime.run_code(
            code=state["code"],
            file_path=state["file_path"],
            execution_mode=state.get("execution_mode", "local"),
        )

        # 兜底，避免 report_generator 太空
        if "summary" not in result:
            result["summary"] = "分析已完成，但未提供详细 summary。"

        if "findings" not in result or not isinstance(result.get("findings"), list):
            result["findings"] = []

        if "metrics" not in result or not isinstance(result.get("metrics"), dict):
            result["metrics"] = {}

        # 统一补充源数据规模
        try:
            file_tool = tool_registry.get("file_tool")
            source_df = file_tool.run(file_path=state["file_path"])
            result["metrics"].setdefault("source_row_count", int(len(source_df)))
            result["metrics"].setdefault("source_column_count", int(len(source_df.columns)))
        except Exception:
            pass

        # 检查是否是“伪成功”结果：代码内部吞掉了异常，只返回失败版 result
        summary_text = str(result.get("summary", "")).strip().lower()
        metrics_dict = result.get("metrics", {}) if isinstance(result.get("metrics", {}), dict) else {}
        findings_list = result.get("findings", []) if isinstance(result.get("findings", []), list) else []

        looks_like_failure = False
        failure_signals = [
            "分析失败",
            "failed",
            "error",
            "异常",
        ]

        if any(sig in summary_text for sig in failure_signals):
            looks_like_failure = True

        if "error" in metrics_dict:
            looks_like_failure = True

        if findings_list and any(("错误" in str(x) or "失败" in str(x)) for x in findings_list):
            looks_like_failure = True

        if looks_like_failure:
            raise RuntimeError(
                "Generated code returned a failure-shaped result instead of raising an exception. "
                f"summary={result.get('summary', '')}, metrics={metrics_dict}"
            )

        elapsed = time.time() - start
        artifacts = normalize_artifacts(result.get("artifacts", []))
        metrics = dict(state.get("metrics", {}))
        metrics.update({
            "last_run_seconds": elapsed,
            "retries": state.get("retries", 0),
            "success": True,
            "execution_mode": state.get("execution_mode", "local"),
        })

        return {
            "output": result,
            "artifacts": artifacts,
            "metrics": metrics,
            "error": "",
            "error_analysis": {},
            "critic_rewrites": 0,
            "finished": True,
            "history": add_history(state, "[executor] 执行成功"),
        }

    except Exception as e:
        elapsed = time.time() - start
        metrics = dict(state.get("metrics", {}))
        metrics.update({
            "last_run_seconds": elapsed,
            "retries": state.get("retries", 0) + 1,
            "success": False,
            "execution_mode": state.get("execution_mode", "local"),
        })

        return {
            "error": format_traceback(e),
            "metrics": metrics,
            "retries": state.get("retries", 0) + 1,
            "finished": False,
            "history": add_history(state, "[executor] 执行失败，已写入 traceback"),
        }


def error_analyzer_node(state: dict) -> dict:
    prompt = f"""
你是 Python 执行错误分析器。
请只输出合法 JSON，不要输出任何解释。

schema profile:
{json.dumps(state.get("schema_profile", {}), ensure_ascii=False, indent=2)}

traceback:
{state.get("error", "")}

输出格式：
{{
  "error_type": "COLUMN_NOT_FOUND",
  "root_cause": "...",
  "fix_hint": "...",
  "recoverable": true
}}
"""

    analysis_data = _invoke_json_with_retry(prompt, "error_analyzer")
    analysis = ErrorAnalysis(**analysis_data)

    return {
        "error_analysis": analysis.model_dump(),
        "history": add_history(
            state,
            f"[error_analyzer] 已分析错误: {analysis.error_type}"
        ),
    }


def report_generator_node(state: dict) -> dict:
    output_data = state.get("output", {})

    prompt = f"""
你是数据分析报告生成器。
请只输出合法 JSON，不要输出任何解释。

用户需求：
{state["input"]}

分析计划：
{json.dumps(state.get("plan", {}), ensure_ascii=False, indent=2)}

执行输出：
{json.dumps(output_data, ensure_ascii=False, indent=2)}

要求：
1. 必须优先依据 output 中的 summary、findings、metrics 写报告
2. key_findings 必须具体，不要写空泛结论
3. dataset_summary 里要包含数据规模信息，如 source_row_count / source_column_count
4. 如果有图表产物，artifacts 必须引用
5. limitations 至少写 1 条真实限制
6. next_steps 至少写 2 条可执行建议

输出格式：
{{
  "title": "...",
  "objective": "...",
  "dataset_summary": "...",
  "methodology": ["..."],
  "key_findings": ["..."],
  "artifacts": ["..."],
  "limitations": ["..."],
  "next_steps": ["...", "..."]
}}
"""

    report_data = _invoke_json_with_retry(prompt, "report_generator")
    report = AnalysisReport(**report_data)

    raw_findings = output_data.get("findings", [])
    if raw_findings and len(report.key_findings) < 2:
        report.key_findings = raw_findings[:5]

    raw_metrics = output_data.get("metrics", {})
    if raw_metrics:
        preferred_order = [
            "source_row_count",
            "source_column_count",
            "derived_row_count",
            "derived_column_count",
            "task_type",
            "total_sales",
            "avg_monthly_sales",
            "months_analyzed",
            "month_count",
            "product_count",
        ]

        ordered_metric_lines = []
        used_keys = set()

        for key in preferred_order:
            if key in raw_metrics:
                ordered_metric_lines.append(f"{key}: {raw_metrics[key]}")
                used_keys.add(key)

        for k, v in raw_metrics.items():
            if k not in used_keys:
                ordered_metric_lines.append(f"{k}: {v}")

        if report.dataset_summary:
            report.dataset_summary += "\n\nMetrics:\n" + "\n".join(ordered_metric_lines[:10])

    md = f"# {report.title}\n\n"
    md += f"## Objective\n{report.objective}\n\n"
    md += f"## Dataset Summary\n{report.dataset_summary}\n\n"
    md += "## Methodology\n" + "\n".join([f"- {x}" for x in report.methodology]) + "\n\n"
    md += "## Key Findings\n" + "\n".join([f"- {x}" for x in report.key_findings]) + "\n\n"
    md += "## Limitations\n" + "\n".join([f"- {x}" for x in report.limitations]) + "\n\n"
    md += "## Next Steps\n" + "\n".join([f"- {x}" for x in report.next_steps]) + "\n"

    report_tool = tool_registry.get("report_tool")
    report_path = REPORT_DIR / "analysis_report.md"
    saved_path = report_tool.run(content=md, output_path=str(report_path))

    artifacts = list(state.get("artifacts", []))
    artifacts.append(saved_path)

    return {
        "report": report.model_dump(),
        "artifacts": artifacts,
        "history": add_history(state, "[report_generator] 已生成分析报告"),
    }


def fail_node(state: dict) -> dict:
    return {
        "finished": True,
        "history": add_history(state, "[fail] 达到最大重试次数或不可恢复，任务失败"),
    }