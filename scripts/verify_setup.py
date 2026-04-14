#!/usr/bin/env python3
"""Verify that the M0 infrastructure is up and working.

Checks:
  1. PostgreSQL is reachable
  2. AdventureWorks data is loaded
  3. pgvector extension is installed
  4. spine_agent schema tables exist
  5. Claude API responds
"""

import sys

import anthropic
import psycopg

from agent.config import get_settings

CHECKS_PASSED = 0
CHECKS_FAILED = 0


def check(label: str, fn):
    global CHECKS_PASSED, CHECKS_FAILED
    try:
        result = fn()
        print(f"  [OK] {label}: {result}")
        CHECKS_PASSED += 1
    except Exception as exc:
        print(f"  [FAIL] {label}: {exc}")
        CHECKS_FAILED += 1


def main():
    settings = get_settings()

    print("\n=== SpineAgent M0 — Setup Verification ===\n")

    # --- Database checks ---
    print("1. Database connectivity")
    conn = psycopg.connect(settings.database_url)

    check(
        "PostgreSQL version",
        lambda: conn.execute("SELECT version()").fetchone()[0].split(",")[0],
    )

    print("\n2. AdventureWorks data")
    check(
        "SalesOrderHeader count",
        lambda: f"{conn.execute('SELECT count(*) FROM sales.salesorderheader').fetchone()[0]} rows",
    )
    check(
        "Product count",
        lambda: f"{conn.execute('SELECT count(*) FROM production.product').fetchone()[0]} rows",
    )
    check(
        "Person count",
        lambda: f"{conn.execute('SELECT count(*) FROM person.person').fetchone()[0]} rows",
    )

    print("\n3. pgvector extension")
    check(
        "vector extension",
        lambda: conn.execute(
            "SELECT extversion FROM pg_extension WHERE extname = 'vector'"
        ).fetchone()[0],
    )

    print("\n4. spine_agent schema")
    tables = ["context_entries", "skills", "pending_approvals", "action_log"]
    for table in tables:
        check(
            f"table spine_agent.{table}",
            lambda t=table: conn.execute(
                f"SELECT count(*) FROM spine_agent.{t}"
            ).fetchone()[0]
            == 0
            and "exists (empty)",
        )

    conn.close()

    # --- Claude API check ---
    print("\n5. Claude API")
    if not settings.anthropic_api_key:
        print("  [SKIP] ANTHROPIC_API_KEY not set — skipping API check")
    else:
        def call_claude():
            client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
            resp = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=50,
                messages=[{"role": "user", "content": "Say 'SpineAgent ready' and nothing else."}],
            )
            return resp.content[0].text

        check("Claude API response", call_claude)

    # --- Summary ---
    total = CHECKS_PASSED + CHECKS_FAILED
    print(f"\n{'='*44}")
    print(f"  Results: {CHECKS_PASSED}/{total} checks passed")
    if CHECKS_FAILED:
        print(f"  {CHECKS_FAILED} check(s) FAILED")
        sys.exit(1)
    else:
        print("  All checks passed!")
    print()


if __name__ == "__main__":
    main()
