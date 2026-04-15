from __future__ import annotations

from pydantic import BaseModel, Field


class ErrorAnalysis(BaseModel):
    error_type: str = Field(description="错误类型")
    root_cause: str = Field(description="根因")
    fix_hint: str = Field(description="修复建议")
    recoverable: bool = Field(description="是否可恢复")