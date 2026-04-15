from __future__ import annotations

from pydantic import BaseModel, Field


class AnalysisReport(BaseModel):
    title: str = Field(description="报告标题")
    objective: str = Field(description="分析目标")
    dataset_summary: str = Field(description="数据概览")
    methodology: list[str] = Field(description="分析步骤")
    key_findings: list[str] = Field(description="关键发现")
    artifacts: list[str] = Field(description="图表或文件")
    limitations: list[str] = Field(description="局限性")
    next_steps: list[str] = Field(description="下一步建议")