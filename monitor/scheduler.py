"""Monitor Scheduler — runs anomaly detection rules periodically.

Uses APScheduler to fire monitor rules at configurable intervals.
Can run as a standalone process or be started within the main agent.
"""

from __future__ import annotations

import asyncio
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from monitor.alerts import route_alerts
from monitor.rules import run_all_rules


async def monitor_tick() -> dict:
    """Execute one monitor cycle: run all rules and route alerts.

    Returns a summary dict. Can be called directly (for testing) or
    scheduled via APScheduler.
    """
    print(f"[Monitor] Tick at {datetime.now().strftime('%H:%M:%S')}...")
    alerts = await run_all_rules()

    if alerts:
        summary = await route_alerts(alerts)
        print(f"[Monitor] Routed {summary['total']} alert(s)")
    else:
        summary = {"total": 0, "timestamp": datetime.now().isoformat()}
        print("[Monitor] No anomalies detected")

    return summary


def create_scheduler(interval_minutes: int = 60) -> AsyncIOScheduler:
    """Create an APScheduler that runs monitor_tick at the given interval.

    Usage::

        scheduler = create_scheduler(interval_minutes=5)
        scheduler.start()
        # ... keep the event loop running ...
    """
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        monitor_tick,
        "interval",
        minutes=interval_minutes,
        id="spine_monitor",
        name="SpineAgent Monitor",
        replace_existing=True,
    )
    return scheduler


async def run_monitor(interval_minutes: int = 60) -> None:
    """Run the monitor as a standalone async loop.

    This is the entry point for running the monitor as its own process.
    """
    print(f"[Monitor] Starting with {interval_minutes}min interval...")

    # Run once immediately
    await monitor_tick()

    # Then schedule periodic runs
    scheduler = create_scheduler(interval_minutes)
    scheduler.start()

    try:
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        print("[Monitor] Shutting down...")
        scheduler.shutdown()


if __name__ == "__main__":
    import sys

    interval = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    asyncio.run(run_monitor(interval))
