#!/usr/bin/env python3
"""SpineAgent interactive CLI — chat with the agent in your terminal."""

from __future__ import annotations

import asyncio
import sys

from agent.core import SpineAgent


BANNER = """
╔══════════════════════════════════════════════╗
║           SpineAgent — Modo Assist           ║
║  Ask questions about orders, customers,      ║
║  products, and inventory.                    ║
║  Type 'exit' or Ctrl+C to quit.             ║
╚══════════════════════════════════════════════╝
"""


async def main() -> None:
    print(BANNER)
    agent = SpineAgent()

    while True:
        try:
            message = input("\n> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nChau!")
            break

        if not message:
            continue
        if message.lower() in ("exit", "quit", "q"):
            print("Chau!")
            break

        print("  Pensando...")
        try:
            response = await agent.handle_message(message)
            print(f"\n{response}")
        except Exception as exc:
            print(f"\n  Error: {exc}")


if __name__ == "__main__":
    asyncio.run(main())
