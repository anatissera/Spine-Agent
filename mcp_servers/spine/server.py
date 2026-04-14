"""
MCP Server: SpineAgent Database Bridge

Exposes AdventureWorks + spine_agent schema to Claude Code via MCP.
All tools here are READ-classified — they never mutate business data.
Context store writes (write_context_entry, create_approval) are internal
memory operations and are also safe to run autonomously.

Run:  python mcp_servers/spine/server.py
Env:  DATABASE_URL
"""

import json
import os
from datetime import datetime, timezone

import psycopg
from psycopg.rows import dict_row
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("spineagent")


# ── Helpers ──────────────────────────────────────────────────────────────────

def _conn():
    """Open a new psycopg v3 connection with dict rows."""
    return psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row)


STATUS_MAP = {
    1: "placed",
    2: "processing",
    3: "cancelled",
    4: "rejected",
    5: "shipped",
    6: "delivered",
}

STALE_HOURS = {
    "placed": 4,
    "processing": 48,
    "shipped": 72,
}


# ── Tools ─────────────────────────────────────────────────────────────────────

@mcp.tool()
def hydrate_order(order_id: int) -> dict:
    """
    Fetch the complete unified Order object from AdventureWorks for a given
    order ID. Returns status, customer contact info, financials, line items
    with stock levels, and stale-state flags. Use this as the first step
    whenever you need to reason about a specific order.
    """
    with _conn() as conn:
        # Header + customer
        header = conn.execute("""
            SELECT
                soh.salesorderid,
                soh.status,
                soh.orderdate,
                soh.shipdate,
                soh.totaldue,
                soh.comment,
                CONCAT(p.firstname, ' ', p.lastname)  AS customer_name,
                ea.emailaddress                        AS customer_email,
                pp.phonenumber                         AS customer_phone,
                EXTRACT(EPOCH FROM (NOW() - soh.modifieddate)) / 3600
                                                       AS hours_since_update
            FROM sales.salesorderheader soh
            JOIN sales.customer c
                ON soh.customerid = c.customerid
            JOIN person.person p
                ON c.personid = p.businessentityid
            LEFT JOIN person.emailaddress ea
                ON p.businessentityid = ea.businessentityid
            LEFT JOIN person.personphone pp
                ON p.businessentityid = pp.businessentityid
            WHERE soh.salesorderid = %s
            LIMIT 1
        """, (order_id,)).fetchone()

        if not header:
            return {"error": f"Order {order_id} not found"}

        # Line items + stock
        items = conn.execute("""
            SELECT
                sod.salesorderdetailid,
                p.productid,
                p.name              AS product_name,
                p.productnumber     AS sku,
                sod.orderqty        AS quantity,
                sod.unitprice,
                p.standardcost,
                ROUND(
                    ((sod.unitprice - p.standardcost) / NULLIF(sod.unitprice, 0) * 100)::numeric,
                    1
                )                   AS margin_pct,
                COALESCE(SUM(pi.quantity), 0) AS stock_available
            FROM sales.salesorderdetail sod
            JOIN production.product p
                ON sod.productid = p.productid
            LEFT JOIN production.productinventory pi
                ON p.productid = pi.productid
            WHERE sod.salesorderid = %s
            GROUP BY sod.salesorderdetailid, p.productid, p.name,
                     p.productnumber, sod.orderqty, sod.unitprice, p.standardcost
            ORDER BY sod.salesorderdetailid
        """, (order_id,)).fetchall()

    status_name = STATUS_MAP.get(header["status"], "unknown")
    hours = float(header["hours_since_update"] or 0)
    stale_threshold = STALE_HOURS.get(status_name, 48)

    line_items = []
    has_stock_issue = False
    for row in items:
        stock = int(row["stock_available"])
        if stock == 0:
            has_stock_issue = True
        line_items.append({
            "product_id": row["productid"],
            "product_name": row["product_name"],
            "sku": row["sku"],
            "quantity": int(row["quantity"]),
            "unit_price": float(row["unitprice"]),
            "standard_cost": float(row["standardcost"]),
            "margin_pct": float(row["margin_pct"] or 0),
            "stock_available": stock,
            "stock_status": "ok" if stock > 5 else ("low" if stock > 0 else "out"),
        })

    return {
        "spine_id": f"SalesOrder:{order_id}",
        "source_id": {"adventureworks": order_id},
        "snapshot_at": datetime.now(timezone.utc).isoformat(),
        "status": {
            "current": status_name,
            "hours_since_update": round(hours, 1),
            "is_stale": hours > stale_threshold,
            "stale_threshold_hours": stale_threshold,
        },
        "customer": {
            "full_name": header["customer_name"],
            "email": header["customer_email"],
            "phone": header["customer_phone"],
        },
        "financials": {
            "total": float(header["totaldue"]),
            "currency": "USD",
        },
        "line_items": line_items,
        "context_flags": {
            "has_stock_issue": has_stock_issue,
            "has_pending_approval": False,
        },
        "comment": header["comment"],
    }


@mcp.tool()
def list_stale_orders(limit: int = 20) -> list:
    """
    Return all active orders that have exceeded their stale-state threshold
    without a status change. Use this in Monitor mode to detect orders that
    need attention. Returns order ID, customer name, status, total, and how
    many hours the order has been idle.
    """
    with _conn() as conn:
        rows = conn.execute("""
            SELECT
                soh.salesorderid,
                soh.status,
                CONCAT(p.firstname, ' ', p.lastname) AS customer_name,
                soh.totaldue                          AS total,
                EXTRACT(EPOCH FROM (NOW() - soh.modifieddate)) / 3600
                                                      AS hours_idle
            FROM sales.salesorderheader soh
            JOIN sales.customer c  ON soh.customerid = c.customerid
            JOIN person.person p   ON c.personid = p.businessentityid
            WHERE soh.status IN (1, 2)   -- placed or processing
              AND (
                  (soh.status = 1 AND soh.modifieddate < NOW() - INTERVAL '4 hours')
               OR (soh.status = 2 AND soh.modifieddate < NOW() - INTERVAL '48 hours')
              )
            ORDER BY hours_idle DESC
            LIMIT %s
        """, (limit,)).fetchall()

    return [
        {
            "order_id": r["salesorderid"],
            "spine_id": f"SalesOrder:{r['salesorderid']}",
            "status": STATUS_MAP.get(r["status"], "unknown"),
            "customer_name": r["customer_name"],
            "total": float(r["total"]),
            "hours_idle": round(float(r["hours_idle"]), 1),
            "alert_level": "CRITICAL" if r["status"] == 1 else "HIGH",
        }
        for r in rows
    ]


@mcp.tool()
def get_order_context(spine_id: str) -> list:
    """
    Retrieve the full context history for an order — past agent decisions,
    alerts, and action results stored in the context store. Use this to
    understand what has already been done before proposing a new action.
    Returns entries newest-first.
    """
    with _conn() as conn:
        rows = conn.execute("""
            SELECT entry_type, content, source, created_at
            FROM spine_agent.context_entries
            WHERE spine_object_id = %s
            ORDER BY created_at DESC
            LIMIT 50
        """, (spine_id,)).fetchall()

    return [
        {
            "entry_type": r["entry_type"],
            "content": r["content"],
            "source": r["source"],
            "created_at": r["created_at"].isoformat(),
        }
        for r in rows
    ]


@mcp.tool()
def write_context_entry(
    spine_id: str,
    entry_type: str,
    content: dict,
    source: str = "agent",
) -> dict:
    """
    Append an entry to the order's context history. Call this after every
    significant action or decision so future reasoning has a full audit trail.
    entry_type must be one of: decision, pattern, rule, action_result, state_snapshot.
    source must be one of: human, agent, system.
    """
    valid_types = {"decision", "pattern", "rule", "action_result", "state_snapshot"}
    valid_sources = {"human", "agent", "system"}

    if entry_type not in valid_types:
        return {"error": f"Invalid entry_type. Must be one of: {valid_types}"}
    if source not in valid_sources:
        return {"error": f"Invalid source. Must be one of: {valid_sources}"}

    with _conn() as conn:
        row = conn.execute("""
            INSERT INTO spine_agent.context_entries
                (spine_object_id, entry_type, content, source)
            VALUES (%s, %s, %s, %s)
            RETURNING id, created_at
        """, (spine_id, entry_type, json.dumps(content), source)).fetchone()
        conn.commit()

    return {"id": row["id"], "created_at": row["created_at"].isoformat(), "status": "written"}


@mcp.tool()
def create_pending_approval(
    spine_id: str,
    action_type: str,
    action_payload: dict,
    context_why: str,
) -> dict:
    """
    Create a pending approval entry before any WRITE action (sending messages,
    updating order status, etc.). Returns the approval ID that must be passed
    to the downstream WRITE tool. The human operator must approve this entry
    before execution proceeds.
    """
    with _conn() as conn:
        row = conn.execute("""
            INSERT INTO spine_agent.pending_approvals
                (spine_object_id, action_type, action_payload, context, expires_at)
            VALUES (%s, %s, %s, %s, NOW() + INTERVAL '2 hours')
            RETURNING id, created_at, expires_at
        """, (
            spine_id,
            action_type,
            json.dumps(action_payload),
            json.dumps({"why": context_why}),
        )).fetchone()
        conn.commit()

    return {
        "approval_id": row["id"],
        "status": "pending",
        "created_at": row["created_at"].isoformat(),
        "expires_at": row["expires_at"].isoformat(),
        "instruction": (
            f"Approval #{row['id']} created. Present this to the operator "
            "and wait for explicit APPROVE before calling the WRITE tool."
        ),
    }


@mcp.tool()
def get_pending_approval(approval_id: int) -> dict:
    """
    Fetch the current status of a pending approval by ID.
    Use this to check whether the human has approved, rejected, or edited
    the proposed action before executing it.
    """
    with _conn() as conn:
        row = conn.execute("""
            SELECT id, spine_object_id, action_type, action_payload,
                   context, status, approved_by, decision_note, decided_at
            FROM spine_agent.pending_approvals
            WHERE id = %s
        """, (approval_id,)).fetchone()

    if not row:
        return {"error": f"Approval {approval_id} not found"}

    return dict(row)


if __name__ == "__main__":
    mcp.run()
