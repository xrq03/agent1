from __future__ import annotations

import json
from pathlib import Path

from langgraph.types import Command

from app.core.config import BASE_DIR, DEFAULT_MAX_RETRIES
from app.core.graph import build_graph
from app.evals.metrics import compute_summary


def load_tasks(task_file: str) -> list[dict]:
    task_path = Path(task_file)
    if not task_path.is_absolute():
        task_path = BASE_DIR / task_file
    return json.loads(task_path.read_text(encoding="utf-8"))


def run_benchmark(task_file: str = "app/evals/tasks.json") -> dict:
    graph = build_graph()
    tasks = load_tasks(task_file)
    results = []

    for task in tasks:
        thread_id = f"benchmark-{task['id']}"
        config = {"configurable": {"thread_id": thread_id}}

        file_path = task["file_path"]
        if not Path(file_path).is_absolute():
            file_path = str(BASE_DIR / file_path)

        initial_state = {
            "input": task["input"],
            "file_path": file_path,
            "history": [],
            "retries": 0,
            "max_retries": DEFAULT_MAX_RETRIES,
            "review_required": True,
            "approved": False,
            "execution_mode": "local",
            "eval_mode": True,
            "benchmark_id": task["id"],
            "force_first_error": task.get("force_first_error", False),
            "metrics": {},
            "artifacts": [],
            "metadata": {},
        }

        graph.invoke(initial_state, config=config)
        final_state = graph.invoke(
            Command(resume={"approved": True, "edited_code": None}),
            config=config,
        )

        results.append({
            "task_id": task["id"],
            "success": bool(final_state.get("output")) and not final_state.get("error"),
            "retries": final_state.get("retries", 0),
            "metrics": final_state.get("metrics", {}),
            "error": final_state.get("error", ""),
        })

    summary = compute_summary(results)
    return {
        "summary": summary,
        "results": results,
    }


if __name__ == "__main__":
    result = run_benchmark()
    print(json.dumps(result, ensure_ascii=False, indent=2))