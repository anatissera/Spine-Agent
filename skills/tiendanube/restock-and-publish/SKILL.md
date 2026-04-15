---
name: restock-and-publish
description: >
  Use this skill when the user wants to publish a new product on Tiendanube
  that requires stock from a provider — "I want to publish a new bike",
  "add a new product and contact the supplier", "request stock from BikeProvider
  and list it on the store", or any request that combines a Tiendanube product
  publication with a supplier stock confirmation via Telegram.
metadata:
  tools:
    - create_restock_request
    - get_restock_request
    - update_restock_state
    - cancel_restock_request
    - confirm_restock_request
    - create_pending_approval
    - send_provider_request
    - poll_provider_response
    - create_product
---

# Skill: Restock & Publish

## What This Skill Does

Orchestrates a two-gate workflow:

1. **Gate 1 — Operator approves contacting the provider** (before any external message is sent)
2. **Gate 2 — Operator approves Tiendanube publication** (after provider confirms stock)

Between the two gates, the agent contacts a Telegram provider, interprets their
free-form response (Spanish or English), and handles follow-up escalation if no
reply arrives.

---

## Prerequisites

- `TELEGRAM_BOT_TOKEN` must be set in `.env`
- `TELEGRAM_OPERATOR_CHAT_ID` must be set in `.env`
- `TIENDANUBE_MOCK=false` to publish to the real store (or keep `true` for demo)
- Provider contacts are defined in `config/providers.yaml`

---

## Phase A — Launch the Restock Request

### Step 1 — Collect product details from the user

Ask for (one question at a time, conversationally):

| Field | Required | Example |
|---|---|---|
| Product name | Yes | "Mountain Bike Trail 29" |
| Description | Yes | "MTB de aluminio, frenos hidráulicos, 21 velocidades" |
| Price (ARS or USD) | Yes | 280000 |
| Quantity needed from provider | Yes | 5 |
| SKU | No | "MTB-TRAIL-29" |

If the user hasn't specified a provider, suggest `bike_provider` (BikeProvider) for
bike/cycling products. Confirm with the user before proceeding.

### Step 2 — Create the restock request (Gate 1)

```
create_restock_request(
    product_name     = <name>,
    product_description = <description>,
    price            = <price>,
    quantity         = <quantity>,
    provider_id      = "bike_provider",
    sku              = <sku or "">
)
```

This returns a `request_id` and `approval_id` (same value). Show the operator:

> **Pending Approval #[request_id]**
> Action: Contact BikeProvider via Telegram to request [quantity] units of "[name]"
> Price target: $[price]
> **Do you approve? Reply APPROVE to proceed.**

**WAIT for explicit operator confirmation before Step 3.**

### Step 3 — Send Telegram message to provider

```
send_provider_request(
    provider_id  = "bike_provider",
    product_name = <name>,
    quantity     = <quantity>,
    unit_price   = <price>,
    description  = <description>,
    request_id   = <request_id>,
    approval_id  = <request_id>,   # same value
)
```

Record the returned `message_id` via:

```
update_restock_state(
    request_id              = <request_id>,
    last_telegram_update_id = 0,
    new_retry_count         = 0,
    telegram_message_id     = <message_id from above>,
)
```

Tell the user:
> "Message sent to BikeProvider (request #[request_id]). Waiting for their reply.
> I'll follow up automatically. You can check status anytime with:
> 'check restock request [request_id]'"

---

## Phase B — Check / Escalate (call on-demand or via Monitor mode)

Trigger: user says "check restock [id]", "any response from provider?", or Monitor mode fires.

### Step 1 — Fetch current state

```
get_restock_request(request_id = <id>)
```

If `status` is already `approved` or `expired`, skip to Phase C or report cancellation.

### Step 2 — Poll Telegram for a response

```
poll_provider_response(
    provider_id     = "bike_provider",
    last_update_id  = <last_update_id from get_restock_request>,
)
```

Always store the `new_update_id` afterward:

```
update_restock_state(
    request_id              = <id>,
    last_telegram_update_id = <new_update_id>,
    new_retry_count         = <current retry_count>,   # unchanged if no message sent
)
```

### Step 3 — Interpret the result

| `response_type` | Action |
|---|---|
| `confirmed` | Go to **Phase C — Confirm and Publish** |
| `rejected` | Call `cancel_restock_request(id, "Provider rejected the request")`. Inform the user. |
| `unclear` | Show the raw text to the user and ask them to decide: confirm, reject, or ignore. |
| `none` | Check escalation (Step 4). |

### Step 4 — Escalation check (only when `response_type = 'none'`)

Check `is_followup_due` from `get_restock_request`:

**If `is_followup_due = false`:** No action needed yet.
> "No reply yet. Next follow-up scheduled for [next_followup_at]."

**If `is_followup_due = true` and `retry_count < 3`:** Send a follow-up message.

```
send_provider_request(
    provider_id  = "bike_provider",
    product_name = <name from payload>,
    quantity     = <quantity from payload>,
    unit_price   = <price from payload>,
    description  = <description from payload>,
    request_id   = <request_id>,
    approval_id  = <request_id>,
)
```

Then update state with incremented retry_count:

```
update_restock_state(
    request_id              = <id>,
    last_telegram_update_id = <current last_update_id>,
    new_retry_count         = <retry_count + 1>,
    telegram_message_id     = <new message_id>,
)
```

Inform the user:
> "No response after [minutes] minutes. Follow-up #[retry_count+1] sent to BikeProvider.
> Next check in [next interval] minutes."

**Escalation schedule:**

| retry_count after update | Wait before next check |
|---|---|
| 0 (initial send) | 30 minutes |
| 1 (1st follow-up) | 60 minutes |
| 2 (2nd follow-up) | 120 minutes |
| 3 (3rd follow-up) | 240 minutes → then cancel |

**If `is_followup_due = true` and `retry_count >= 3` (or `max_retries_reached = true`):**

```
cancel_restock_request(
    request_id = <id>,
    reason     = "No response from provider after maximum wait time (4 hours total).",
)
```

> "BikeProvider did not respond after 4+ hours of follow-ups.
> Restock request #[id] has been cancelled. No product was published."

---

## Phase C — Confirm and Publish

### Step 1 — Confirm the restock request

```
confirm_restock_request(
    request_id        = <id>,
    provider_response = <raw_text from poll_provider_response>,
)
```

This returns `product_to_publish` with the product details.

### Step 2 — Gate 2: operator approves Tiendanube publication

```
create_pending_approval(
    spine_id       = "Product:restock:<request_id>",
    action_type    = "tiendanube_create_product",
    action_payload = <product_to_publish dict>,
    context_why    = "BikeProvider confirmed stock. Ready to publish on Tiendanube.",
)
```

Show the operator:

> **Pending Approval #[new_approval_id]**
> Action: Publish "[product_name]" on Tiendanube — [quantity] units at $[price]
> BikeProvider confirmed: "[raw_text]"
> **Do you approve publication? Reply APPROVE to proceed.**

**WAIT for explicit operator confirmation before Step 3.**

### Step 3 — Publish on Tiendanube

```
create_product(
    name        = <product_name>,
    description = <product_description>,
    price       = <price>,
    stock       = <quantity_requested>,
    sku         = <sku or "">,
    approval_id = <new_approval_id>,
)
```

### Step 4 — Write audit trail

```
write_context_entry(
    spine_id   = "Product:restock:<request_id>",
    entry_type = "action_result",
    content    = {
        "action": "tiendanube_product_published",
        "product_id": <id from create_product>,
        "permalink": <permalink>,
        "provider": "BikeProvider",
        "restock_request_id": <request_id>,
    },
    source = "agent",
)
```

Tell the user:
> "✅ Product published on Tiendanube!
> **[product_name]** — ID: [id]
> Stock: [quantity] units | Price: $[price]
> Link: [permalink]"

---

## Error Handling

| Situation | Action |
|---|---|
| Provider not found in providers.yaml | Inform user, list available provider IDs |
| `TELEGRAM_BOT_TOKEN` not set | Explain setup: message @BotFather, add token to `.env` |
| Tiendanube API error (400/422) | Show validation error, ask user to correct product details |
| Operator rejects Gate 1 or Gate 2 | Cancel cleanly, no external actions taken |
| `response_type = 'unclear'` | Show raw text, ask user how to proceed |

---

## Constraints

- **Never skip Gate 1** — always create a pending approval before sending Telegram messages
- **Never skip Gate 2** — always create a pending approval before publishing on Tiendanube
- **Never publish without provider confirmation** — do not call `create_product` if `confirm_restock_request` hasn't succeeded
- **Never send more than 4 Telegram messages total** (1 initial + 3 follow-ups)
