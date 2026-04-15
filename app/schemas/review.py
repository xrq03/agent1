from __future__ import annotations

from pydantic import BaseModel, Field


class ReviewDecision(BaseModel):
    approved: bool = Field(description="是否批准执行")
    edited_code: str | None = Field(default=None, description="人工修改后的代码")