"""Human-in-the-Loop Approval Gate.

Core rule: internal operations (query, draft, test, store) = autonomous.
Production-affecting actions (send message to customer, mutate live system) = requires approval.

Manages the spine_agent.pending_approvals table: create requests, check status,
approve/reject, handle expiration.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from agent.db import get_connection

DEFAULT_EXPIRY_HOURS = 2


# ── Classification ───────────────────────────────────────────────────────────

# Internal skills — run autonomously (no production side-effects)
READ_SKILLS = {
    "query_order_status",
    "get_customer_info",
    "list_order_items",
    "check_inventory",
    "detect_stale_orders",
    "generate_order_summary",
    "analyze_company_config",
}

# Production-affecting skills — require human approval before execution
WRITE_SKILLS = {
    "send_whatsapp_notification",
    "send_telegram_message",
    "update_order_status",
}


def requires_approval(skill_name: str) -> bool:
    """Check if a skill affects production and requires human approval.

    Default: unknown skills require approval (safe default — assume
    production impact until proven otherwise).
    """
    if skill_name in READ_SKILLS:
        return False
    return True


# ── CRUD ─────────────────────────────────────────────────────────────────────


async def create_approval(
    spine_object_id: str,
    action_type: str,
    action_payload: dict,
    context: dict | None = None,
    expiry_hours: int = DEFAULT_EXPIRY_HOURS,
) -> int:
    """Create a pending approval request. Returns the approval ID."""
    expires_at = datetime.now(timezone.utc) + timedelta(hours=expiry_hours)

    async with await get_connection() as conn:
        row = await (
            await conn.execute(
                """
                INSERT INTO spine_agent.pending_approvals
                    (spine_object_id, action_type, action_payload, context,
                     status, requested_by, expires_at)
                VALUES (%(sid)s, %(atype)s, %(payload)s, %(ctx)s,
                        'pending', 'agent', %(expires)s)
                RETURNING id
                """,
                {
                    "sid": spine_object_id,
                    "atype": action_type,
                    "payload": json.dumps(action_payload),
                    "ctx": json.dumps(context) if context else None,
                    "expires": expires_at,
                },
            )
        ).fetchone()
    return row["id"]


async def get_approval(approval_id: int) -> dict | None:
    """Fetch an approval by ID."""
    async with await get_connection() as conn:
        row = await (
            await conn.execute(
                "SELECT * FROM spine_agent.pending_approvals WHERE id = %(id)s",
                {"id": approval_id},
            )
        ).fetchone()
    return dict(row) if row else None


async def approve(approval_id: int, approved_by: str = "human", note: str | None = None) -> bool:
    """Approve a pending request. Returns True if status was updated."""
    async with await get_connection() as conn:
        result = await conn.execute(
            """
            UPDATE spine_agent.pending_approvals
            SET status = 'approved', approved_by = %(by)s,
                decision_note = %(note)s, decided_at = NOW()
            WHERE id = %(id)s AND status = 'pending'
            """,
            {"id": approval_id, "by": approved_by, "note": note},
        )
    return result.rowcount > 0


async def reject(approval_id: int, approved_by: str = "human", note: str | None = None) -> bool:
    """Reject a pending request. Returns True if status was updated."""
    async with await get_connection() as conn:
        result = await conn.execute(
            """
            UPDATE spine_agent.pending_approvals
            SET status = 'rejected', approved_by = %(by)s,
                decision_note = %(note)s, decided_at = NOW()
            WHERE id = %(id)s AND status = 'pending'
            """,
            {"id": approval_id, "by": approved_by, "note": note},
        )
    return result.rowcount > 0


async def list_pending(spine_object_id: str | None = None) -> list[dict]:
    """List all pending approvals, optionally filtered by spine object."""
    where_parts = ["status = 'pending'"]
    params: dict = {}

    if spine_object_id:
        where_parts.append("spine_object_id = %(sid)s")
        params["sid"] = spine_object_id

    where = " AND ".join(where_parts)

    async with await get_connection() as conn:
        rows = await (
            await conn.execute(
                f"""
                SELECT id, spine_object_id, action_type, action_payload,
                       context, expires_at, created_at
                FROM spine_agent.pending_approvals
                WHERE {where}
                ORDER BY created_at DESC
                """,
                params,
            )
        ).fetchall()
    return rows


async def expire_stale_approvals() -> int:
    """Expire approvals past their deadline. Returns count expired."""
    async with await get_connection() as conn:
        result = await conn.execute(
            """
            UPDATE spine_agent.pending_approvals
            SET status = 'expired', decided_at = NOW()
            WHERE status = 'pending' AND expires_at < NOW()
            """
        )
    return result.rowcount
