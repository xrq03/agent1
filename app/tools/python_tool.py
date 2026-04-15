from __future__ import annotations

from typing import Any


class PythonTool:
    name = "python_tool"
    description = "Execute generated Python code locally"

    def run(
        self,
        code: str,
        globals_dict: dict[str, Any],
        locals_dict: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if locals_dict is None:
            locals_dict = {}

        exec(code, globals_dict, locals_dict)
        return locals_dict