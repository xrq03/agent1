from __future__ import annotations

from pydantic import BaseModel, Field


class EvalResult(BaseModel):
    task_id: str = Field(description="任务 ID")
    success: bool = Field(description="是否成功")
    retries: int = Field(description="重试次数")
    error: str = Field(description="错误信息")
    metrics: dict = Field(description="运行指标")