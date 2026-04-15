from __future__ import annotations

from pydantic import BaseModel, Field


class AnalysisPlan(BaseModel):
    objective: str = Field(description="分析目标")
    steps: list[str] = Field(description="执行步骤")
    expected_outputs: list[str] = Field(description="预期输出")
    libraries: list[str] = Field(description="建议使用的库")
    risk_notes: list[str] = Field(description="潜在风险")
    save_plot_as: str = Field(description="图表保存文件名")
    selected_tools: list[str] = Field(description="本任务需要使用的工具")