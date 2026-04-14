# Skill Schema and Registry

> **Document type:** System Definition — Self-Improvement Engine  
> **Project:** SpineAgent — Anthropic Hackathon  
> **Status:** Authoritative. The Skill Schema defined here is the only valid format for skills in this system.

---

## 1. What a Skill Is

A Skill is the atomic unit of executable capability in the SpineAgent system. It is not a prompt — it is a discrete, callable function that wraps a specific operation (database query, API call, computation, LLM generation) in a standardized interface that the agent can discover, invoke, and chain.

The Skill Registry is not just code storage. It is **the institutionalized knowledge of how this business operates** — encoded, versioned, and reusable.

### Key Properties

- **Self-describing:** Every skill carries enough metadata for the LLM to decide when to use it without reading its code
- **Sandboxable:** Every skill can be executed in isolation with mock inputs
- **Classifiable:** Every skill has an immutable READ/WRITE classification
- **Discoverable:** The LLM can search the registry by natural language description
- **Chainable:** Skill outputs follow a standardized schema so they can feed into the next skill

---

## 2. The Skill File Structure

Each skill lives in its own directory under `skills/`:

```
skills/
├── registry.py               # Registry CRUD and search
├── base_skill.py             # BaseSkill class all skills inherit from
│
├── builtin/                  # Seed skills (hardcoded, hand-written)
│   ├── query_order_status/
│   ├── get_customer_info/
│   └── ... (see Section 4)
│
└── generated/                # AutoSkill-generated skills
    └── calculate_order_margin/  ← Example from the demo
```

Each skill directory contains exactly these files:

```
skills/builtin/query_order_status/
├── spec.yaml         ← Machine-readable metadata (the LLM reads this to decide)
├── code.py           ← The executable implementation
└── metadata.json     ← Operational metadata (creation, usage, health)
```

---

## 3. The Skill Spec (spec.yaml)

This is the canonical schema every skill must conform to. The LLM uses this file — not the code — to decide whether to invoke a skill.

```yaml
# ─────────────────────────────────────────────────────────────
# SKILL SPECIFICATION — spec.yaml
# ─────────────────────────────────────────────────────────────

name: query_order_status

# One sentence: what this skill does. Written for the LLM to read.
description: >
  Retrieves the current status, lifecycle position, and fulfillment
  summary of an order from AdventureWorks by order ID.

# READ: no external side effects. WRITE: modifies external state.
classification: READ

# When does the agent use this skill?
trigger:
  modes: [assist, act, monitor]      # which agent modes may invoke this
  intent_signals:                    # natural language phrases that suggest this skill
    - "order status"
    - "what happened with order"
    - "order state"
    - "is the order shipped"

# What this skill needs to run
inputs:
  - name: order_id
    type: integer
    required: true
    description: "The AdventureWorks SalesOrderHeader ID"

# What this skill returns — feeds into next skill in chain
outputs:
  - name: order_status
    type: object
    description: "Subset of the Unified Order Schema (status + fulfillment fields)"
    schema_ref: "UnifiedOrderSchema.status"

# External dependencies this skill requires
dependencies:
  - type: database
    name: adventureworks
    connection_env: "DATABASE_URL"
  - type: python_package
    name: psycopg2

# Domain for registry indexing
domain: sales

# For Monitor mode: does this skill run on a schedule?
trigger_type: on_demand    # on_demand | persistent | monitor_rule

# Registry-level constraints
constraints:
  max_execution_time_ms: 3000
  requires_approval: false
  safe_to_retry: true
```

---

## 4. The Skill Implementation (code.py)

All skills inherit from `BaseSkill` and implement a single `execute()` method. The interface is fixed — the implementation is free.

```python
# skills/base_skill.py  — the contract every skill must fulfill

from abc import ABC, abstractmethod
from typing import Any
from dataclasses import dataclass

@dataclass
class SkillResult:
    success: bool
    data: Any                    # The output — passed to next skill in chain
    error: str | None = None
    execution_ms: int = 0
    skill_name: str = ""

class BaseSkill(ABC):
    """
    Every skill — built-in or AutoSkill-generated — inherits from this.
    The agent calls execute(inputs) and gets a SkillResult back.
    """

    @abstractmethod
    def execute(self, inputs: dict) -> SkillResult:
        """
        Run the skill. Must be deterministic for the same inputs.
        Must not have side effects if classification=READ.
        Must create an approval entry before any external mutation if classification=WRITE.
        """
        pass

    @classmethod
    def mock_execute(cls, inputs: dict) -> SkillResult:
        """
        Used by the AutoSkill sandbox validator.
        Subclasses may override to provide mock responses.
        """
        raise NotImplementedError("Skill must implement mock_execute for sandbox validation")
```

```python
# skills/builtin/query_order_status/code.py  — example implementation

import time
import psycopg2
from skills.base_skill import BaseSkill, SkillResult

class QueryOrderStatus(BaseSkill):

    def execute(self, inputs: dict) -> SkillResult:
        start = time.time()
        order_id = inputs["order_id"]

        try:
            conn = psycopg2.connect(os.environ["DATABASE_URL"])
            cur = conn.cursor()
            cur.execute("""
                SELECT
                    soh.salesorderid,
                    soh.status,
                    soh.orderdate,
                    soh.shipdate,
                    soh.totaldue,
                    soh.comment,
                    EXTRACT(EPOCH FROM (NOW() - soh.modifieddate)) / 3600 AS hours_since_update
                FROM sales.salesorderheader soh
                WHERE soh.salesorderid = %s
            """, (order_id,))
            row = cur.fetchone()

            if not row:
                return SkillResult(success=False, error=f"Order {order_id} not found",
                                   skill_name="query_order_status")

            status_map = {1: "placed", 2: "processing", 3: "cancelled",
                          4: "rejected", 5: "shipped", 6: "delivered"}

            data = {
                "order_id": row[0],
                "status": status_map.get(row[1], "unknown"),
                "status_code": row[1],
                "order_date": str(row[2]),
                "ship_date": str(row[3]) if row[3] else None,
                "total": float(row[4]),
                "hours_since_update": float(row[6]),
                "is_stale": float(row[6]) > 48
            }

            return SkillResult(success=True, data=data,
                               execution_ms=int((time.time() - start) * 1000),
                               skill_name="query_order_status")

        except Exception as e:
            return SkillResult(success=False, error=str(e),
                               skill_name="query_order_status")
        finally:
            if conn:
                conn.close()

    @classmethod
    def mock_execute(cls, inputs: dict) -> SkillResult:
        return SkillResult(success=True, data={
            "order_id": inputs["order_id"],
            "status": "processing",
            "status_code": 2,
            "order_date": "2024-01-08",
            "ship_date": None,
            "total": 3578.27,
            "hours_since_update": 168.0,
            "is_stale": True
        }, skill_name="query_order_status")
```

---

## 5. The Skill Metadata (metadata.json)

Operational data that the registry tracks. Updated automatically after each execution.

```json
{
  "skill_name": "query_order_status",
  "created_at": "2024-01-10T09:00:00Z",
  "author": "human",
  "version": "1.0.0",
  "usage": {
    "total_invocations": 47,
    "last_invoked": "2024-01-15T14:00:00Z",
    "success_rate": 0.98,
    "avg_execution_ms": 124
  },
  "health": "ok",
  "tags": ["sales", "order", "status", "read"]
}
```

---

## 6. Seed Skills — The Hardcoded Starting Set

These 8 skills ship with the system. They are not generated — they are hand-written and cover the complete MVP use case.

| # | Skill Name | Classification | Domain | MCP Server | Description |
|---|-----------|----------------|--------|-----------|-------------|
| 1 | `query_order_status` | READ | Sales | — | Get order status and lifecycle position from AdventureWorks |
| 2 | `get_customer_info` | READ | Customer | — | Get customer name, email, phone from AdventureWorks person schema |
| 3 | `list_order_items` | READ | Sales | — | List all line items with product details, quantity, price, and margin |
| 4 | `check_inventory` | READ | Production | — | Check current stock level for a product ID |
| 5 | `get_tiendanube_order` | READ | E-commerce | `tiendanube` | Fetch order details from the live Tiendanube store via MCP |
| 6 | `detect_stale_orders` | READ | Monitor | — | Scan all orders and return those violating stale-state thresholds |
| 7 | `draft_whatsapp_message` | READ | Comms | — | LLM-generates a WhatsApp message from spine context. Returns text, never sends. |
| 8 | `send_whatsapp_message` | **WRITE** | Comms | `whatsapp` | Send a WhatsApp message via Twilio/Meta API. Always requires approval. |

### Seed Skill Input/Output Contracts

```
query_order_status
  IN:  { order_id: int }
  OUT: { order_id, status, order_date, ship_date, total, is_stale, hours_since_update }

get_customer_info
  IN:  { order_id: int }
  OUT: { customer_id, full_name, email, phone, whatsapp_eligible }

list_order_items
  IN:  { order_id: int }
  OUT: { items: [{ product_id, product_name, sku, quantity, unit_price, standard_cost, margin_pct, stock_available }] }

check_inventory
  IN:  { product_id: int }
  OUT: { product_id, product_name, stock_available, stock_status: "ok"|"low"|"out" }

get_tiendanube_order
  IN:  { order_id: str }     ← Tiendanube order ID (e.g., "TN-9981")
  OUT: { tiendanube_order: object }   ← Raw MCP response, merged into spine._meta

detect_stale_orders
  IN:  { }   ← no inputs, scans all active orders
  OUT: { stale_orders: [{ order_id, status, hours_in_status, alert_level, customer_name }] }

draft_whatsapp_message
  IN:  { spine_object: UnifiedOrder, context: str, tone: "formal"|"friendly" }
  OUT: { message_text: str, word_count: int }

send_whatsapp_message
  IN:  { phone: str, message: str, approval_id: str }   ← approval_id REQUIRED
  OUT: { message_id: str, status: "sent"|"failed", timestamp: str }
```

---

## 7. The AutoSkill Loop — Self-Improvement Flow

### 7.1 When It Activates

The AutoSkill loop activates when the **Planner** cannot find a skill that satisfies a step in the plan. This is not an error — it is a growth signal.

```
Planner step: "Calculate the margin for each item in order 43659"
Registry search: no skill found for "margin calculation"
AutoSkill loop: ACTIVATED
```

### 7.2 The Full Synthesis Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         AUTOSKILL LOOP                                  │
└─────────────────────────────────────────────────────────────────────────┘

STEP 1 — GAP DETECTION
─────────────────────
  Planner identifies a required capability with no matching skill.
  
  Gap record created:
  {
    "gap_id": "GAP-001",
    "description": "Calculate gross margin for all items in an order",
    "detected_in": "PLN-0017",
    "context": "User asked 'how much margin does order 43659 have?'"
  }
  
         │
         ▼

STEP 2 — SCHEMA RESEARCH
─────────────────────────
  The agent reads the AdventureWorks schema for relevant tables.
  No external API calls — for the MVP, research is schema-only.
  
  Research query: "Find tables and columns related to cost, price, margin in orders"
  
  Findings:
  - sales.salesorderdetail.unitprice       ← selling price per unit
  - sales.salesorderdetail.orderqty        ← quantity
  - production.product.standardcost        ← cost basis
  - sales.salesorderdetail.salesorderid   ← join key
  
  Research artifact:
  {
    "gap_id": "GAP-001",
    "schema_findings": ["sales.salesorderdetail", "production.product"],
    "computation": "margin = (unitprice - standardcost) / unitprice * 100",
    "join_path": "salesorderdetail JOIN product ON productid"
  }
  
         │
         ▼

STEP 3 — SKILL GENERATION (LLM)
──────────────────────────────
  The LLM receives: gap description + schema findings + BaseSkill template
  The LLM generates: spec.yaml + code.py + mock_execute()
  
  Prompt template (condensed):
  """
  You are generating a new skill for the SpineAgent system.
  
  GAP: {gap.description}
  SCHEMA: {research.schema_findings}
  COMPUTATION: {research.computation}
  
  Generate:
  1. spec.yaml — following the schema in SKILL_SCHEMA_AND_REGISTRY.md
  2. code.py   — inheriting from BaseSkill, implementing execute() and mock_execute()
  
  Rules:
  - classification must be READ (this skill only queries data)
  - mock_execute() must return realistic data for order_id=43659
  - SQL must use parameterized queries only (no f-strings with user data)
  - No external imports beyond: psycopg2, os, time, dataclasses
  """
  
         │
         ▼

STEP 4 — SANDBOX VALIDATION
────────────────────────────
  The generated skill is NOT registered yet. It runs in isolation.
  
  Validation checks:
  a. Syntax check: can the Python file be imported without error?
  b. Schema check: does spec.yaml have all required fields?
  c. Classification check: is this READ? (if WRITE — reject, flag for human review)
  d. Mock run: skill.mock_execute({"order_id": 43659}) → does it return SkillResult?
  e. SQL safety check: does the SQL contain any parameterization bypass?
  
  If ALL checks pass → proceed to Step 5
  If ANY check fails → return to Step 3 with failure context (max 2 retries)
  
         │
         ▼

STEP 5 — HUMAN APPROVAL (for the demo moment)
──────────────────────────────────────────────
  Even though this is a READ skill, generating new agent code is a 
  significant action. The system presents the generated skill to the human.
  
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  NEW SKILL GENERATED — Approval Required
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Skill: calculate_order_margin
  Classification: READ
  Sandbox: PASSED (4/4 checks)
  
  Description: "Calculates gross margin % and absolute margin for each 
  line item and the total order using standardcost and unitprice."
  
  SQL Preview:
    SELECT sod.salesorderid, p.name, sod.unitprice, p.standardcost,
           ROUND(((sod.unitprice - p.standardcost) / sod.unitprice * 100)::numeric, 1) AS margin_pct
    FROM sales.salesorderdetail sod
    JOIN production.product p ON sod.productid = p.productid
    WHERE sod.salesorderid = $1
  
  [ APPROVE & REGISTER ]  [ REJECT ]
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

         │
         ▼

STEP 6 — REGISTRY PERSISTENCE
──────────────────────────────
  On approval:
  - Write files to skills/generated/calculate_order_margin/
  - Insert registry entry into SQLite skills table
  - Set metadata.json: author="agent", version="1.0.0"
  
         │
         ▼

STEP 7 — EXECUTION & FEEDBACK
───────────────────────────────
  The original plan resumes. The new skill is executed immediately.
  
  Result is logged to Context Store:
  {
    "entry_type": "autoskill_generation",
    "gap_id": "GAP-001",
    "skill_generated": "calculate_order_margin",
    "outcome": "success",
    "first_result": { ... }
  }
  
  Next time the Planner needs margin calculation → skill already exists.
```

### 7.3 AutoSkill Safety Constraints (Non-Negotiable)

The AutoSkill loop is the most powerful and dangerous part of the system. These constraints are hardcoded:

1. **AutoSkill may only generate READ-classified skills.** A generated skill that attempts database writes, API mutations, or file system changes is rejected at Step 4 regardless of how valid it looks.

2. **AutoSkill research is schema-only for the MVP.** No external API calls, no web scraping. The only research source is the local AdventureWorks schema. This prevents the agent from pulling in arbitrary external code.

3. **The generated code runs in a subprocess with a 5-second timeout.** If it hangs, it fails.

4. **Maximum 2 generation retries per gap.** If the LLM cannot produce a valid skill in 2 attempts, the loop surfaces the gap to the human as an unresolved capability request — and stops.

5. **Generated skills cannot import the skills module.** A generated skill cannot modify the registry from within its own execute(). Registry writes go through `autoskill/validator.py` only.

---

## 8. Registry Implementation (SQLite)

For hackathon speed, the registry index lives in SQLite alongside the filesystem.

```sql
CREATE TABLE skill_registry (
    skill_name      TEXT PRIMARY KEY,
    description     TEXT NOT NULL,
    classification  TEXT NOT NULL CHECK (classification IN ('READ', 'WRITE')),
    domain          TEXT NOT NULL,
    trigger_type    TEXT NOT NULL,
    author          TEXT NOT NULL CHECK (author IN ('human', 'agent')),
    version         TEXT NOT NULL,
    file_path       TEXT NOT NULL,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_invoked    DATETIME,
    total_invocations INTEGER DEFAULT 0,
    success_rate    REAL DEFAULT 1.0,
    health          TEXT DEFAULT 'ok'
);
```

### Registry Search (used by Planner)

```python
def find_skill(query: str, mode: str) -> list[SkillSpec]:
    """
    Given a natural language description of what we need,
    return the best matching skills.
    
    For MVP: keyword match on description + domain filter.
    Post-MVP: replace with vector similarity search.
    """
```

---

## 9. The Demo Moment Checklist

For the live AutoSkill demo to work perfectly, these conditions must be met:

- [ ] `calculate_order_margin` does NOT exist in the registry before the demo starts
- [ ] The Planner must correctly identify the gap when asked about margin
- [ ] The research step must correctly identify `standardcost` and `unitprice` from schema
- [ ] The generated SQL must produce correct results against AdventureWorks data for order `43659`
- [ ] The approval gate must display the generated code cleanly in the CLI
- [ ] After approval, the skill must execute and return real margin data

Pre-demo: run `demo/reset_autoskill_demo.py` which removes `calculate_order_margin` from registry to ensure a clean slate.
