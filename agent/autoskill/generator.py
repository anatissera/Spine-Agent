"""AutoSkill Generator — uses Claude to generate new skills from gap descriptions.

Given a description of what the user needs, generates:
  1. A skill spec (name, description, domain, inputs/outputs)
  2. The Python implementation code
  3. A basic test

The generated skill is returned as a dict — validation and persistence happen
in the validator and registry respectively.
"""

from __future__ import annotations

import json
import re

import anthropic

from agent.config import get_settings

GENERATOR_SYSTEM_PROMPT = """\
You are a skill generator for SpineAgent. You generate Python skill code \
that queries an AdventureWorks PostgreSQL database.

The database has these schemas and key tables:
- sales: salesorderheader, salesorderdetail, customer, salesperson
- production: product, productinventory, productcategory, productsubcategory
- person: person, emailaddress, personphone, address
- purchasing: purchaseorderheader, purchaseorderdetail, vendor
- humanresources: employee, department

All table and column names are lowercase in PostgreSQL.

Here is an EXAMPLE of a correct skill implementation:

```python
from typing import Any
from skills.base_skill import BaseSkill

class CalculateOrderMargin(BaseSkill):
    name = "calculate_order_margin"
    description = "Calculate profit margin for a sales order"
    domain = "sales"

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        from agent.db import get_connection
        order_id = kwargs["order_id"]
        async with await get_connection() as conn:
            rows = await (await conn.execute(
                \"\"\"SELECT ... FROM ... WHERE ... = %(order_id)s\"\"\",
                {"order_id": order_id}
            )).fetchall()
        return {"success": True, "data": rows}
```

CRITICAL RULES:
1. Subclass BaseSkill from skills.base_skill
2. Set name, description, domain as CLASS ATTRIBUTES (not in __init__)
3. Use "from agent.db import get_connection" — this is psycopg3 (NOT asyncpg)
4. Connection pattern: async with await get_connection() as conn
5. Query pattern: await (await conn.execute(sql, params)).fetchall()
6. Use %(param)s for query parameters (psycopg named params), NOT $1
7. Return {"success": True, ...} or {"success": False, "error": "..."}
8. Read-only (SELECT only)
9. Import typing.Any for type hints

Respond with JSON only:
{
  "name": "skill_name_in_snake_case",
  "description": "What the skill does",
  "domain": "sales|production|purchasing|person|cross-domain",
  "code": "full Python source code of the skill module"
}
"""


async def generate_skill(gap_description: str, user_message: str) -> dict | None:
    """Generate a new skill using Claude based on a gap description.

    Returns a dict with name, description, domain, and code.
    Returns None if generation fails.
    """
    settings = get_settings()
    if not settings.anthropic_api_key:
        return None

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        system=GENERATOR_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Generate a skill for this need:\n\n"
                    f"Gap: {gap_description}\n"
                    f"Original user message: {user_message}\n\n"
                    f"Generate the skill as JSON with name, description, domain, and code fields."
                ),
            },
        ],
    )

    text = response.content[0].text.strip()

    # Handle markdown code blocks
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        return None

    if not all(k in result for k in ("name", "description", "domain", "code")):
        return None

    return result
