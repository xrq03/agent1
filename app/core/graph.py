from __future__ import annotations

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from app.core.nodes import (
    coder_node,
    critic_node,
    error_analyzer_node,
    executor_node,
    fail_node,
    planner_node,
    report_generator_node,
    review_node,
    schema_inspector_node,
    tool_selector_node,
)
from app.core.router import (
    route_after_critic,
    route_after_error_analyzer,
    route_after_executor,
)
from app.core.state import AgentState


def build_graph():
    builder = StateGraph(AgentState)

    builder.add_node("schema_inspector", schema_inspector_node)
    builder.add_node("planner", planner_node)
    builder.add_node("tool_selector", tool_selector_node)
    builder.add_node("coder", coder_node)
    builder.add_node("critic", critic_node)
    builder.add_node("review", review_node)
    builder.add_node("executor", executor_node)
    builder.add_node("error_analyzer", error_analyzer_node)
    builder.add_node("report_generator", report_generator_node)
    builder.add_node("fail", fail_node)

    builder.add_edge(START, "schema_inspector")
    builder.add_edge("schema_inspector", "planner")
    builder.add_edge("planner", "tool_selector")
    builder.add_edge("tool_selector", "coder")

    builder.add_edge("coder", "critic")

    builder.add_conditional_edges(
        "critic",
        route_after_critic,
        {
            "review": "review",
            "coder": "coder",
        },
    )

    builder.add_edge("review", "executor")

    builder.add_conditional_edges(
        "executor",
        route_after_executor,
        {
            "report_generator": "report_generator",
            "error_analyzer": "error_analyzer",
        },
    )

    builder.add_conditional_edges(
        "error_analyzer",
        route_after_error_analyzer,
        {
            "coder": "coder",
            "fail": "fail",
        },
    )

    builder.add_edge("report_generator", END)
    builder.add_edge("fail", END)

    checkpointer = InMemorySaver()
    return builder.compile(checkpointer=checkpointer)