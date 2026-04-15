from __future__ import annotations

from pathlib import Path


class ReportTool:
    name = "report_tool"
    description = "Write markdown analysis report"

    def run(self, content: str, output_path: str) -> str:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return str(path)