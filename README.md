# Self-Correcting Data Analyst Agent via LangGraph

基于 **LangGraph** 构建的自愈式 Python 数据分析 Agent。  
系统能够根据用户的自然语言需求，自动完成：

- 数据结构理解
- 分析任务规划
- 工具选择
- Python 代码生成
- 执行前代码自检
- 人工审核
- 代码执行
- 错误分析与自动修复
- 图表生成
- 分析报告输出

项目重点不在于“一次生成成功”，而在于：  
**当第一轮代码执行失败时，系统能否基于 traceback 自动修复并重试。**

---

## 项目亮点

### 1. 自愈式执行闭环
系统在执行失败后不会直接结束，而是会：

1. 捕获 traceback
2. 将错误写入全局 state
3. 由 `error_analyzer` 分类错误根因
4. 再次驱动 `coder` 生成修复版代码
5. 重试执行直到成功或达到上限

---

### 2. LangGraph 状态化工作流
整个系统由 LangGraph 的有状态图驱动，而不是单纯的 while 循环。

核心节点包括：

- `schema_inspector`
- `planner`
- `tool_selector`
- `coder`
- `critic`
- `review`
- `executor`
- `error_analyzer`
- `report_generator`

---

### 3. Human-in-the-loop
在代码真正执行之前，系统会在 `review` 节点中断，等待人工审核后再继续。  
这样可以降低 LLM 直接执行代码带来的安全风险。

---

### 4. Critic 自检
在执行前，系统会先让 `critic` 对生成代码进行检查，重点关注：

- 是否引用不存在的列
- 是否存在未定义变量
- 是否覆盖运行环境变量
- 是否与分析计划一致
- 是否大概率可执行

---

### 5. 分析结果可交付
系统不仅会生成图表，还会输出 Markdown 报告，方便面试演示和后续扩展到前端。

---

# 项目结构

```text
self_correcting_data_agent_v4/
├── .env
├── requirements.txt
├── run_demo.py
├── run_server.py
├── README.md
├── app/
│   ├── core/
│   │   ├── config.py
│   │   ├── graph.py
│   │   ├── nodes.py
│   │   ├── router.py
│   │   └── state.py
│   ├── runtime/
│   │   ├── artifacts.py
│   │   ├── executor.py
│   │   └── llm.py
│   ├── schemas/
│   │   ├── critic.py
│   │   ├── error_analysis.py
│   │   ├── plan.py
│   │   ├── report.py
│   │   ├── review.py
│   │   ├── schema_profile.py
│   │   └── tool_selection.py
│   ├── tools/
│   │   ├── base.py
│   │   ├── chart_tool.py
│   │   ├── file_tool.py
│   │   ├── python_tool.py
│   │   ├── registry.py
│   │   ├── report_tool.py
│   │   ├── sandbox_tool.py
│   │   └── stats_tool.py
│   └── ui/
│       └── streamlit_app.py
├── data/
├── outputs/
└── reports/

安装步骤
1. 创建虚拟环境
python -m venv .venv

Windows:

.venv\Scripts\activate

macOS / Linux:

source .venv/bin/activate
2. 安装依赖
pip install -r requirements.txt
环境变量配置

在项目根目录创建 .env 文件：

OPENAI_API_KEY=your_api_key
OPENAI_MODEL=your_model_name
OPENAI_BASE_URL=your_base_url

例如使用兼容 OpenAI 接口的模型服务：

OPENAI_API_KEY=sk-xxxx
OPENAI_MODEL=DeepSeek-V3.2
OPENAI_BASE_URL=https://your-openai-compatible-endpoint/v1
数据准备

将待分析的数据文件放到 data/ 目录下，例如：

data/
└── sales.csv

示例 sales.csv：

date,product,sales
2026-01-05,A,100
2026-01-15,B,120
2026-02-05,A,130
2026-02-20,B,150
2026-03-08,A,170
2026-03-18,B,180
运行方式
1. 命令行演示
python run_demo.py

该脚本会：

启动整个图
在 review 节点中断
自动恢复执行
如果首轮失败，则触发自愈循环
最终输出结果、图表和报告
2. Streamlit 前端
python run_server.py

或直接运行：

streamlit run app/ui/streamlit_app.py

前端支持：

上传 CSV / Excel
输入分析需求
触发运行
人工批准继续执行
查看输出结果与图表
输出产物

运行成功后，通常会在以下目录看到结果：

outputs/
└── analysis.png

reports/
└── analysis_report.md

其中：

analysis.png 为趋势图
analysis_report.md 为自动生成的分析报告
