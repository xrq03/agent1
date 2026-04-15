from __future__ import annotations

from pydantic import BaseModel, Field


class SchemaProfile(BaseModel):
    columns: list[str] = Field(description="原始列名")
    dtypes: dict[str, str] = Field(description="列类型")
    shape: list[int] = Field(description="数据形状")
    date_columns: list[str] = Field(description="候选日期列")
    numeric_columns: list[str] = Field(description="候选数值列")
    categorical_columns: list[str] = Field(description="候选分类列")
    missing_summary: dict[str, float] = Field(description="各列缺失率")
    column_aliases: dict[str, list[str]] = Field(description="语义别名映射")
    observations: list[str] = Field(description="对数据的关键观察")