"""AutoSkill Loop — orchestrates the full gap → generate → validate → persist cycle.

This is the entry point for the AutoSkill system. When a skill gap is detected,
this module drives the full loop:
  1. Detect the gap (from detector)
  2. Generate a new skill (via Claude)
  3. Validate the generated code (syntax, class structure)
  4. Persist to filesystem and register in the skill registry
"""

from __future__ import annotations

from agent.autoskill.detector import GapDetector, SkillGap
from agent.autoskill.generator import generate_skill
from agent.autoskill.validator import ValidationResult, persist_skill_code, validate_skill_code
from skills.registry import SkillRegistry

# Shared instances — initialized by the orchestrator
_detector = GapDetector()


def get_detector() -> GapDetector:
    return _detector


async def handle_gap(
    user_message: str,
    gap_description: str,
    domain: str,
    registry: SkillRegistry,
    max_attempts: int = 2,
) -> dict:
    """Full AutoSkill loop: detect → generate → validate → persist.

    Args:
        user_message: The original user message that triggered the gap.
        gap_description: What skill is needed.
        domain: Best guess at the domain.
        registry: The skill registry to persist the new skill to.
        max_attempts: How many generation attempts before giving up.

    Returns:
        A result dict with success status and details.
    """
    detector = get_detector()

    # Check if we should even try
    if not await detector.should_generate(gap_description):
        return {"success": False, "reason": "Skill for this gap was already generated"}

    # Record the gap
    gap = detector.record_gap(user_message, gap_description, domain)

    # Try generation + validation up to max_attempts times
    for attempt in range(1, max_attempts + 1):
        print(f"  [AutoSkill] Attempt {attempt}/{max_attempts}: generating skill for '{gap_description}'...")

        # Generate
        generated = await generate_skill(gap_description, user_message)
        if generated is None:
            print(f"  [AutoSkill] Generation failed (attempt {attempt})")
            continue

        name = generated["name"]
        code = generated["code"]
        print(f"  [AutoSkill] Generated '{name}' — validating...")

        # Validate
        result = validate_skill_code(name, code)
        if not result.valid:
            print(f"  [AutoSkill] Validation failed: {result.error}")
            continue

        # Persist code to filesystem
        path = persist_skill_code(name, code)
        print(f"  [AutoSkill] Code saved to {path}")

        # Register in the skill registry
        await registry.register(result.skill)
        detector.resolve_gap(gap, name)

        print(f"  [AutoSkill] Skill '{name}' registered successfully!")
        return {
            "success": True,
            "skill_name": name,
            "description": generated["description"],
            "domain": generated["domain"],
            "code_path": str(path),
            "attempts": attempt,
        }

    return {
        "success": False,
        "reason": f"Failed after {max_attempts} attempts",
        "gap_description": gap_description,
    }
