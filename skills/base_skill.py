"""Base class for all SpineAgent skills."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseSkill(ABC):
    """Every skill must subclass this and implement execute()."""

    name: str
    description: str
    domain: str  # sales | production | purchasing | person | cross-domain

    def get_spec(self) -> dict[str, Any]:
        """Return the skill spec for DB storage.  Override in subclasses."""
        return {"inputs": {}, "outputs": {}, "dependencies": []}

    @abstractmethod
    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        """Run the skill and return a result dict."""
        ...
