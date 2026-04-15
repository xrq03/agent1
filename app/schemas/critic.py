from __future__ import annotations

from pydantic import BaseModel, Field


class CriticResult(BaseModel):
    is_safe: bool = Field(description="代码是否安全")
    is_consistent_with_plan: bool = Field(description="是否与计划一致")
    is_executable_likely: bool = Field(description="是否大概率可执行")
    issues: list[str] = Field(description="发现的问题")
    suggestions: list[str] = Field(description="修改建议")
    should_rewrite: bool = Field(description="是否建议重写代码")