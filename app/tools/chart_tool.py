from __future__ import annotations

from pathlib import Path
import matplotlib.pyplot as plt


class ChartTool:
    name = "chart_tool"
    description = "Save matplotlib figures"

    def run(self, save_path: str) -> str:
        path = Path(save_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(path)
        return str(path)