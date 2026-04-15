from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import matplotlib.pyplot as plt

from app.tools.registry import ToolRegistry


class ExecutionRuntime:
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.registry = ToolRegistry()

    def run_code(
        self,
        code: str,
        file_path: str,
        execution_mode: str = "local",
    ) -> dict[str, Any]:
        file_tool = self.registry.get("file_tool")
        df = file_tool.run(file_path=file_path)

        plt.close("all")

        context = {
            "__builtins__": __builtins__,
            "pd": pd,
            "plt": plt,
            "df": df,
            "OUTPUT_DIR": self.output_dir,
        }

        if execution_mode == "sandbox":
            sandbox = self.registry.get("sandbox_tool")
            result_locals = sandbox.run(code=code, context=context)
        else:
            python_tool = self.registry.get("python_tool")
            result_locals = python_tool.run(
                code=code,
                globals_dict=context,
                locals_dict={},
            )

        if "result" not in result_locals:
            raise ValueError("代码执行后未生成 result 变量")

        return result_locals["result"]