from __future__ import annotations

from pathlib import Path
import pandas as pd

from .base import BaseTool


class FileTool(BaseTool):
    name = "file_tool"
    description = "Read local CSV or Excel files"

    def run(self, file_path: str):
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        suffix = path.suffix.lower()
        if suffix == ".csv":
            return pd.read_csv(path)
        if suffix in [".xlsx", ".xls"]:
            return pd.read_excel(path)

        raise ValueError(f"不支持的文件类型: {suffix}")