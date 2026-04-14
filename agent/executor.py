"""Executor — runs a plan's skill chain, halting before production-affecting actions.

Internal steps (query, draft, test, store) execute autonomously.  When a step
would affect production (send message to customer, mutate live system), creates
a pending approval in the gate and stops.  The caller (CLI or API) must then
present the approval to the human, and resume execution after approval.
"""

from __future__ import annotations

import json

from agent.approval_gate import create_approval, requires_approval
from agent.context_store import add_entry
from agent.planner import Plan
from skills.registry import SkillRegistry


class ExecutionResult:
    """Result of executing a plan (partial or complete)."""

    def __init__(self) -> None:
        self.completed_steps: list[dict] = []
        self.pending_approval: dict | None = None  # set if halted at WRITE
        self.approval_id: int | None = None
        self.finished: bool = False
        self.error: str | None = None

    def format_for_human(self) -> str:
        """Format the execution result for display."""
        lines = []

        if self.completed_steps:
            lines.append("Completed steps:")
            for step in self.completed_steps:
                lines.append(f"  ✅ Step {step['step']}: {step['skill']} — {step.get('summary', 'done')}")

        if self.pending_approval:
            lines.append("")
            lines.append("⏸️  Awaiting approval:")
            pa = self.pending_approval
            lines.append(f"  Action: {pa['action_type']}")
            lines.append(f"  Details: {json.dumps(pa['action_payload'], indent=2, default=str)}")
            if self.approval_id:
                lines.append(f"  Approval ID: {self.approval_id}")
            lines.append("")
            lines.append("  Reply 'approve' or 'reject' to continue.")

        if self.finished:
            lines.append("\n✅ Plan completed.")

        if self.error:
            lines.append(f"\n❌ Error: {self.error}")

        return "\n".join(lines)


async def execute_plan(
    plan: Plan,
    registry: SkillRegistry,
    start_from: int = 0,
) -> ExecutionResult:
    """Execute a plan's steps sequentially.

    Internal steps run autonomously.  At the first production-affecting step,
    execution halts and a pending approval is created.

    Args:
        plan: The plan to execute.
        registry: Skill registry for looking up skills.
        start_from: Step index to resume from (after approval).

    Returns:
        ExecutionResult with completed steps and/or pending approval.
    """
    result = ExecutionResult()
    accumulated_context: dict = {}  # output from previous steps, available to next

    for i, step in enumerate(plan.steps):
        if i < start_from:
            continue

        skill_name = step.get("skill", "")
        params = step.get("parameters", {})
        classification = step.get("classification", "READ")

        # Merge accumulated context into parameters
        # (e.g., customer phone from step 1 becomes available in step 2)
        merged_params = {**accumulated_context, **params}

        # Production-affecting step → halt for approval
        if classification == "WRITE" or requires_approval(skill_name):
            approval_id = await create_approval(
                spine_object_id=plan.spine_object_id or "unknown",
                action_type=skill_name,
                action_payload=merged_params,
                context={
                    "plan_objective": plan.objective,
                    "step": step,
                    "prior_results": [s.get("result") for s in result.completed_steps],
                },
            )
            result.pending_approval = {
                "step": step,
                "action_type": skill_name,
                "action_payload": merged_params,
            }
            result.approval_id = approval_id
            return result

        # Internal step → execute autonomously
        skill = await registry.get(skill_name)
        if skill is None:
            result.error = f"Skill '{skill_name}' not found in registry"
            return result

        try:
            skill_result = await skill.execute(**merged_params)
            await registry.record_usage(skill_name)
        except Exception as exc:
            result.error = f"Skill '{skill_name}' failed: {exc}"
            return result

        # Accumulate useful outputs for subsequent steps
        if isinstance(skill_result, dict):
            for key in ("customer_name", "email", "phone", "total_due", "status",
                        "items", "products", "order_id", "customer_id"):
                if key in skill_result:
                    accumulated_context[key] = skill_result[key]

        result.completed_steps.append({
            "step": step.get("step", i + 1),
            "skill": skill_name,
            "result": skill_result,
            "summary": _summarize_result(skill_name, skill_result),
        })

    # Save execution to context store
    if plan.spine_object_id:
        await add_entry(
            spine_object_id=plan.spine_object_id,
            entry_type="action_result",
            content={
                "objective": plan.objective,
                "steps_completed": len(result.completed_steps),
                "results": [s.get("summary") for s in result.completed_steps],
            },
            source="agent",
        )

    result.finished = True
    return result


def _summarize_result(skill_name: str, result: dict) -> str:
    """One-line summary of a skill result for display."""
    if not result.get("success"):
        return f"failed: {result.get('error', 'unknown')}"

    if skill_name == "query_order_status":
        return f"Order {result.get('order_id')}: {result.get('status')}, ${result.get('total_due')}"
    if skill_name == "get_customer_info":
        return f"{result.get('first_name')} {result.get('last_name')} — {result.get('email') or 'no email'}"
    if skill_name == "list_order_items":
        return f"{result.get('item_count')} items, subtotal ${result.get('subtotal')}"
    if skill_name == "check_inventory":
        return f"{len(result.get('products', []))} products checked"

    return "done"
