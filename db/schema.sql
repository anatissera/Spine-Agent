-- SpineAgent additional schemas
-- Runs after AdventureWorks is loaded (02-spine-schema.sql)

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- Schema: spine_agent
-- ============================================================
CREATE SCHEMA IF NOT EXISTS spine_agent;

-- ------------------------------------------------------------
-- Context Store: persistent business memory
-- ------------------------------------------------------------
CREATE TABLE spine_agent.context_entries (
    id              BIGSERIAL PRIMARY KEY,
    spine_object_id TEXT        NOT NULL,          -- e.g. "SalesOrder:43659"
    entry_type      TEXT        NOT NULL           -- decision | pattern | rule | action_result | state_snapshot
        CHECK (entry_type IN (
            'decision', 'pattern', 'rule',
            'action_result', 'state_snapshot'
        )),
    content         JSONB       NOT NULL,          -- structured payload
    embedding       vector(1536),                  -- for semantic search (OpenAI-compatible dim)
    source          TEXT        NOT NULL DEFAULT 'system'
        CHECK (source IN ('human', 'agent', 'system')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_context_spine_object ON spine_agent.context_entries (spine_object_id);
CREATE INDEX idx_context_entry_type   ON spine_agent.context_entries (entry_type);
CREATE INDEX idx_context_created_at   ON spine_agent.context_entries (created_at DESC);

-- HNSW index for fast approximate nearest-neighbor search on embeddings
CREATE INDEX idx_context_embedding ON spine_agent.context_entries
    USING hnsw (embedding vector_cosine_ops);

-- ------------------------------------------------------------
-- Skill Registry: catalog of agent capabilities
-- ------------------------------------------------------------
CREATE TABLE spine_agent.skills (
    id              BIGSERIAL PRIMARY KEY,
    name            TEXT        NOT NULL UNIQUE,
    description     TEXT        NOT NULL,
    domain          TEXT        NOT NULL,           -- sales | production | purchasing | person | cross-domain
    trigger_type    TEXT        NOT NULL DEFAULT 'on_demand'
        CHECK (trigger_type IN ('persistent', 'on_demand', 'auto_generated')),
    spec            JSONB       NOT NULL,           -- inputs, outputs, dependencies
    code_path       TEXT,                           -- relative path to code.py
    version         INT         NOT NULL DEFAULT 1,
    author          TEXT        NOT NULL DEFAULT 'human'
        CHECK (author IN ('human', 'agent')),
    enabled         BOOLEAN     NOT NULL DEFAULT true,
    usage_count     INT         NOT NULL DEFAULT 0,
    last_used_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_skills_domain       ON spine_agent.skills (domain);
CREATE INDEX idx_skills_trigger_type ON spine_agent.skills (trigger_type);
CREATE INDEX idx_skills_enabled      ON spine_agent.skills (enabled) WHERE enabled = true;

-- Description embedding for semantic skill search
ALTER TABLE spine_agent.skills ADD COLUMN description_embedding vector(1536);
CREATE INDEX idx_skills_desc_embedding ON spine_agent.skills
    USING hnsw (description_embedding vector_cosine_ops);

-- ------------------------------------------------------------
-- Pending Approvals: human-in-the-loop gate
-- ------------------------------------------------------------
CREATE TABLE spine_agent.pending_approvals (
    id                BIGSERIAL PRIMARY KEY,
    spine_object_id   TEXT        NOT NULL,
    action_type       TEXT        NOT NULL,         -- e.g. "send_whatsapp", "update_order_status"
    action_payload    JSONB       NOT NULL,         -- full details of proposed action
    context           JSONB,                        -- supporting context for the approver
    status            TEXT        NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'approved', 'rejected', 'expired', 'edited')),
    requested_by      TEXT        NOT NULL DEFAULT 'agent',
    approved_by       TEXT,
    decision_note     TEXT,                         -- optional note from approver
    expires_at        TIMESTAMPTZ,
    decided_at        TIMESTAMPTZ,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_approvals_status     ON spine_agent.pending_approvals (status);
CREATE INDEX idx_approvals_spine_obj  ON spine_agent.pending_approvals (spine_object_id);
CREATE INDEX idx_approvals_created_at ON spine_agent.pending_approvals (created_at DESC);

-- ------------------------------------------------------------
-- Agent action log: audit trail of everything the agent does
-- ------------------------------------------------------------
CREATE TABLE spine_agent.action_log (
    id              BIGSERIAL PRIMARY KEY,
    spine_object_id TEXT,
    action          TEXT        NOT NULL,
    skill_name      TEXT,
    input_payload   JSONB,
    output_payload  JSONB,
    status          TEXT        NOT NULL DEFAULT 'success'
        CHECK (status IN ('success', 'failure', 'pending_approval')),
    approval_id     BIGINT      REFERENCES spine_agent.pending_approvals(id),
    duration_ms     INT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_action_log_spine_obj ON spine_agent.action_log (spine_object_id);
CREATE INDEX idx_action_log_created   ON spine_agent.action_log (created_at DESC);
