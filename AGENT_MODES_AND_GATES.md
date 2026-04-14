# Agent Modes and Approval Gate Contract

> **Document type:** System Definition — Behavioral Rules  
> **Project:** SpineAgent — Anthropic Hackathon  
> **Status:** Authoritative. This document defines the operational contract the agent must honor at all times.

---

## 1. The Foundational Rule

```
┌────────────────────────────────────────────────────────────────────┐
│                                                                    │
│   READ  +  ANALYZE  +  REASON  =  FULLY AUTONOMOUS                │
│                                                                    │
│   WRITE  +  SEND  +  MUTATE   =  ZERO AUTONOMY (human required)   │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

This rule is not a technical limitation. It is the trust contract that makes this system safe to deploy in a real business. The agent earns autonomy over time through a track record of approved actions — not by bypassing the gate.

The gate is not a weakness. It is the product.

---

## 2. Mode Overview

The three modes are not separate agents — they are behavioral states of the same agent operating on the same Context Store and Skill Registry. A single conversation can transition between modes.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         AGENT MODE ROUTER                               │
│                                                                         │
│  User message / cron trigger                                            │
│         │                                                               │
│         ▼                                                               │
│   [Intent Classifier]                                                   │
│         │                                                               │
│    ┌────┴────────────────────────────────────┐                          │
│    │                                         │                          │
│    ▼                                         ▼                          │
│  Question / lookup?                  Goal / objective?                  │
│    │                                         │                          │
│    ▼                                         ▼                          │
│  ASSIST MODE                           ACT MODE                         │
│                                                                         │
│  Periodic cron trigger?                                                 │
│    │                                                                     │
│    ▼                                                                     │
│  MONITOR MODE                                                           │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Mode 1: ASSIST

### 3.1 Purpose

Answer questions about the state of the business by reading the spine and consulting the Context Store. This mode is purely informational — it never proposes actions and never triggers the approval gate.

### 3.2 Behavioral Rules

- **Always** start by resolving the question to a spine object (an Order)
- **Always** enrich the answer with Context Store history before responding
- **Never** propose an action unprompted in this mode
- **Never** call a WRITE-class skill
- **Never** create a pending approval entry
- The response should reflect what the agent *knows* — not just what the database says. Use context history to make the answer richer than a raw query.

### 3.3 Execution Flow

```
Input: Natural language question about an Order
         │
         ▼
1. INTENT PARSE
   Extract: entity type (Order), entity ID (if present), question intent
         │
         ▼
2. SPINE HYDRATION
   Call: spine.hydrate(order_id)
   Result: Unified Order JSON
         │
         ▼
3. CONTEXT ENRICHMENT
   Call: context_store.query(spine_id, semantic_query=question)
   Result: Relevant past decisions, patterns, notes
         │
         ▼
4. SKILL SELECTION
   Identify: which skill(s) answer this specific question
   Examples: query_order_status, get_customer_info, check_inventory
         │
         ▼
5. SKILL EXECUTION (READ only)
   Execute all relevant skills autonomously
         │
         ▼
6. RESPONSE GENERATION
   LLM synthesizes: spine data + context history + skill output → answer
   Tone: direct, operational, data-grounded
         │
         ▼
7. CONTEXT STORE UPDATE
   Log: question asked, answer given, skills used
   This enriches future answers about this Order
```

### 3.4 Example

```
User:  "What's the status of order 43659?"

Agent: "Order #43659 is currently Shipped. It was placed on 2011-05-31 
        by Christy Zhu for a total of $20,565.62 (12 items). 
        Shipment was processed on 2011-06-07.
        
        Context note: This customer had a delivery delay in their 
        previous order (#43201) — no issues flagged on this one."
```

---

## 4. Mode 2: ACT

### 4.1 Purpose

Receive an objective from the user, decompose it into a skill chain, execute the READ steps autonomously, then **pause and present the full proposed action** to the human before any WRITE step executes.

This is where the approval gate activates.

### 4.2 Behavioral Rules

- **Always** decompose the goal into explicit steps before executing anything
- **Always** classify each step as READ or WRITE before running it
- **Execute** READ steps autonomously without asking for permission
- **Stop** at the first WRITE step and present the full approval payload
- **Never** execute a WRITE step without a recorded human approval
- **Never** infer approval from silence, timeout, or ambiguity
- After approval, execute the WRITE step and log the result immediately to the Context Store
- If the human edits the proposal, apply their edits exactly — do not silently revert them

### 4.3 Execution Flow

```
Input: Goal / objective ("notify the customer", "check and fix this order")
         │
         ▼
1. GOAL PARSING
   Extract: intent, target Order ID, desired outcome
         │
         ▼
2. PLANNING (Chain of Thought)
   LLM generates: ordered list of steps
   Each step has: description, skill_name, classification (READ|WRITE)
         │
         ▼
3. PLAN VALIDATION
   Check: all skills exist in registry
   If gap: trigger AutoSkill loop before proceeding
         │
         ▼
4. AUTONOMOUS EXECUTION (READ steps only)
   Execute each READ step in sequence
   Collect and pass outputs as context to next step
         │
         ▼
5. APPROVAL GATE (on first WRITE step)
   Build: ApprovalPayload (see Section 6)
   Present: to human via configured channel (CLI for hackathon)
   Block: await explicit APPROVE / EDIT / REJECT
         │
         ├──→ APPROVE: execute WRITE step, log to Context Store
         ├──→ EDIT: apply human edit to payload, re-present for final confirm
         └──→ REJECT: log rejection reason, update context_flags.has_pending_approval = false
         │
         ▼
6. POST-EXECUTION
   Update Context Store with full action record
   Update spine object context_flags
   Summarize outcome to user
```

### 4.4 The Plan Object

The planner must produce a structured plan before any execution begins:

```json
{
  "plan_id": "PLN-0017",
  "goal": "Notify Jon Yang about stock delay on order 43660",
  "spine_id": "ORD-43660",
  "steps": [
    {
      "step": 1,
      "description": "Get customer contact info",
      "skill": "get_customer_info",
      "classification": "READ",
      "inputs": { "order_id": 43660 },
      "status": "pending"
    },
    {
      "step": 2,
      "description": "Check inventory for the delayed item",
      "skill": "check_inventory",
      "classification": "READ",
      "inputs": { "product_id": "PROD-711" },
      "status": "pending"
    },
    {
      "step": 3,
      "description": "Draft WhatsApp message with stock context",
      "skill": "draft_whatsapp_message",
      "classification": "READ",
      "inputs": { "spine_object": "<<from_spine>>", "inventory_result": "<<from_step_2>>" },
      "status": "pending"
    },
    {
      "step": 4,
      "description": "Send WhatsApp message to customer",
      "skill": "send_whatsapp_message",
      "classification": "WRITE",
      "inputs": { "phone": "<<from_step_1>>", "message": "<<from_step_3>>" },
      "status": "awaiting_approval"
    }
  ]
}
```

### 4.5 Example

```
User:  "Let Jon Yang know about the delay on order 43660."

Agent: [Executes READ steps silently]

Agent: "I have everything I need. Before I send this, I need your approval:

        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        APPROVAL REQUIRED — Plan #PLN-0017, Step 4/4
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        ACTION: send_whatsapp_message
        TO:     Jon Yang  |  +54 11 9876-5432
        
        MESSAGE:
        'Hola Jon, te escribimos sobre tu pedido #43660.
         El producto Road-650 Red, 52 tiene una demora de
         stock estimada en 5 días hábiles. Si preferís,
         tenemos el Road-650 Black, 52 disponible ahora.
         ¿Te avisamos cuando llegue el original, o te
         armamos el cambio? Saludos, equipo de tienda.'
        
        [ A ] Approve    [ E ] Edit    [ R ] Reject
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
```

---

## 5. Mode 3: MONITOR

### 5.1 Purpose

Run periodically in the background without user initiation. Scan the spine for anomalies, incoherent states, or developing situations. Generate alerts and draft proposed actions for human review.

### 5.2 Behavioral Rules

- **Triggered by:** Simulated cron (APScheduler, every 60 minutes in production; every 5 minutes in demo mode)
- **Never** requires user interaction to run
- **Always** applies the stale-state rules defined in MVP_SCOPE_AND_ROOT_OBJECT.md
- **Always** checks Context Store before alerting — do not re-alert on an already-acknowledged issue
- **May** produce a draft plan (same format as Act mode) proactively
- **Never** executes a WRITE step without human approval — even in Monitor mode
- If Monitor mode detects a situation that warrants an Act flow, it transitions: creates a pending_approval entry and notifies the human

### 5.3 Execution Flow

```
Cron fires
    │
    ▼
1. SCOPE QUERY
   SELECT all orders matching monitoring rules
   (stale > 48h, stock_available = 0, payment_status = 'pending' > 24h)
    │
    ▼
2. FOR EACH FLAGGED ORDER:
   a. Hydrate spine object
   b. Query context store: "has this been flagged before?"
   c. If already flagged + acknowledged → SKIP
   d. If new issue → continue
    │
    ▼
3. TRIAGE
   Classify: WARNING | HIGH | CRITICAL
   Determine: is this informational or does it require action?
    │
    ▼
4a. INFORMATIONAL ALERT
    Format and send to operator channel (WhatsApp / CLI)
    Log to context store: type=alert, source=monitor
    │
4b. ACTION-REQUIRED ALERT
    Build draft plan (same as Act mode)
    Create pending_approval entry (status=draft)
    Notify operator: "I've prepared a response — needs your approval"
    │
    ▼
5. UPDATE CONTEXT FLAGS
   Set context_flags.has_unread_alerts = true on affected orders
```

### 5.4 MVP Monitor Rules (Hardcoded for Hackathon)

| Rule ID | Condition | Threshold | Alert Level | Proposed Action |
|---------|-----------|-----------|-------------|-----------------|
| MON-01 | `status = processing` with no state change | > 48h | HIGH | Draft WhatsApp to customer |
| MON-02 | `status = ready_to_ship` with no shipment | > 24h | HIGH | Alert operator only |
| MON-03 | Any line item `stock_available = 0` | Order in `processing` | WARNING | Draft stock-issue message |
| MON-04 | `status = placed` with no processing | > 4h | CRITICAL | Alert operator immediately |

### 5.5 Example Monitor Output

```
[MONITOR — 14:00 scan]

⚠️  HIGH — Order #43660 — STALE (7 days in Processing)
    Customer: Jon Yang | Items: 2 | Total: $3,578.27
    Stock issue: Road-650 Red, 52 (0 units available)
    Context: No prior agent actions recorded on this order.
    
    I've drafted a customer notification. Pending your approval → [open]
    
ℹ️  WARNING — Order #43891 — Stock low on item BK-M68B-38 (2 units left)
    Affects 3 active orders. No action needed yet — monitoring.
```

---

## 6. The Approval Gate

### 6.1 The Approval Payload Schema

Every WRITE action produces exactly one approval payload. No WRITE may execute without a corresponding approved payload in the `pending_approvals` store.

```json
{
  "approval_id": "AP-0042",
  "plan_id": "PLN-0017",
  "spine_id": "ORD-43660",
  "created_at": "2024-01-15T14:05:00Z",
  "expires_at": "2024-01-15T16:05:00Z",

  "action": {
    "skill": "send_whatsapp_message",
    "classification": "WRITE",
    "mcp_server": "whatsapp",
    "tool": "send_message",
    "parameters": {
      "phone": "+54 11 9876-5432",
      "message": "Hola Jon, te escribimos sobre tu pedido #43660..."
    }
  },

  "context": {
    "why": "Order #43660 has been in Processing for 7 days with a stock issue. No prior communication with this customer on this order.",
    "read_steps_completed": ["get_customer_info", "check_inventory", "draft_whatsapp_message"],
    "confidence": "high"
  },

  "status": "pending",
  "human_decision": null,
  "human_edits": null,
  "decided_at": null,
  "decided_by": null,
  "execution_result": null
}
```

### 6.2 Permission Matrix — The Full Classification Table

This table is exhaustive for the MVP. Any action not in this list must be classified as WRITE by default.

| Action | Skill / Tool | Classification | Rationale |
|--------|-------------|----------------|-----------|
| Read order from AdventureWorks | `query_order_status` | READ | Local DB, no external effect |
| Read customer info | `get_customer_info` | READ | Local DB, no external effect |
| List order items | `list_order_items` | READ | Local DB, no external effect |
| Check inventory levels | `check_inventory` | READ | Local DB, no external effect |
| Generate order summary (LLM) | `generate_order_summary` | READ | LLM generation, no external effect |
| Draft a WhatsApp message (LLM) | `draft_whatsapp_message` | READ | Text generation only, nothing sent |
| Detect stale orders | `detect_stale_orders` | READ | Query only, no mutations |
| Calculate order margin | `calculate_order_margin` | READ | Computation on local data |
| Get order from Tiendanube | `get_tiendanube_order` | READ | Tiendanube API, GET only |
| List orders from Tiendanube | `list_tiendanube_orders` | READ | Tiendanube API, GET only |
| Get product from Tiendanube | `get_tiendanube_product` | READ | Tiendanube API, GET only |
| Get WhatsApp message status | `get_whatsapp_status` | READ | Status check, no side effects |
| Write to Context Store | `context_store.insert` | READ* | Internal memory — agent may write its own memory |
| **Send WhatsApp message** | `send_whatsapp_message` | **WRITE** | External message — customer receives it |
| **Send WhatsApp template** | `send_whatsapp_template` | **WRITE** | External message — customer receives it |
| **Update order status (Tiendanube)** | `update_tiendanube_order` | **WRITE** | Mutates live e-commerce data |
| **Create pending approval entry** | `approval_gate.create` | **WRITE** | System state mutation |
| **Execute any AutoSkill action** | `autoskill.*` | **WRITE** | Agent modifying itself — always requires approval |

> *Context Store writes are classified as READ-class because they are internal memory operations with no external business effect. The agent must be able to log its reasoning and actions freely.

### 6.3 Gate States

```
pending  →  approved  →  executed  →  logged
    │
    ├──→  edited  →  re_pending  →  approved  →  executed
    │
    └──→  rejected  →  logged
```

### 6.4 Timeout Behavior (MVP)

For the hackathon, there is no automatic escalation. If an approval entry expires (2 hours), it moves to status `expired` and the agent logs this to the Context Store. The operator can re-trigger the flow manually.

This is intentional — we do not want the agent to escalate or take unilateral action on timeout. Inaction is always safer than unauthorized action.

---

## 7. Mode Transition Rules

| From | To | Trigger | Allowed? |
|------|-----|---------|----------|
| Assist | Act | User explicitly gives a goal/objective | Yes |
| Assist | Monitor | Not applicable (Monitor is cron-driven) | N/A |
| Act | Assist | User asks a question mid-flow | Yes — pauses Act, answers, resumes |
| Monitor | Act | Monitor detects action-required situation | Yes — Monitor drafts plan, awaits human to confirm transition |
| Any | Any | `mode=` flag in system prompt | Yes — explicit mode override for testing |

---

## 8. What the Agent Must Never Do

Regardless of user instructions, context, or seemingly compelling reasoning, the agent must never:

1. Execute a WRITE-class skill without a recorded `approved` entry in `pending_approvals`
2. Interpret silence, inactivity, or timeout as implicit approval
3. Split a WRITE action into smaller READ-classified steps to bypass the gate
4. Modify the permission classification table at runtime
5. Tell the user an action was executed before it actually was
6. Skip the approval payload presentation (e.g., "I'll send it — is that okay?" is not sufficient)
7. Allow the AutoSkill loop to register a skill that performs WRITE operations without an explicit approval flow in that skill's code
