"""Planner — decomposes a user objective into an ordered chain of skill calls.

Uses Claude to reason about what steps are needed, mapping each step to an
available skill with the correct parameters.  Classifies each step as READ
or WRITE to determine where the approval gate should halt execution.
"""

from __future__ import annotations

import json

import anthropic

from agent.config import get_settings

PLANNER_SYSTEM_PROMPT = """\
You are a planner for a business operations agent. Given a user objective, \
decompose it into an ordered sequence of skill calls.

Available skills:
- query_order_status(order_id) → order status, dates, totals, customer name [READ]
- get_customer_info(order_id or customer_id) → name, email, phone, store [READ]
- list_order_items(order_id) → line items with product details and pricing [READ]
- check_inventory(product_id or order_id) → stock levels by location [READ]
- detect_stale_orders(limit) → orders past their expected processing time [READ]
- analyze_company_config(schemas?, exclude_schemas?) → database structure report with schemas, tables, columns, FKs [READ]
- send_telegram_message(message, chat_id) → send message to customer/operator [WRITE]
- update_order_status(order_id, new_status) → change order status [WRITE]

Rules:
- Each step must map to exactly one skill
- Steps execute in order; output of step N is available to step N+1
- READ steps execute autonomously (no approval needed)
- WRITE steps HALT execution and require human approval before proceeding
- Extract all numeric IDs from the user message
- If the objective requires information before acting, put READ steps first
- Always gather context (READ) before proposing actions (WRITE)

Respond with JSON only:
{
  "objective": "one-line summary of what the user wants",
  "spine_object_id": "SalesOrder:{id}" or null,
  "steps": [
    {
      "step": 1,
      "skill": "skill_name",
      "parameters": {"param": "value"},
      "classification": "READ" or "WRITE",
      "description": "what this step does and why"
    }
  ]
}
"""


class Plan:
    """A structured execution plan."""

    def __init__(self, data: dict) -> None:
        self.objective: str = data.get("objective", "")
        self.spine_object_id: str | None = data.get("spine_object_id")
        self.steps: list[dict] = data.get("steps", [])
        self.raw = data

    @property
    def read_steps(self) -> list[dict]:
        return [s for s in self.steps if s.get("classification") == "READ"]

    @property
    def write_steps(self) -> list[dict]:
        return [s for s in self.steps if s.get("classification") == "WRITE"]

    def format_for_human(self) -> str:
        """Format the plan for human review (approval gate presentation)."""
        lines = [f"Objective: {self.objective}", ""]
        for step in self.steps:
            tag = "🟢 READ" if step.get("classification") == "READ" else "🔴 WRITE"
            lines.append(f"  Step {step['step']}: [{tag}] {step['skill']}({step.get('parameters', {})})")
            lines.append(f"         {step.get('description', '')}")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return f"Plan(objective={self.objective!r}, steps={len(self.steps)})"


async def create_plan(user_message: str) -> Plan:
    """Use Claude to decompose a user objective into an execution plan."""
    settings = get_settings()
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=PLANNER_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = {"objective": user_message, "steps": []}

    return Plan(data)
