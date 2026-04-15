from __future__ import annotations

from typing import Literal


def route_after_critic(state: dict) -> Literal["review", "coder"]:
    critic = state.get("critic_result", {})
    critic_rewrites = state.get("critic_rewrites", 0)
    max_critic_rewrites = state.get("max_critic_rewrites", 2)

    if critic.get("should_rewrite", False) and critic_rewrites < max_critic_rewrites:
        return "coder"

    return "review"


def route_after_executor(state: dict) -> Literal["report_generator", "error_analyzer"]:
    if not state.get("error"):
        return "report_generator"
    return "error_analyzer"


def route_after_error_analyzer(state: dict) -> Literal["coder", "fail"]:
    analysis = state.get("error_analysis", {})
    retries = state.get("retries", 0)
    max_retries = state.get("max_retries", 3)

    if not analysis.get("recoverable", True):
        return "fail"

    if retries >= max_retries:
        return "fail"

    return "coder"