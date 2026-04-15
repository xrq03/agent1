from __future__ import annotations

import json
from langgraph.types import Command

from app.core.config import BASE_DIR, DEFAULT_EXECUTION_MODE, DEFAULT_MAX_RETRIES
from app.core.graph import build_graph


def pretty_print_state(state: dict) -> None:
    show = {
        "schema_profile": state.get("schema_profile"),
        "plan": state.get("plan"),
        "tool_plan": state.get("tool_plan"),
        "critic_result": state.get("critic_result"),
        "error_analysis": state.get("error_analysis"),
        "report": state.get("report"),
        "output": state.get("output"),
        "error": state.get("error"),
        "retries": state.get("retries"),
        "critic_rewrites": state.get("critic_rewrites"),
        "history": state.get("history"),
        "artifacts": state.get("artifacts"),
        "metrics": state.get("metrics"),
    }
    print(json.dumps(show, ensure_ascii=False, indent=2, default=str))


def has_interrupt(result: dict) -> bool:
    return "__interrupt__" in result and bool(result["__interrupt__"])


def main():
    graph = build_graph()
    thread_id = "demo-v4-001"
    config = {"configurable": {"thread_id": thread_id}}

    current = {
        "input": "请分析销售数据，按月份统计销售额并绘制趋势图，输出关键指标，并生成简短分析报告。",
        "file_path": str(BASE_DIR / "data" / "sales.csv"),
        "history": [],
        "retries": 0,
        "max_retries": DEFAULT_MAX_RETRIES,
        "review_required": True,
        "approved": False,
        "force_first_error": True,
        "finished": False,
        "execution_mode": DEFAULT_EXECUTION_MODE,
        "metrics": {},
        "artifacts": [],
        "metadata": {},
        "critic_rewrites": 0,
        "max_critic_rewrites": 2,
    }

    print("\n========== 启动图 ==========\n")
    result = graph.invoke(current, config=config)
    print(result)

    # 只要还在 interrupt，就持续恢复
    while has_interrupt(result):
        print("\n========== 检测到 review 中断，自动批准并恢复 ==========\n")
        result = graph.invoke(
            Command(resume={"approved": True, "edited_code": None}),
            config=config,
        )
        print(result)

    print("\n========== 最终状态 ==========\n")
    pretty_print_state(result)


if __name__ == "__main__":
    main()