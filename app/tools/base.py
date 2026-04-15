from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    name: str = "base_tool"
    description: str = "abstract tool"

    @abstractmethod
    def run(self, **kwargs) -> Any:
        raise NotImplementedError