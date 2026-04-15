from __future__ import annotations

from pydantic import BaseModel, Field


class ToolSelection(BaseModel):
    selected_tools: list[str] = Field(description="所需工具")
    rationale: list[str] = Field(description="选择这些工具的原因")
    execution_mode: str = Field(description="local 或 sandbox")