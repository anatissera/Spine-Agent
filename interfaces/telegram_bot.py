#!/usr/bin/env python3
"""SpineAgent Telegram Bot — the agent's primary chat interface.

Routes all messages through SpineAgent (Assist + Act + approval gate).
Each Telegram user gets their own agent session with independent state.

Run:
    PYTHONPATH=. python interfaces/telegram_bot.py

Requires TELEGRAM_TOKEN in .env
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

from agent.core import SpineAgent
from interfaces.dashboard.helpers import run_async

logging.basicConfig(
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("spine-telegram")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN", "")

# Per-user agent sessions
_agents: dict[int, SpineAgent] = {}


def _get_agent(user_id: int) -> SpineAgent:
    """Get or create a SpineAgent session for a Telegram user."""
    if user_id not in _agents:
        _agents[user_id] = SpineAgent()
    return _agents[user_id]


# ── Commands ─────────────────────────────────────────────────────────────────


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start — greet the user and explain capabilities."""
    user = update.message.from_user.first_name
    await update.message.reply_text(
        f"Hola {user}, soy SpineAgent.\n\n"
        "Opero sobre el objeto raiz de tu negocio (ordenes de venta). "
        "Preguntame lo que necesites:\n\n"
        "Modo Assist — preguntame sobre ordenes, clientes, inventario\n"
        "Modo Act — pedime que ejecute acciones (con tu aprobacion)\n\n"
        "Comandos:\n"
        "/monitor — ver alertas de ordenes estancadas\n"
        "/skills — ver skills disponibles\n"
        "/spine <order_id> — ver el estado unificado de una orden\n"
        "/reset — reiniciar la sesion",
    )


async def cmd_monitor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /monitor — run stale order detection and show alerts."""
    await update.message.chat.send_action("typing")
    try:
        from monitor.rules import detect_stale_orders
        alerts = await detect_stale_orders(limit=5)
        if not alerts:
            await update.message.reply_text("Sin anomalias detectadas.")
            return
        lines = [f"*Monitor: {len(alerts)} alerta(s)*\n"]
        for a in alerts[:5]:
            level = "HIGH" if a["level"] == "HIGH" else "WARN"
            lines.append(
                f"[{level}] Orden #{a['order_id']}: {a['status_label']} "
                f"por {a['hours_stale']:.0f}h — {a['customer_name']} (${a['total_due']})"
            )
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"Error en monitor: {e}")


async def cmd_skills(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /skills — list all registered skills."""
    await update.message.chat.send_action("typing")
    try:
        from skills.registry import SkillRegistry
        reg = SkillRegistry()
        await reg.ensure_builtin_skills()
        all_skills = await reg.list_all()
        lines = [f"*{len(all_skills)} skills registradas:*\n"]
        for s in all_skills:
            lines.append(f"  `{s['name']}` ({s['domain']}) — usada {s.get('usage_count', 0)}x")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def cmd_spine(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /spine <order_id> — show unified spine object."""
    args = context.args
    if not args:
        await update.message.reply_text("Uso: /spine <order_id>\nEjemplo: /spine 43659")
        return

    try:
        order_id = int(args[0])
    except ValueError:
        await update.message.reply_text("El order_id debe ser un numero.")
        return

    await update.message.chat.send_action("typing")
    try:
        from agent.spine import get_spine
        spine = await get_spine(order_id)
        if spine is None:
            await update.message.reply_text(f"Orden {order_id} no encontrada.")
            return

        c = spine.customer
        text = (
            f"*Orden #{spine.sales_order_id}* — {spine.status_label}\n\n"
            f"*Cliente:* {c.first_name or ''} {c.last_name or ''}\n"
            f"*Email:* {c.email or '—'}\n"
            f"*Telefono:* {c.phone or '—'}\n"
            f"*Tienda:* {c.store_name or '—'}\n\n"
            f"*Total:* ${spine.total_due}\n"
            f"*Items:* {len(spine.items)}\n"
            f"*Fecha pedido:* {str(spine.order_date)[:10]}\n"
            f"*Fecha envio:* {str(spine.ship_date)[:10] if spine.ship_date else 'pendiente'}\n"
            f"*Envio a:* {spine.ship_to.city}, {spine.ship_to.state_province}\n"
        )
        await update.message.reply_text(text, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /reset — clear the user's agent session."""
    user_id = update.message.from_user.id
    if user_id in _agents:
        del _agents[user_id]
    await update.message.reply_text("Sesion reiniciada.")


# ── Message handler ──────────────────────────────────────────────────────────


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route all text messages through SpineAgent."""
    user_id = update.message.from_user.id
    message = update.message.text
    agent = _get_agent(user_id)

    await update.message.chat.send_action("typing")

    try:
        response = await agent.handle_message(message)
    except Exception as e:
        logger.error(f"Agent error for user {user_id}: {e}")
        response = f"Error interno del agente: {e}"

    # Telegram has a 4096 char limit per message
    for chunk in _split_message(response, 4000):
        await update.message.reply_text(chunk, parse_mode="Markdown")


def _split_message(text: str, max_len: int) -> list[str]:
    """Split a long message into chunks that fit Telegram's limit."""
    if len(text) <= max_len:
        return [text]
    chunks = []
    while text:
        if len(text) <= max_len:
            chunks.append(text)
            break
        # Try to split at a newline
        split_at = text.rfind("\n", 0, max_len)
        if split_at == -1:
            split_at = max_len
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    return chunks


# ── Main ─────────────────────────────────────────────────────────────────────


def main() -> None:
    if not TELEGRAM_TOKEN:
        print("Error: TELEGRAM_TOKEN not set in .env")
        print("1. Message @BotFather on Telegram -> /newbot")
        print("2. Add TELEGRAM_TOKEN=<your_token> to .env")
        sys.exit(1)

    print("Starting SpineAgent Telegram Bot...")
    print("Send /start to your bot to begin.")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("monitor", cmd_monitor))
    app.add_handler(CommandHandler("skills", cmd_skills))
    app.add_handler(CommandHandler("spine", cmd_spine))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()


if __name__ == "__main__":
    main()
