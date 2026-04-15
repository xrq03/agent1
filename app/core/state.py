from typing import Any
from typing_extensions import TypedDict


class AgentState(TypedDict, total=False):
    input: str
    file_path: str

    schema_profile: dict
    plan: dict
    tool_plan: dict
    code: str
    critic_result: dict
    review_decision: dict
    output: dict

    error: str
    error_analysis: dict

    report: dict
    artifacts: list[str]
    metrics: dict[str, Any]
    history: list[str]

    retries: int
    max_retries: int
    approved: bool
    review_required: bool
    finished: bool

    selected_tools: list[str]
    execution_mode: str
    eval_mode: bool
    benchmark_id: str
    metadata: dict[str, Any]

    force_first_error: bool
    critic_rewrites: int
    max_critic_rewrites: int