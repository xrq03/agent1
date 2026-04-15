from __future__ import annotations

from typing import Any


class SandboxTool:
    name = "sandbox_tool"
    description = "Execute generated Python code in a sandbox-like interface"

    def run(self, code: str, context: dict[str, Any]) -> dict[str, Any]:
        """
        当前版本只是预留统一接口。
        后续你可以替换成：
        - Docker 容器
        - 远程沙箱服务
        - RestrictedPython
        """
        exec_globals = dict(context)
        exec_locals: dict[str, Any] = {}
        exec(code, exec_globals, exec_locals)
        return exec_locals