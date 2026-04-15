from __future__ import annotations

from .chart_tool import ChartTool
from .file_tool import FileTool
from .python_tool import PythonTool
from .report_tools import ReportTool
from .sandbox_tool import SandboxTool
from .states_tool import StatsTool


class ToolRegistry:
    def __init__(self):
        self.tools = {
            "file_tool": FileTool(),
            "python_tool": PythonTool(),
            "sandbox_tool": SandboxTool(),
            "chart_tool": ChartTool(),
            "stats_tool": StatsTool(),
            "report_tool": ReportTool(),
        }

    def get(self, name: str):
        if name not in self.tools:
            raise ValueError(f"Tool not found: {name}")
        return self.tools[name]

    def list_tools(self) -> dict[str, str]:
        return {name: tool.description for name, tool in self.tools.items()}