from __future__ import annotations

from pathlib import Path
from typing import Iterable


def normalize_artifacts(artifacts: Iterable[str] | None) -> list[str]:
    if not artifacts:
        return []
    return [str(Path(p)) for p in artifacts]