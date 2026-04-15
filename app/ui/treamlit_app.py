from __future__ import annotations

from pathlib import Path

import streamlit as st
from langgraph.types import Command

from app.core.config import BASE_DIR
from app.core.graph import build_graph

graph = build_graph()

st.set_page_config(page_title="Self-Correcting Data Analyst Agent v4", layout="wide")
st.title("Self-Correcting Data Analyst Agent v4")

uploaded = st.file_uploader("上传 CSV / Excel 文件", type=["csv", "xlsx", "xls"])
user_input = st.text_area("输入分析需求", value="请按月份统计销售额并绘制趋势图，并生成简短分析报告。")
review_required = st.checkbox("启用人工审核", value=True)
execution_mode = st.selectbox("执行模式", ["local", "sandbox"])
force_first_error = st.checkbox("演示首轮故意报错", value=True)

if "thread_id" not in st.session_state:
    st.session_state.thread_id = "streamlit-v4-demo"

if uploaded:
    save_dir = BASE_DIR / "data"
    save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / uploaded.name
    save_path.write_bytes(uploaded.read())
    st.success(f"文件已保存到: {save_path}")

    if st.button("开始运行"):
        config = {"configurable": {"thread_id": st.session_state.thread_id}}
        initial_state = {
            "input": user_input,
            "file_path": str(save_path),
            "history": [],
            "retries": 0,
            "max_retries": 3,
            "review_required": review_required,
            "approved": False,
            "execution_mode": execution_mode,
            "force_first_error": force_first_error,
            "metrics": {},
            "artifacts": [],
            "metadata": {},
        }

        first_result = graph.invoke(initial_state, config=config)
        st.subheader("第一次返回")
        st.write(first_result)

    if st.button("批准并恢复执行"):
        config = {"configurable": {"thread_id": st.session_state.thread_id}}
        final_result = graph.invoke(
            Command(resume={"approved": True, "edited_code": None}),
            config=config,
        )

        st.subheader("最终结果")
        st.json(final_result)

        report = final_result.get("report", {})
        if report:
            st.subheader("分析报告摘要")
            st.write(report)

        for artifact in final_result.get("artifacts", []):
            st.write(f"产物: {artifact}")
            artifact_path = Path(artifact)
            if artifact_path.exists() and artifact_path.suffix.lower() in [".png", ".jpg", ".jpeg"]:
                st.image(str(artifact_path))