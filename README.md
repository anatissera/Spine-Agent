# SpineAgent

An autonomous agent that operates on the root operational object of a business — the entity that crosses multiple functional areas and drives work through the organization.

Built for the Anthropic hackathon. Uses AdventureWorks (OLTP) as demo data, with `SalesOrder` as the spine object.

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- An Anthropic API key

### 1. Environment

```bash
cp .env.example .env
# Edit .env and set your ANTHROPIC_API_KEY
```

### 2. Start the database

```bash
docker compose up --build -d
```

This builds a PostgreSQL 16 + pgvector image that:
- Clones and loads AdventureWorks OLTP data
- Creates the `spine_agent` schema (context_store, skill_registry, pending_approvals, action_log)

First build takes a few minutes (downloads CSVs + converts them).

### 3. Install Python dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

### 4. Verify everything works

```bash
python scripts/verify_setup.py
```

This checks:
- PostgreSQL connectivity
- AdventureWorks data is loaded
- pgvector extension is installed
- spine_agent tables exist
- Claude API responds (if key is set)

## Project Structure

```
spine-agent/
├── docker-compose.yml           # PostgreSQL + pgvector
├── docker/postgres/             # Custom Dockerfile + init scripts
├── agent/                       # Core agent modules
│   ├── config.py                # Settings (from .env)
│   ├── core.py                  # Orchestrator
│   ├── spine.py                 # Operational Spine
│   ├── context_store.py         # Persistent business memory
│   ├── planner.py               # Action planner
│   ├── executor.py              # Skill executor
│   ├── router.py                # Intent router
│   ├── approval_gate.py         # Human-in-the-loop gate
│   └── autoskill/               # AutoSkill loop
├── skills/                      # Skill registry + built-in skills
├── mcp_servers/                 # MCP server implementations
│   ├── tiendanube/
│   └── whatsapp/
├── db/                          # Schema + migrations
├── monitor/                     # Background monitor mode
├── interfaces/                  # CLI, API, dashboard
├── scripts/                     # Utility scripts
└── tests/
```

## Architecture

See [operational_spine_agent_project_plan.md](operational_spine_agent_project_plan.md) for the full architecture document.
