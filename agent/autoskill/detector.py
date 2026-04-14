"""AutoSkill Gap Detector — identifies when the agent needs a skill it doesn't have.

When the orchestrator or planner can't find a matching skill for a user request,
the detector records the gap and triggers the AutoSkill generation loop.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class SkillGap:
    """A detected gap in the skill registry."""

    description: str          # what the user wanted
    domain: str               # best guess at domain
    user_message: str         # original message that triggered the gap
    detected_at: datetime = field(default_factory=datetime.now)
    resolved: bool = False
    generated_skill_name: str | None = None


class GapDetector:
    """Tracks skill gaps and decides when to trigger AutoSkill generation."""

    def __init__(self) -> None:
        self._gaps: list[SkillGap] = []

    def record_gap(self, user_message: str, description: str, domain: str = "cross-domain") -> SkillGap:
        """Record a detected skill gap. Called by the orchestrator when no skill matches."""
        gap = SkillGap(
            description=description,
            domain=domain,
            user_message=user_message,
        )
        self._gaps.append(gap)
        return gap

    def get_unresolved_gaps(self) -> list[SkillGap]:
        """Return all gaps that haven't been resolved yet."""
        return [g for g in self._gaps if not g.resolved]

    def resolve_gap(self, gap: SkillGap, skill_name: str) -> None:
        """Mark a gap as resolved after a skill was generated for it."""
        gap.resolved = True
        gap.generated_skill_name = skill_name

    async def should_generate(self, description: str) -> bool:
        """Check if we should attempt to generate a skill for this gap.

        Avoids re-generating for the same gap repeatedly. Returns True if
        no existing gap with the same description has been resolved.
        """
        for gap in self._gaps:
            if gap.description == description and gap.resolved:
                return False  # Already generated a skill for this
        return True
