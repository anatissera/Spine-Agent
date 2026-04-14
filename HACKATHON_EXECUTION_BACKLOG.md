# Hackathon Execution Backlog

> **Document type:** Technical Roadmap  
> **Project:** SpineAgent — Anthropic Hackathon  
> **Status:** Living document. Mark tasks complete as you go. Update blockers in real time.

---

## Operating Principle

We build vertically, not horizontally. At the end of each phase, the system must be able to run a partial demo. We never have a phase that "adds infrastructure" without something running end-to-end.

**Definition of Done for each task:** it runs, produces observable output, and you could demo it if asked right now.

---

## Phase Overview

| Phase | Name | Goal | Done When |
|-------|------|------|-----------|
| **Phase 1** | Scaffolding & Connections | Everything connects | Both MCP servers respond to a test call |
| **Phase 2** | Context Store & Spine | The brain has a body | Ask about an order, get a rich answer |
| **Phase 3** | Main Loop & Approval Gate | The agent does something real | Act mode flow runs end-to-end with gate |
| **Phase 4** | Magic Demo Script | Demo-ready | All 4 demo scenarios run reproducibly |

---

## Phase 1: Scaffolding and MCP Server Connection

**Goal:** Have a running project skeleton where both MCP servers respond to a test call and the database is loaded.

**Exit criteria:** Run `python test_connections.py` and see three green checks: DB, Tiendanube MCP, WhatsApp MCP.

---

### 1.1 — Repository and Docker Setup

- [ ] Create the directory structure from the project plan exactly as defined
- [ ] Write `docker-compose.yml` with:
  - PostgreSQL 16 service with pgvector extension enabled
  - Port 5432 exposed
  - Volume for data persistence
  - Health check on pg_isready
- [ ] Write `requirements.txt`:
  ```
  anthropic>=0.25.0
  psycopg2-binary
  mcp>=0.9.0
  python-dotenv
  apscheduler
  twilio
  requests
  pyyaml
  ```
- [ ] Write `.env.example` with all required keys (no actual values):
  ```
  DATABASE_URL=postgresql://postgres:postgres@localhost:5432/Adventureworks
  ANTHROPIC_API_KEY=
  TIENDANUBE_STORE_ID=
  TIENDANUBE_ACCESS_TOKEN=
  TWILIO_ACCOUNT_SID=
  TWILIO_AUTH_TOKEN=
  TWILIO_WHATSAPP_FROM=
  ```
- [ ] Run `docker-compose up -d` and confirm PostgreSQL is healthy

---

### 1.2 — AdventureWorks Database

- [ ] Clone the AdventureWorks-for-Postgres repo
- [ ] Run the Ruby CSV conversion script
- [ ] Load into the Docker PostgreSQL instance
- [ ] Verify core tables exist:
  ```sql
  SELECT COUNT(*) FROM sales.salesorderheader;          -- expect ~31,465
  SELECT COUNT(*) FROM sales.salesorderdetail;          -- expect ~121,317
  SELECT COUNT(*) FROM production.productinventory;     -- expect ~1,069
  SELECT COUNT(*) FROM person.person;                   -- expect ~19,972
  ```
- [ ] Create the SpineAgent additional schema (single `schema.sql` file):
  ```sql
  -- Context Store
  CREATE TABLE context_entries (
      id              SERIAL PRIMARY KEY,
      spine_id        TEXT NOT NULL,
      entry_type      TEXT NOT NULL,   -- decision|pattern|rule|action_result|alert|autoskill_generation
      content         JSONB NOT NULL,
      source          TEXT NOT NULL,   -- human|agent|system
      created_at      TIMESTAMPTZ DEFAULT NOW()
  );
  CREATE INDEX idx_context_spine ON context_entries(spine_id);
  CREATE INDEX idx_context_type ON context_entries(entry_type);

  -- Pending Approvals
  CREATE TABLE pending_approvals (
      approval_id     TEXT PRIMARY KEY,
      plan_id         TEXT,
      spine_id        TEXT NOT NULL,
      action_skill    TEXT NOT NULL,
      action_params   JSONB NOT NULL,
      context_why     TEXT,
      status          TEXT DEFAULT 'pending',  -- pending|approved|rejected|expired|executed
      human_edits     JSONB,
      created_at      TIMESTAMPTZ DEFAULT NOW(),
      expires_at      TIMESTAMPTZ,
      decided_at      TIMESTAMPTZ,
      decided_by      TEXT,
      execution_result JSONB
  );

  -- Skill Registry Index
  CREATE TABLE skill_registry (
      skill_name      TEXT PRIMARY KEY,
      description     TEXT NOT NULL,
      classification  TEXT NOT NULL,
      domain          TEXT NOT NULL,
      trigger_type    TEXT NOT NULL,
      author          TEXT NOT NULL,
      version         TEXT NOT NULL,
      file_path       TEXT NOT NULL,
      created_at      TIMESTAMPTZ DEFAULT NOW(),
      last_invoked    TIMESTAMPTZ,
      total_invocations INTEGER DEFAULT 0,
      success_rate    REAL DEFAULT 1.0,
      health          TEXT DEFAULT 'ok'
  );
  ```
- [ ] Run `schema.sql` against the database
- [ ] Confirm all tables created with `\dt` in psql

---

### 1.3 — MCP Server: Tiendanube

- [ ] Read the Tiendanube API documentation and identify endpoints for:
  - GET `/orders/{id}` — single order
  - GET `/orders` — list with filters
  - GET `/products/{id}` — product details
- [ ] Write `mcp_servers/tiendanube/server.py`:
  - Use the Python MCP SDK (`mcp` package)
  - Expose 3 tools: `get_order`, `list_orders`, `get_product`
  - Auth via `TIENDANUBE_ACCESS_TOKEN` header
- [ ] Write `mcp_servers/tiendanube/tools.py`:
  - Each tool is a Python function that calls the Tiendanube REST API
  - Returns normalized JSON (no raw API response shapes)
- [ ] **If Tiendanube sandbox is unavailable or rate-limited:**
  - Write `mcp_servers/tiendanube/mock_server.py`
  - Mock returns the Tiendanube equivalent of AW order 43659 and 43660
  - This is not a fallback — it is a valid demo strategy
- [ ] Test: call `get_order("TN-9981")` and see a JSON response

---

### 1.4 — MCP Server: WhatsApp Business

- [ ] Set up Twilio Sandbox for WhatsApp (fastest path — 10 minutes to working sandbox):
  - Create Twilio account
  - Navigate to Messaging → Try it out → Send a WhatsApp message
  - Sandbox number is assigned immediately
- [ ] Write `mcp_servers/whatsapp/server.py`:
  - Expose 3 tools: `send_message`, `draft_message`, `get_message_status`
  - `draft_message` is READ: LLM generates text, does not call Twilio
  - `send_message` is WRITE: calls Twilio, requires `approval_id` parameter
- [ ] Write `mcp_servers/whatsapp/tools.py`:
  - `send_message` implementation using Twilio Python SDK
  - Returns `{ message_id, status, timestamp }`
- [ ] Test: send a WhatsApp message to your own number via sandbox

---

### 1.5 — Connection Smoke Test

- [ ] Write `test_connections.py`:
  ```python
  # Checks:
  # 1. PostgreSQL: connects, counts salesorderheader rows
  # 2. Claude API: sends "hello" message, gets response
  # 3. Tiendanube MCP: calls get_order, gets back JSON
  # 4. WhatsApp MCP: calls draft_message (READ only), gets text back
  # Prints: PASS / FAIL for each
  ```
- [ ] All 4 checks pass before moving to Phase 2

---

## Phase 2: Context Store and Spine Implementation

**Goal:** Given an order ID, the agent can hydrate the full Unified Order Schema and query its history from the Context Store.

**Exit criteria:** `python demo_assist.py 43659` prints a rich order summary with context history.

---

### 2.1 — The Spine Module

- [ ] Write `agent/spine.py`:
  - `hydrate(order_id: int) -> UnifiedOrderSchema`
  - Runs a single SQL query that JOINs all relevant AW tables (salesorderheader, salesorderdetail, product, productinventory, person, emailaddress)
  - Maps raw rows to the Unified Order Schema JSON defined in MVP_SCOPE_AND_ROOT_OBJECT.md
  - Sets `context_flags` defaults
  - Fills `_meta.hydration_errors` if any join returns null
- [ ] Write `agent/spine.py`:
  - `merge_tiendanube(spine: UnifiedOrderSchema, tiendanube_data: dict) -> UnifiedOrderSchema`
  - Merges Tiendanube data into `source_id.tiendanube` and updates `status` if TN status differs from AW
- [ ] Test: `spine.hydrate(43659)` returns the correct schema

---

### 2.2 — The Context Store Module

- [ ] Write `agent/context_store.py`:
  - `insert(spine_id, entry_type, content, source)` — appends a context entry
  - `query_by_spine(spine_id)` — returns all entries for this order, newest first
  - `query_by_type(spine_id, entry_type)` — filtered by type
  - `has_entry_of_type(spine_id, entry_type, since_hours=None)` — boolean check (used by Monitor to avoid duplicate alerts)
  - `summarize(spine_id)` — calls Claude to generate a 2-sentence plain English summary of all entries (used to populate `context_history_summary` in spine)
- [ ] Seed the Context Store with demo history for orders 43659 and 43660:
  ```python
  # seeds/demo_context.py
  # 43659: "Operator approved WhatsApp dispatch notification on 2024-01-14"
  # 43660: (no entries — clean slate, to trigger Monitor alert in demo)
  ```
- [ ] Test: `context_store.query_by_spine("ORD-43659")` returns seeded entries

---

### 2.3 — The Skill Registry Module

- [ ] Write `skills/registry.py`:
  - `register(spec_yaml_path)` — inserts skill into PostgreSQL skill_registry table
  - `find(query: str) -> list[dict]` — keyword search on description + domain
  - `get(skill_name: str) -> dict` — fetch full spec
  - `invoke(skill_name: str, inputs: dict) -> SkillResult` — instantiates and calls the skill class
  - `record_invocation(skill_name, success, duration_ms)` — updates stats
- [ ] Write `skills/base_skill.py` with `BaseSkill` and `SkillResult` as defined in SKILL_SCHEMA_AND_REGISTRY.md
- [ ] Implement all 8 seed skills with `code.py`, `spec.yaml`, `metadata.json`
- [ ] Register all 8 seed skills into the database
- [ ] Test: `registry.find("order status")` returns `query_order_status`

---

### 2.4 — Assist Mode (Minimal)

- [ ] Write `agent/router.py`:
  - `classify_intent(message: str) -> dict` — calls Claude to classify mode + domain + entity
  - Returns: `{ mode: "assist"|"act"|"monitor", domain, entity_id }`
- [ ] Write `agent/core.py`:
  - `handle_assist(order_id, question) -> str`
  - Calls: spine.hydrate → context_store.summarize → registry.find → registry.invoke → Claude synthesis
- [ ] Test end-to-end with: `"What's the status of order 43659?"`

---

### 2.5 — Phase 2 Demo Checkpoint

```
python demo_assist.py

> What's the status of order 43659?

[SpineAgent] Assist mode — Sales domain — Order 43659

Order #43659 — Shipped
Customer: Christy Zhu | Total: $20,565.62 | 12 items
Shipped: 2011-06-07

Context: Operator approved WhatsApp dispatch notification on 2024-01-14.
         Customer confirmed receipt preference via WhatsApp.

Skills used: query_order_status, get_customer_info
```

---

## Phase 3: Main Loop and Approval Gate

**Goal:** Act mode works. The agent plans a multi-step chain, executes READ steps autonomously, presents the WRITE step for approval, and executes it on approval.

**Exit criteria:** The canonical Demo 2 scenario runs end-to-end: operator types goal → agent plans → executes reads → approval gate fires → operator approves → WhatsApp message sent.

---

### 3.1 — The Planner

- [ ] Write `agent/planner.py`:
  - `plan(goal: str, spine: UnifiedOrderSchema) -> Plan`
  - Calls Claude with: goal + spine JSON + skill registry summary
  - System prompt includes: permission matrix from AGENT_MODES_AND_GATES.md
  - Output: the Plan JSON structure (steps array with READ/WRITE classification)
  - Validates: each skill exists in registry; flags gaps for AutoSkill
- [ ] Test: `planner.plan("Notify Jon Yang about the delay on order 43660", spine_43660)` produces a 4-step plan with step 4 as WRITE

---

### 3.2 — The Executor

- [ ] Write `agent/executor.py`:
  - `execute_read_steps(plan: Plan) -> Plan` — runs all READ steps in sequence, stores outputs in plan
  - `get_first_write_step(plan: Plan) -> Step` — returns the first WRITE step
  - `execute_write_step(step: Step, approval_id: str) -> SkillResult` — runs it after approval
  - Each step's output is passed as context to the next step (chain pattern)

---

### 3.3 — The Approval Gate

- [ ] Write `agent/approval_gate.py`:
  - `create_approval(plan, write_step) -> ApprovalPayload` — writes to `pending_approvals` table
  - `present_approval(payload: ApprovalPayload)` — formats and displays to CLI
  - `await_decision() -> tuple[str, dict | None]` — blocks on user input: "A"pprove, "E"dit, "R"eject
  - `apply_edit(payload, human_edits) -> ApprovalPayload` — mutates payload with edits, re-presents
  - `record_decision(approval_id, decision, edits, decided_by)` — writes final state to DB
- [ ] The CLI presentation must show: action name, target (phone), full message text, plan context (why)
- [ ] Test: present an approval, type "A", confirm it's marked `approved` in DB

---

### 3.4 — Act Mode Integration

- [ ] Write `agent/core.py`:
  - `handle_act(goal: str, spine: UnifiedOrderSchema)` — orchestrates planner + executor + gate
  - Full flow: plan → execute reads → gate → on approval, execute write → log to context store
- [ ] Write `interfaces/cli.py`:
  - Simple REPL: reads input, calls `router.classify_intent`, dispatches to handle_assist or handle_act
  - Renders approval payload clearly with ASCII box
  - Accepts A/E/R input
- [ ] Test the full Demo 2 scenario end-to-end

---

### 3.5 — Phase 3 Demo Checkpoint

```
python main.py

SpineAgent > Notify Jon Yang about the delay on order 43660

[Planning...]
  Step 1: get_customer_info(43660)         [READ] ✓
  Step 2: check_inventory(PROD-711)        [READ] ✓
  Step 3: draft_whatsapp_message(context)  [READ] ✓
  Step 4: send_whatsapp_message(phone,msg) [WRITE] ⏸ PENDING APPROVAL

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
APPROVAL REQUIRED — AP-0042
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ACTION: send_whatsapp_message
TO:     Jon Yang | +54 11 9876-5432

MESSAGE:
  "Hola Jon, te escribimos sobre tu pedido #43660..."

Why: Order has been in Processing 7 days with stock issue.
     No prior communication recorded.

[ A ] Approve   [ E ] Edit   [ R ] Reject
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
> A

[Executing send_whatsapp_message...]
✓ Message sent. ID: SM-abc123 | Status: delivered
Context Store updated.
```

---

## Phase 4: The Magic Demo Script

**Goal:** Produce a rehearsed, reproducible demo where the agent encounters an unknown capability, generates a skill live, and uses it to answer a real question.

**This phase is not about building new features. It is about scripting, resetting state, and making the demo bulletproof.**

---

### 4.1 — Monitor Mode (Simulated)

- [ ] Write `monitor/scheduler.py`:
  - Uses APScheduler, interval configurable via `MONITOR_INTERVAL_SECONDS` env var
  - Default: 3600 seconds (production), 30 seconds (demo mode via `DEMO_MODE=1`)
- [ ] Write `monitor/rules.py`:
  - Implements the 4 monitor rules from AGENT_MODES_AND_GATES.md (MON-01 through MON-04)
  - Each rule returns a list of flagged orders with alert level
- [ ] Write `monitor/alerts.py`:
  - Formats alerts for CLI output
  - Checks context_store for prior alerts (no duplicate alerts)
  - For action-required alerts: calls `planner.plan()` and creates a draft approval entry
- [ ] Test: set `DEMO_MODE=1`, wait 30 seconds, confirm alert fires for order 43660

---

### 4.2 — AutoSkill Loop

- [ ] Write `agent/autoskill/detector.py`:
  - Called by planner when `registry.find(step_description)` returns empty
  - Creates gap record, initiates research
- [ ] Write `agent/autoskill/researcher.py`:
  - For MVP: reads AdventureWorks schema introspection SQL
  - Returns relevant tables, columns, and JOIN paths for the gap description
  - No external API calls
- [ ] Write `agent/autoskill/generator.py`:
  - Calls Claude with: gap description + schema research + BaseSkill template + spec.yaml template
  - Returns: `{ spec_yaml: str, code_py: str }`
  - Prompt must be deterministic — same input → same output (set temperature=0)
- [ ] Write `agent/autoskill/validator.py`:
  - Syntax check via `ast.parse()`
  - Schema check via `yaml.safe_load()` + field validation
  - Classification safety check: reject if `classification: WRITE`
  - Mock run in subprocess: `python -c "from generated_skill import *; print(skill.mock_execute(...))"` with 5s timeout
  - Returns: `{ passed: bool, checks: list, errors: list }`
- [ ] Integrate into the Planner: when gap detected, runs the full loop before presenting the plan to the user

---

### 4.3 — The Demo Reset Script

> This is as important as any feature. The demo must be fully reproducible.

- [ ] Write `demo/reset_demo.py`:
  ```python
  # Resets the system to a clean demo state:
  # 1. Truncates context_entries (keeps schema)
  # 2. Truncates pending_approvals
  # 3. Removes 'calculate_order_margin' from skill_registry and filesystem
  # 4. Re-seeds context_store with demo history for order 43659
  # 5. Leaves order 43660 with NO context history (for Monitor to detect)
  # 6. Prints: "Demo state reset. Ready to run."
  ```
- [ ] Test: run `reset_demo.py` three times consecutively — always produces same state

---

### 4.4 — The Rehearsed Demo Script

This is the sequence you run for the judges. Practice it at least 3 times before the presentation.

```
PRE-DEMO:
  $ python demo/reset_demo.py
  $ python main.py

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SCENE 1 — "The Agent Has Memory" (Assist Mode)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Type: "What's the status of order 43659?"

Expected: Rich answer with context history (Christy Zhu, shipped,
          notes about prior WhatsApp approval). NOT just a DB lookup.

TALKING POINT: "Notice it knows about the prior approval. This is the
               context store — it remembers what happened to this order."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SCENE 2 — "The Agent Acts" (Act Mode + Gate)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Type: "Notify Jon Yang about the delay on order 43660"

Expected:
  - Agent reads customer info, checks inventory, drafts message
  - Approval gate presents the message before sending
  - You press A to approve
  - Message is sent, context store updated

TALKING POINT: "The agent planned 4 steps, ran 3 on its own, then stopped.
               It will never send a message without a human approving it first.
               That's the trust contract."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SCENE 3 — "The Agent Watches" (Monitor Mode)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Type: "run monitor" (or wait for DEMO_MODE cron to fire)

Expected:
  - Monitor scans, finds order 43660 stale + stock issue
  - Generates alert with severity
  - Offers draft plan (optional: approve it and send the message from Scene 2)

TALKING POINT: "Nobody asked the agent to do this. It noticed it on its own."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SCENE 4 — "The Magic Moment" (AutoSkill Live)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Type: "How much margin does order 43659 have?"

Expected:
  [1] Agent looks for margin skill — not found
  [2] AutoSkill loop activates — visible in terminal
  [3] Research runs — finds standardcost and unitprice in schema
  [4] Skill generated — shows spec and SQL
  [5] Sandbox validation — 4/4 checks pass
  [6] Approval gate: "New skill generated — approve to register"
  [7] You press A
  [8] Skill executes against real data
  [9] Returns: "Gross margin: 40.1% ($8,234.50). Lowest margin item: Mountain Bike Socks (12.3%)"

TALKING POINT: "It just taught itself a new skill. Next time anyone asks
               about margin, it already knows. This is institutional knowledge
               that compounds — it doesn't reset between sessions."
```

---

### 4.5 — Final Checklist Before Presenting

- [ ] All 4 demo scenes run end-to-end without errors
- [ ] `reset_demo.py` produces a clean slate every time
- [ ] Docker Compose starts cleanly on a fresh `docker-compose up`
- [ ] `.env` is configured with real credentials (not committed to repo)
- [ ] You can narrate what the agent is doing at each step from memory
- [ ] You have a fallback plan if Tiendanube is down (mock server is running)
- [ ] You have a fallback plan if Twilio has issues (mock the send, show the log)
- [ ] The terminal font is large enough for judges to read from 3 meters away

---

## Parking Lot (Good Ideas, Not This Weekend)

These are explicitly deferred. Document them here so they don't get smuggled back in during the hackathon.

| Idea | Why It's Good | Why Not Now |
|------|--------------|-------------|
| pgvector semantic search | Richer context retrieval | SQLite keyword search is sufficient for demo; pgvector adds setup risk |
| Streamlit dashboard | Visual spine visualization | CLI is faster to build; visual demo not worth the time cost |
| Inbound WhatsApp replies | Full conversation loop | Two-way comms doubles the complexity of demo flow |
| Multi-object spine support | Generalizes the system | One object, one weekend |
| Skill versioning + rollback | Production-grade registry | Not needed for a hackathon demo |
| Real-time Tiendanube webhooks | Event-driven monitoring | Polling is sufficient for the demo scenario |
| OAuth for Tiendanube | Proper auth flow | API key auth is fine for the sandbox |
| Unit test suite | Correctness guarantees | Manual testing + happy path is fine for hackathon |
