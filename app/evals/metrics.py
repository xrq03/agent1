from __future__ import annotations


def compute_summary(results: list[dict]) -> dict:
    total = len(results)
    success_count = sum(1 for r in results if r.get("success"))
    avg_retries = sum(r.get("retries", 0) for r in results) / total if total else 0

    return {
        "total_tasks": total,
        "success_count": success_count,
        "success_rate": success_count / total if total else 0,
        "avg_retries": avg_retries,
    }