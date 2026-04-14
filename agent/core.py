"""Core Orchestrator — ties together routing, skills, context, and LLM response.

Supports two modes:
  Assist: question → router → skill → context → LLM response
  Act:    objective → planner → executor (READ auto, WRITE → approval gate)
"""

from __future__ import annotations

import json

import anthropic

from agent.config import get_settings
from agent.context_store import add_entry, get_entries_for_spine
from agent.executor import ExecutionResult, execute_plan
from agent.planner import Plan, create_plan
from agent.router import RoutingResult, route
from skills.registry import SkillRegistry

RESPONSE_SYSTEM_PROMPT = """\
You are SpineAgent, an operational assistant for a business that uses \
AdventureWorks as its system of record. You help operators understand orders, \
customers, inventory, and business operations.

You will receive:
1. The user's original question
2. Real data from the business systems (skill execution results)
3. Historical context about the spine object (if any)

Rules:
- Answer based ONLY on the real data provided — never invent information
- Be concise and direct
- Use the actual numbers, names, and dates from the data
- If data is missing or an error occurred, say so honestly
- Format currency with $ and two decimals where appropriate
- You can respond in the same language the user writes in
"""


class SpineAgent:
    """Main agent orchestrator."""

    def __init__(self) -> None:
        self.registry = SkillRegistry()
        self._initialized = False
        self._pending_plan: Plan | None = None
        self._pending_execution: ExecutionResult | None = None

    async def _ensure_init(self) -> None:
        if not self._initialized:
            await self.registry.ensure_builtin_skills()
            self._initialized = True

    async def handle_message(self, message: str) -> str:
        """Process a user message end-to-end and return a natural language response.

        Supports:
          - Assist mode: question → skill → context → LLM response
          - Act mode: objective → plan → execute (halt at WRITE for approval)
          - Approval responses: 'approve' / 'reject' to continue a halted plan
        """
        await self._ensure_init()

        # Handle approval responses for pending plans
        lower = message.strip().lower()
        if lower in ("approve", "aprobar", "si", "yes") and self._pending_execution:
            return await self._handle_approval(approved=True)
        if lower in ("reject", "rechazar", "no") and self._pending_execution:
            return await self._handle_approval(approved=False)

        # 1. Route
        routing = await route(message)

        if routing.mode == "act":
            return await self._handle_act(message)

        # 2. Select and execute skill
        skill_result = await self._execute_skill(routing)

        # 3. Fetch context history for the spine object
        context_history = await self._get_context(routing)

        # 4. Generate response with Claude
        response = await self._generate_response(message, routing, skill_result, context_history)

        # 5. Save to context store
        await self._save_interaction(routing, message, skill_result, response)

        return response

    async def _execute_skill(self, routing: RoutingResult) -> dict:
        """Execute the best matching skill based on routing."""
        skill = None

        # Try exact skill match first
        if routing.skill:
            skill = await self.registry.get(routing.skill)

        # Fallback: search by domain
        if skill is None:
            domain_skills = await self.registry.search_by_domain(routing.domain)
            if domain_skills:
                skill = await self.registry.get(domain_skills[0]["name"])

        if skill is None:
            return {"success": False, "error": "No matching skill found"}

        try:
            result = await skill.execute(**routing.parameters)
            await self.registry.record_usage(skill.name)
            return result
        except Exception as exc:
            return {"success": False, "error": f"Skill execution failed: {exc}"}

    async def _get_context(self, routing: RoutingResult) -> list[dict]:
        """Fetch historical context entries for the relevant spine object."""
        order_id = routing.parameters.get("order_id")
        if order_id:
            return await get_entries_for_spine(f"SalesOrder:{order_id}")
        return []

    async def _generate_response(
        self,
        user_message: str,
        routing: RoutingResult,
        skill_result: dict,
        context_history: list[dict],
    ) -> str:
        """Use Claude to generate a natural language response from the data."""
        settings = get_settings()
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

        # Build the context block for Claude
        parts = [f"## Skill Result\n```json\n{json.dumps(skill_result, indent=2, default=str)}\n```"]

        if context_history:
            history_text = "\n".join(
                f"- [{e['entry_type']}] {json.dumps(e['content'], default=str)}"
                for e in context_history[:5]  # last 5 entries
            )
            parts.append(f"## Historical Context\n{history_text}")

        parts.append(f"## Routing\nMode: {routing.mode} | Domain: {routing.domain} | Skill: {routing.skill}")

        context_block = "\n\n".join(parts)

        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=RESPONSE_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"{user_message}\n\n---\n\n{context_block}",
                },
            ],
        )

        return response.content[0].text

    async def _save_interaction(
        self,
        routing: RoutingResult,
        user_message: str,
        skill_result: dict,
        response: str,
    ) -> None:
        """Save the interaction as a context entry for future reference."""
        order_id = routing.parameters.get("order_id")
        if not order_id:
            return

        await add_entry(
            spine_object_id=f"SalesOrder:{order_id}",
            entry_type="action_result",
            content={
                "user_message": user_message,
                "skill": routing.skill,
                "result_summary": response[:200],
            },
            source="agent",
        )

    # ── Act Mode ─────────────────────────────────────────────────────────

    async def _handle_act(self, message: str) -> str:
        """Handle Act mode: plan → execute → halt at WRITE for approval."""
        # 1. Create plan
        plan = await create_plan(message)
        self._pending_plan = plan

        if not plan.steps:
            return "No pude descomponer el objetivo en pasos ejecutables."

        # 2. Execute the plan (will halt at first WRITE step)
        result = await execute_plan(plan, self.registry)
        self._pending_execution = result

        # 3. Format response
        parts = [f"**Plan:** {plan.objective}\n"]
        parts.append(plan.format_for_human())
        parts.append("\n---\n")
        parts.append(result.format_for_human())

        return "\n".join(parts)

    async def _handle_approval(self, approved: bool) -> str:
        """Handle approve/reject for a pending WRITE action."""
        from agent.approval_gate import approve, reject

        execution = self._pending_execution
        if not execution or not execution.approval_id:
            return "No hay acciones pendientes de aprobación."

        approval_id = execution.approval_id

        if approved:
            await approve(approval_id)
            self._pending_execution = None
            self._pending_plan = None
            return (
                f"✅ Acción aprobada (approval #{approval_id}).\n\n"
                "La acción fue registrada. La ejecución real de acciones WRITE "
                "(envío de mensajes, actualizaciones) se completará cuando se "
                "integren los MCP servers de Telegram/Tiendanube."
            )
        else:
            await reject(approval_id)
            self._pending_execution = None
            self._pending_plan = None
            return f"❌ Acción rechazada (approval #{approval_id}). No se ejecutará ninguna acción."
