"""Intent Router — classifies user messages into modes and extracts parameters.

Uses Claude to determine:
  - mode: assist | act | monitor
  - domain: sales | production | purchasing | person | cross-domain
  - skill: best matching skill name (if identifiable)
  - parameters: extracted from the message (e.g. order_id, customer_id, product_id)
"""

from __future__ import annotations

import json

import anthropic

from agent.config import get_settings

ROUTER_SYSTEM_PROMPT = """\
You are an intent router for a business operations agent. Your job is to \
classify user messages and extract structured parameters.

Available skills:
- query_order_status: Check order status (needs order_id)
- get_customer_info: Get customer details (needs order_id or customer_id)
- list_order_items: List items in an order (needs order_id)
- check_inventory: Check product stock (needs product_id or order_id)
- analyze_company_config: Show database structure, schemas, tables, columns, relationships (no params needed)

Respond with JSON only, no other text:
{
  "mode": "assist" | "act",
  "domain": "sales" | "production" | "purchasing" | "person" | "cross-domain",
  "skill": "<skill_name or null if unclear>",
  "parameters": { "order_id": <int>, "customer_id": <int>, "product_id": <int> },
  "summary": "<one-line summary of what the user wants>"
}

Rules:
- "assist" mode: user is asking a question or requesting information
- "act" mode: user wants the agent to DO something (send, update, notify, change)
- Extract numeric IDs from the message (e.g. "orden 43659" → order_id: 43659)
- If the user mentions an order, default domain to "sales"
- If the user asks about a customer, default domain to "person"
- If the user asks about stock/inventory, default domain to "production"
- If the user asks about database structure, schemas, tables, columns, or "what data do we have", route to analyze_company_config with domain "cross-domain"
- parameters should only contain IDs you can actually extract from the message
"""


class RoutingResult:
    """Structured output from the router."""

    __slots__ = ("mode", "domain", "skill", "parameters", "summary", "raw")

    def __init__(self, data: dict) -> None:
        self.mode: str = data.get("mode", "assist")
        self.domain: str = data.get("domain", "cross-domain")
        self.skill: str | None = data.get("skill")
        self.parameters: dict = data.get("parameters", {})
        # Strip None values from parameters
        self.parameters = {k: v for k, v in self.parameters.items() if v is not None}
        self.summary: str = data.get("summary", "")
        self.raw = data

    def __repr__(self) -> str:
        return f"RoutingResult(mode={self.mode!r}, domain={self.domain!r}, skill={self.skill!r}, params={self.parameters})"


async def route(message: str) -> RoutingResult:
    """Classify a user message and extract parameters using Claude."""
    settings = get_settings()
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=256,
        system=ROUTER_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": message}],
    )

    text = response.content[0].text.strip()

    # Parse JSON — handle markdown code blocks if Claude wraps it
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = {"mode": "assist", "domain": "cross-domain", "skill": None, "parameters": {}, "summary": message}

    return RoutingResult(data)
