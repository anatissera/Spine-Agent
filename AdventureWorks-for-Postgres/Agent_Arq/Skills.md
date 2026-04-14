---
name: skill-creator
description: Use this skill when someone asks you to create, draft, write, or design a new skill file — for any domain, customer, or capability. Activate on requests like "create a skill for X", "write a SKILL.md for Y", "add a new skill that does Z", or "build me a skill to handle...". Produces a complete, ready-to-use SKILL.md file following the platform's canonical structure.
metadata:
  tools:
    - write_file
---

# Skill: Skill Creator

## What This Skill Does

Produces a complete, correctly structured `SKILL.md` file for any capability — data access, document generation, reference knowledge, notifications, collaboration, or any combination — using the patterns established across the Novum and KMB customer packages.

The output is always a deployable file, not a template with blanks. Every section is filled with real instructions specific to the requested capability.

---

## Step 1 — Gather Requirements

Before writing anything, collect the following. If the person has already provided them, skip ahead.

| Field | Question to ask | Notes |
|---|---|---|
| **Skill name** | What should this skill be called? | kebab-case, e.g. `invoice-lookup`, `weekly-report-sender` |
| **Trigger intent** | What does the employee say or ask when they want this? | Collect 3–5 example phrases |
| **What it produces** | What is the output — a table, a document, a notification, a verbal answer? | Determines archetype |
| **Data sources** | What system(s) does it read from? | DB views, APIs, file system, wiki, tools |
| **Tools available** | What platform tools does it call? | List all tool names exactly |
| **Constraints** | What should this skill NOT do? | Routing rules, escalation, hard limits |
| **Background trigger** | Should this skill fire automatically on a schedule or event? | If yes, note interval and condition |

If any field is missing and cannot be inferred, ask before writing. Do not fill in placeholder values.

---

## Step 2 — Select the Archetype

Map the request to exactly one primary archetype. The archetype determines which sections to include and their order.

| Archetype | Signal | Primary output |
|---|---|---|
| **Query** | Reads a database, API, or structured view; returns tabular data | Result table shown in chat |
| **Generation** | Produces a document, draft, or filled template | Artifact saved to Document Studio |
| **Reference** | Navigates documentation, wiki, or conceptual knowledge; no writes | Verbal synthesis answer |
| **Notification / Utility** | Lightweight action — notify, record, flag, store | Confirmation message |
| **Collaboration** | Participates in multi-party threads; creates shared artifacts | In-thread content + artifacts |
| **Composite** | Two archetypes combined (e.g. Query → then Generation) | Both outputs in sequence |

For composite skills, follow both archetypes' section patterns in the order they execute.

---

## Step 3 — Write the Frontmatter

```yaml
---
name: {skill-name}
description: {activation sentence}
metadata:
  tools:
    - {tool_1}
    - {tool_2}
---
```

**Rules for each field:**

`name` — kebab-case, matches the folder name exactly, no version suffixes.

`description` — starts with "Use this skill when…". One or two sentences. Activation-first: tell the agent *when to fire*, not what the skill does internally. Include 3–4 example trigger phrases in natural language. Max 1024 characters.

> Good: `Use this skill when an employee asks to look up payment status for an invoice — "has Shell paid?", "show me overdue invoices", "what's the status on INV-432?". Covers all payment states: pending, partial, complete, overdue.`

> Bad: `This skill queries the payments database and returns invoice payment records.`

`metadata.tools` — list every tool the skill calls by exact name. If the skill is reference-only (reads files, no tool calls), use `metadata: {}`.

---

## Step 4 — Write the Body

### Universal opener (all archetypes)

```markdown
# Skill: {Human-Readable Name}

## What This Skill Does

{2–3 sentences. What data it touches, what it produces, who uses it, and how it fits into the broader workflow. Reference the source system by name.}

---
```

---

### Archetype sections

#### QUERY skills

```markdown
## Primary View: `{view_or_table_name}`

> {Any column notation warning, e.g. "Column names contain spaces — always use bracket notation."}

| Column | Type | Description |
|---|---|---|
| `[Column Name]` | varchar N | {what it means} |
...

---

## {Secondary View (if any): `{view_name}`}

{Same table format. Omit this section if there is only one view.}

---

## Common Queries

### {Query name — what business question it answers}
```sql
SELECT ...
FROM {view} WITH (NOLOCK)
WHERE ...
ORDER BY ...
```

{Repeat for each standard query pattern — at minimum: a "show all recent", a "filter by counterparty/entity", and a "filter by date range".}

---

## Presenting Results

{How to format the output. Which columns to show by default. What to say when a record is found vs. not found. Any units or formatting rules.}

---

## Escalation

{Who to contact if data is wrong or missing. Do not create or modify records.}
```

---

#### GENERATION skills

```markdown
## When to Activate

{Bullet list of trigger conditions. Be specific — include example employee phrases.}

---

## Workflow

### Step 1 — {Name}

{Instruction. What data to pull, from which skill, with which filters.}

### Step 2 — {Name}

{Instruction.}

...

### Step N — Save to {output destination}

{Exact sequence of tool calls. Show parameter values explicitly. State what to tell the employee in chat after saving — one-line summary only.}

---

## {Derivation Rules (if applicable)}

{Field-by-field computation rules. Use a table when there are many fields.}

| Placeholder / Field | Derived from | Rule |
|---|---|---|
| `{field}` | `{source.column}` | {transformation or lookup} |

---

## {Formatting Rules}

{Output format specification. If a specific directive syntax is required (e.g. `{{email-header:...}}`), show the exact template.}

---

## Editing an Existing {Document Type}

{Step-by-step for when the employee asks to change something in a previously saved document. Always full-replace, never append unless the document type explicitly supports append.}

---

## What This Skill Does NOT Handle

{Hard boundaries as a bullet list. Include routing hints — "for X, use Y skill instead."}
```

---

#### REFERENCE skills

```markdown
## When To Use This Skill

{List of question types and trigger phrases. Include "also activate when you need conceptual context to explain a live-data result."}

---

## Default Reading Order

Read only what is necessary.

### For {question category}

1. `{file path}`
2. `{file path}`

{Repeat per category.}

---

## How To Answer

- Lead with the answer, not the file path
- Be explicit when giving a synthesized explanation vs. a live-data fact
- If sources conflict, follow the higher-priority source and state the conflict

---

## Constraints

- Read-only — this skill does not call tools or modify state
- Do not treat placeholder pages as authoritative
- Do not use this skill instead of live skills for current-state questions
```

---

#### NOTIFICATION / UTILITY skills

```markdown
## When to Use This Skill

{Trigger conditions as a bullet list. Include the negative — when NOT to use.}

---

## Step-by-Step Instructions

### {Action name}

1. {Step with exact parameter names and acceptable values.}
2. {Step.}
...

### {Second action, if any}

1. {Step.}
...

---

## Tools

- `{tool_name}` — {one-line description of what it does and when to call it}

---

## Constraints

{Hard limits as a bullet list. Include any field restrictions, priority usage guidelines, duplicate-prevention rules.}
```

---

#### COLLABORATION skills

```markdown
## When to Activate

{Trigger conditions. Include both direct requests and implicit signals from conversation context.}

---

## Conversation Types

| Type | Trigger | Agent role |
|---|---|---|
| {type} | {trigger phrase} | {what the agent does} |

---

## Operating Sequences

### {Sequence name}

1. {Step.}
2. {Step.}

---

## Artifact Reference Guide

{For each artifact type the skill can create:}

### {Artifact type} — `{document_type value}`

**When to create:** {condition}

**Tool call:**
```json
{
  "tool": "{tool_name}",
  "parameters": { ... }
}
```

**Content format:** {what goes in the content field}

---

## Participant Awareness

{Role-specific guidance. What each participant type needs, how to address them, what they care about.}

---

## Routing Rules

{When to hand off to another skill. Format: "If the employee asks X, route to Y-skill."}

---

## What This Skill Does NOT Handle

{Hard limits as a bullet list.}
```

---

## Step 5 — Apply Quality Gates

Before finalizing the SKILL.md, verify each item:

**Frontmatter**
- [ ] `name` is kebab-case and matches the folder name
- [ ] `description` starts with "Use this skill when…"
- [ ] `description` includes at least 3 example trigger phrases
- [ ] `description` is under 1024 characters
- [ ] All tool names in `metadata.tools` are exact (no guessing)
- [ ] Reference-only skills use `metadata: {}`

**Body**
- [ ] No placeholder text remains (`TBD`, `[INSERT]`, `{{TODO}}`, etc.)
- [ ] Every tool listed in frontmatter is explained in a Tools section or referenced in the workflow
- [ ] Constraints section explicitly states what the skill does NOT handle
- [ ] If it writes to a document workspace, the save sequence is shown step-by-step
- [ ] If it queries a database, at least 3 common SQL templates are included
- [ ] If it generates a document, the full output format is specified (not "write something appropriate")
- [ ] Escalation contacts or routing rules are present wherever data errors are possible
- [ ] Background check trigger language is absent unless a `background_check` block was requested

**Composite skills**
- [ ] Sections follow the execution order (e.g. query sections come before generation sections)
- [ ] The handoff point between phases is explicit ("Once Step 3 is complete, move to the Generation phase below")

---

## Step 6 — Output

Write the complete SKILL.md. Do not summarize it — output the full file content.

If `write_file` is available and the destination path is known, save it directly. Otherwise output the content in a fenced code block so the person can copy it.

Confirm with one line: what the skill does, what archetype it is, which tools it uses, and where it was saved (or that it is ready to copy).

---

## Constraints

- Never produce a SKILL.md with placeholder text — every field must be real
- Never invent tool names; use only tools explicitly provided or already known to the platform
- Do not add a `background_check` block unless the request explicitly mentions monitoring, scheduling, or automatic triggering
- If required information is missing and cannot be inferred, ask before writing — a wrong skill is worse than a delayed one
- The `description` field is the activation signal; precision here directly determines whether the agent fires at the right time
- Skill bodies must be instructional, not descriptive — write what the agent *should do*, not what the skill *is about*
