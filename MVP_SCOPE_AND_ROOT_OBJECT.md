# MVP Scope and Root Object Definition

> **Document type:** System Definition  
> **Project:** SpineAgent — Anthropic Hackathon  
> **Status:** Authoritative. Any deviation from this document must be explicitly discussed and recorded.

---

## 1. The Prime Directive of This Weekend

We are building **one complete, demo-able flow** — not a feature-complete system. Every architectural decision must be evaluated against this question:

> *Does this get us to the Magic Demo faster, or does it get in the way?*

If something is not listed in this document as **IN SCOPE**, it does not exist this weekend.

---

## 2. The Root Object: The Order

### 2.1 Definition

The **Order** is the operational spine of this system. It is the single entity that crosses every functional domain simultaneously:

- **Sales domain:** order placed, pricing, discounts
- **Inventory/Production domain:** stock availability, fulfillment status  
- **Customer domain:** who ordered, how to contact them
- **Logistics domain:** shipment state, delivery ETA

The Order is chosen as the root object because it has the highest density of cross-domain references. Any anomaly in the business manifests as an anomaly in an Order's state.

### 2.2 Data Sources for the MVP

The Order object is hydrated from two sources:

| Source | Role | Access Method |
|--------|------|---------------|
| **AdventureWorks (PostgreSQL)** | Local structured data — order details, inventory, customer info | Direct SQL queries via Python |
| **Tiendanube** | Live e-commerce platform — real order states, customer-facing data | MCP Server (`tiendanube`) |

> **Decision:** AdventureWorks is the **authoritative data source for demo data**. Tiendanube MCP is the **live integration that proves real-world connectivity**. The demo script maps AdventureWorks order IDs to plausible Tiendanube representations.

---

## 3. The Unified Order Schema (The Spine Object)

This is the canonical JSON structure that represents a fully-resolved Order. Every agent mode, every skill, and every approval payload operates on this object — never on raw database rows.

```json
{
  "spine_id": "ORD-43659",
  "source_id": {
    "adventureworks": 43659,
    "tiendanube": "TN-9981"
  },
  "snapshot_at": "2024-01-15T10:30:00Z",

  "status": {
    "current": "shipped",
    "previous": "processing",
    "last_updated": "2024-01-14T08:00:00Z",
    "days_in_current_status": 1,
    "is_stale": false,
    "stale_threshold_hours": 48
  },

  "customer": {
    "id": "CUST-291",
    "full_name": "Christy Zhu",
    "email": "christy.zhu@example.com",
    "phone": "+54 11 1234-5678",
    "whatsapp_eligible": true
  },

  "financials": {
    "subtotal": 18432.50,
    "tax": 2133.12,
    "total": 20565.62,
    "currency": "ARS",
    "payment_status": "paid"
  },

  "line_items": [
    {
      "product_id": "PROD-776",
      "product_name": "Mountain-200 Black, 38",
      "sku": "BK-M68B-38",
      "quantity": 1,
      "unit_price": 2024.99,
      "standard_cost": 1251.97,
      "margin_pct": 38.2,
      "stock_available": 12,
      "stock_status": "ok"
    }
  ],

  "fulfillment": {
    "assigned_to": "sales_rep_id_285",
    "warehouse": "WH-NORTH",
    "shipment_id": "SHIP-74831",
    "carrier": "OCA",
    "tracking_number": "OCA-123456789",
    "estimated_delivery": "2024-01-18"
  },

  "context_flags": {
    "has_stock_issue": false,
    "has_pending_approval": false,
    "has_unread_alerts": false,
    "autoskill_ran": false
  },

  "context_history_summary": "Order created 2024-01-10. Operator Tato approved WhatsApp dispatch notification on 2024-01-14. Customer confirmed receipt preference via WhatsApp.",

  "_meta": {
    "hydrated_from": ["adventureworks", "tiendanube"],
    "hydration_errors": [],
    "spine_version": "1.0"
  }
}
```

### 3.1 Field Ownership

| Field Group | Owner | Mutable by Agent? |
|-------------|-------|-------------------|
| `status` | Tiendanube / AW | READ ONLY — agent observes, never mutates directly |
| `customer` | AdventureWorks `person` schema | READ ONLY |
| `financials` | AdventureWorks `sales` schema | READ ONLY |
| `line_items` | AdventureWorks `salesorderdetail` + `productinventory` | READ ONLY |
| `fulfillment` | AdventureWorks `shipment` | READ ONLY |
| `context_flags` | Agent (Context Store) | READ/WRITE — agent updates these |
| `context_history_summary` | Context Store (generated) | WRITE — agent appends |

---

## 4. The Order Lifecycle

The following state machine defines valid Order status transitions. The agent must understand this graph to reason about what is and is not anomalous.

```
         ┌──────────────────────────────────────────────────────┐
         │                   ORDER LIFECYCLE                     │
         └──────────────────────────────────────────────────────┘

  [placed] ──→ [processing] ──→ [ready_to_ship] ──→ [shipped] ──→ [delivered]
      │              │                 │                  │              │
      │         (anomaly zone)    (anomaly zone)          │         [completed]
      │         > 48h = STALE     > 24h = STALE           │
      │                                                    │
      └──────────────→ [cancelled] ←──────────────────────┘
                             │
                       [refund_pending] ──→ [refunded]
```

### 4.1 Stale State Rules (for Monitor Mode)

| Status | Stale Threshold | Alert Level |
|--------|----------------|-------------|
| `processing` | > 48 hours | WARNING |
| `ready_to_ship` | > 24 hours | HIGH |
| `shipped` with no tracking update | > 72 hours | WARNING |
| `placed` with no processing | > 4 hours | CRITICAL |

---

## 5. The MVP Use Case (The Canonical Demo Flow)

### Scenario: Stock Issue Detection → Draft Solution → Human Approval → WhatsApp Notification

This is the one scenario we will demo perfectly. Everything we build must serve this flow.

```
TRIGGER (Monitor Mode — simulated cron)
  └─→ Agent scans orders, detects: Order #43660 has line item with stock_available = 0
                                    Status has been "processing" for 7 days
                                    No context history recorded for this issue

DETECT (Autonomous — READ only)
  └─→ Agent reads full spine object for Order #43660
  └─→ Agent reads context store: no prior decisions recorded
  └─→ Agent classifies: STOCK ISSUE requiring customer communication

REASON (Autonomous — internal chain of thought)
  └─→ "The item 'Road-650 Red, 52' is out of stock."
  └─→ "The order has been stuck for 7 days — customer is waiting."
  └─→ "Best action: notify customer with ETA or offer alternatives."
  └─→ "I need: customer WhatsApp number ✓ | message draft ✓ | send_message skill ✓"

PLAN (Autonomous — builds action chain)
  Step 1: get_customer_info(order_id=43660)            [READ — autonomous]
  Step 2: check_inventory(product_id=PROD-711)         [READ — autonomous]
  Step 3: draft_whatsapp_message(context=spine_object) [READ — autonomous, LLM generates text]
  Step 4: send_whatsapp_message(phone, message)        [WRITE — REQUIRES APPROVAL]

APPROVAL GATE (Blocks on Step 4)
  └─→ Presents to human:
      ┌─────────────────────────────────────────────────┐
      │ PENDING APPROVAL — Action #AP-0042              │
      │                                                  │
      │ Skill: send_whatsapp_message                     │
      │ To: Jon Yang (+54 11 9876-5432)                  │
      │ Message:                                         │
      │   "Hola Jon, te escribimos sobre tu pedido       │
      │    #43660. El producto 'Road-650 Red, 52'        │
      │    tiene una demora en stock. Tenemos el         │
      │    'Road-650 Black, 52' disponible como          │
      │    alternativa. ¿Te gustaría el cambio o         │
      │    preferís esperar 5 días hábiles?              │
      │    Quedamos a tu disposición."                   │
      │                                                  │
      │  [ APPROVE ]  [ EDIT ]  [ REJECT ]              │
      └─────────────────────────────────────────────────┘

EXECUTE (Post-approval — WRITE action)
  └─→ Calls WhatsApp MCP: send_message(phone, message)
  └─→ Logs result to Context Store
  └─→ Updates Order spine: context_flags.has_pending_approval = false
  └─→ Appends to context_history_summary
```

---

## 6. What Is IN SCOPE for the MVP

| Feature | Rationale |
|---------|-----------|
| Order as the one root object | It's the entity with most cross-domain density |
| AdventureWorks as the demo database | It's real, relational, and rich enough |
| Tiendanube MCP (read operations only) | `get_order`, `list_orders`, `get_product` |
| WhatsApp MCP (send + draft) | `send_message`, `draft_message` |
| Assist mode (question → answer) | Demonstrates basic intelligence |
| Act mode (objective → plan → approval → execute) | The core value proposition |
| Monitor mode (simulated cron, one rule: stale orders) | Demonstrates proactivity |
| Approval Gate (CLI prompt for hackathon) | Non-negotiable — the trust contract |
| AutoSkill loop (one live generation during demo) | The "magic" moment |
| Context Store (SQLite for hackathon speed) | Persistent memory — enables the rich-context demo |
| Skill Registry (filesystem + SQLite index) | Foundation for self-improvement |
| CLI interface | Sufficient for demo and judging |

---

## 7. What Is EXPLICITLY OUT OF SCOPE

> These items do not exist this weekend. Do not build them. Do not design for them. Do not leave "extension points" for them.

| Out of Scope | Why |
|-------------|-----|
| Multi-object spine (Deal, Case, Project, etc.) | One object only. Prove the concept. |
| Authentication / user management | Not needed for a demo |
| Multi-tenant / multi-store | One store, one spine |
| Real-time webhooks from Tiendanube | Polling + manual trigger is fine for demo |
| Twilio WhatsApp inbound messages (receiving replies) | Send-only for MVP |
| Streamlit dashboard | CLI is sufficient; dashboard is a distraction |
| pgvector / semantic search | Use keyword + structured queries only; vectors add complexity with low demo value |
| AutoSkill with external API research | Demo AutoSkill generates from AdventureWorks schema only |
| Skill versioning / rollback | Not needed for hackathon |
| Production deployment / Dockerfile optimization | Docker Compose runs locally — that's the "deployment" |
| Rate limiting / retry logic | Happy path only for the demo |
| Test suite (unit + integration) | Validate manually; write tests post-hackathon |
| Multi-turn WhatsApp conversation handling | One-shot send only |
| `update_order_status` Tiendanube write operation | Read-only Tiendanube for safety |

---

## 8. The Source of Truth Contract

The Unified Order Schema defined in Section 3 is the **only** representation of an Order that any component in this system may operate on. No component may:

- Query AdventureWorks directly and return raw rows to the agent
- Pass a partial object downstream without flagging it as partial in `_meta`
- Mutate any READ ONLY field — mutations are logged to Context Store, not reflected in the spine

When in doubt, ask: *"Is this change reflected in the spine object?"* If not, it's a Context Store entry, not a spine mutation.
