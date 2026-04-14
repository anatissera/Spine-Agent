"""Monitor rules — detect anomalies and stale orders in the spine.

Each rule function queries AdventureWorks and returns a list of alerts (dicts).
Rules are designed to run periodically via the scheduler.
"""

from __future__ import annotations

from agent.db import get_connection

# Stale thresholds in hours — aligned with M3-MCP spine server thresholds
STALE_THRESHOLDS = {
    1: 4,    # "In Process" stale after 4 hours
    2: 48,   # "Approved" stale after 48 hours
    5: 72,   # "Shipped" stale after 72 hours (no delivery confirmation)
}


async def detect_stale_orders(limit: int = 20) -> list[dict]:
    """Find orders that have been in their current status longer than expected.

    Uses AdventureWorks status codes:
      1=In Process, 2=Approved, 3=Backordered, 4=Rejected, 5=Shipped, 6=Cancelled

    Returns list of alert dicts with order details and staleness info.
    """
    async with await get_connection() as conn:
        rows = await (
            await conn.execute(
                """
                SELECT
                    soh.salesorderid,
                    soh.status,
                    soh.orderdate,
                    soh.duedate,
                    soh.shipdate,
                    soh.totaldue,
                    soh.modifieddate,
                    EXTRACT(EPOCH FROM (NOW() - soh.modifieddate)) / 3600 AS hours_stale,
                    c.customerid,
                    p.firstname,
                    p.lastname
                FROM sales.salesorderheader soh
                JOIN sales.customer c ON c.customerid = soh.customerid
                LEFT JOIN person.person p ON p.businessentityid = c.personid
                WHERE soh.status IN (1, 2, 5)
                ORDER BY hours_stale DESC
                LIMIT %(limit)s
                """,
                {"limit": limit},
            )
        ).fetchall()

    alerts = []
    for row in rows:
        status = row["status"]
        hours = float(row["hours_stale"])
        threshold = STALE_THRESHOLDS.get(status)

        if threshold is None or hours < threshold:
            continue

        status_label = {1: "In Process", 2: "Approved", 5: "Shipped"}.get(status, f"Status {status}")
        alerts.append({
            "type": "stale_order",
            "level": "HIGH" if hours > threshold * 3 else "WARNING",
            "order_id": row["salesorderid"],
            "status": status,
            "status_label": status_label,
            "hours_stale": round(hours, 1),
            "threshold_hours": threshold,
            "total_due": str(row["totaldue"]),
            "customer_name": f"{row['firstname'] or ''} {row['lastname'] or ''}".strip() or "N/A",
            "customer_id": row["customerid"],
            "order_date": row["orderdate"].isoformat() if row["orderdate"] else None,
            "due_date": row["duedate"].isoformat() if row["duedate"] else None,
            "message": (
                f"Order #{row['salesorderid']} has been in '{status_label}' "
                f"for {round(hours, 1)}h (threshold: {threshold}h). "
                f"Customer: {row['firstname'] or ''} {row['lastname'] or ''}. "
                f"Total: ${row['totaldue']}."
            ),
        })

    return alerts


async def detect_overdue_orders(limit: int = 20) -> list[dict]:
    """Find orders past their due date that haven't shipped."""
    async with await get_connection() as conn:
        rows = await (
            await conn.execute(
                """
                SELECT
                    soh.salesorderid,
                    soh.status,
                    soh.orderdate,
                    soh.duedate,
                    soh.totaldue,
                    EXTRACT(DAY FROM (NOW() - soh.duedate)) AS days_overdue,
                    p.firstname,
                    p.lastname
                FROM sales.salesorderheader soh
                JOIN sales.customer c ON c.customerid = soh.customerid
                LEFT JOIN person.person p ON p.businessentityid = c.personid
                WHERE soh.status IN (1, 2, 3)
                  AND soh.duedate < NOW()
                ORDER BY days_overdue DESC
                LIMIT %(limit)s
                """,
                {"limit": limit},
            )
        ).fetchall()

    return [
        {
            "type": "overdue_order",
            "level": "HIGH",
            "order_id": row["salesorderid"],
            "days_overdue": int(row["days_overdue"]),
            "total_due": str(row["totaldue"]),
            "customer_name": f"{row['firstname'] or ''} {row['lastname'] or ''}".strip() or "N/A",
            "message": (
                f"Order #{row['salesorderid']} is {int(row['days_overdue'])} days past due. "
                f"Customer: {row['firstname'] or ''} {row['lastname'] or ''}. "
                f"Total: ${row['totaldue']}."
            ),
        }
        for row in rows
    ]


async def run_all_rules() -> list[dict]:
    """Run all monitor rules and return combined alert list."""
    stale = await detect_stale_orders()
    overdue = await detect_overdue_orders()
    return stale + overdue
