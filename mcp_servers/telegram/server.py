"""
MCP Server: Telegram Bot

Connects Claude Code to Telegram via the Bot API.
Replaces WhatsApp for demo simplicity — setup takes ~5 minutes.

Setup:
  1. Message @BotFather on Telegram → /newbot → get your BOT_TOKEN
  2. Message your new bot → /start
  3. Run: python mcp_servers/telegram/server.py --get-chat-id
     to retrieve your TELEGRAM_OPERATOR_CHAT_ID
  4. Add both values to .env

READ tools  (autonomous):  draft_message, get_chat_id
WRITE tools (need approval): send_message, send_alert

Run:  python mcp_servers/telegram/server.py
Env:  TELEGRAM_BOT_TOKEN, TELEGRAM_OPERATOR_CHAT_ID
"""

import os
import sys

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("telegram")

BOT_TOKEN   = os.environ.get("TELEGRAM_BOT_TOKEN", "")
OPERATOR_ID = os.environ.get("TELEGRAM_OPERATOR_CHAT_ID", "")

API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _post(method: str, payload: dict) -> dict:
    with httpx.Client(timeout=10.0) as client:
        r = client.post(f"{API_BASE}/{method}", json=payload)
        data = r.json()
        if not data.get("ok"):
            raise RuntimeError(f"Telegram API error: {data.get('description', data)}")
        return data["result"]


def _get(method: str, params: dict | None = None) -> dict:
    with httpx.Client(timeout=10.0) as client:
        r = client.get(f"{API_BASE}/{method}", params=params or {})
        data = r.json()
        if not data.get("ok"):
            raise RuntimeError(f"Telegram API error: {data.get('description', data)}")
        return data["result"]


# ── Tools ─────────────────────────────────────────────────────────────────────

@mcp.tool()
def draft_message(
    customer_name: str,
    order_id: str,
    situation: str,
    tone: str = "friendly",
) -> dict:
    """
    Generate a Telegram/WhatsApp-style message for a customer given the
    order situation. Returns the draft text — does NOT send anything.
    Always call this before send_message so the operator can review the text.
    tone: 'friendly' (default) or 'formal'.
    """
    if tone == "formal":
        text = (
            f"Estimado/a {customer_name},\n\n"
            f"Le escribimos en relación a su pedido #{order_id}.\n"
            f"{situation}\n\n"
            f"Quedamos a su disposición para cualquier consulta.\n"
            f"Saludos, el equipo de la tienda."
        )
    else:
        text = (
            f"Hola {customer_name} 👋\n\n"
            f"Te escribimos sobre tu pedido #{order_id}.\n"
            f"{situation}\n\n"
            f"Cualquier consulta, estamos acá. ¡Gracias!"
        )

    return {
        "draft": text,
        "character_count": len(text),
        "note": "This is a draft. Call send_message with an approved approval_id to send.",
    }


@mcp.tool()
def send_message(
    message: str,
    approval_id: int,
    chat_id: str = "",
) -> dict:
    """
    Send a Telegram message to the customer or operator.
    REQUIRES approval_id — this is a WRITE action that must be explicitly
    approved via the pending_approvals gate before calling.
    chat_id defaults to TELEGRAM_OPERATOR_CHAT_ID if not provided.
    """
    if not approval_id:
        return {
            "error": "approval_id is required. Create a pending approval via the spineagent "
                     "create_pending_approval tool and get operator sign-off first."
        }
    if not BOT_TOKEN:
        return {"error": "TELEGRAM_BOT_TOKEN not set in environment"}

    target = chat_id or OPERATOR_ID
    if not target:
        return {
            "error": "No chat_id provided and TELEGRAM_OPERATOR_CHAT_ID not set. "
                     "Run with --get-chat-id to find your chat ID."
        }

    try:
        result = _post("sendMessage", {
            "chat_id": target,
            "text": message,
            "parse_mode": "Markdown",
        })
        return {
            "message_id": result["message_id"],
            "chat_id": result["chat"]["id"],
            "status": "sent",
            "approval_id_used": approval_id,
        }
    except Exception as e:
        return {"error": str(e), "status": "failed"}


@mcp.tool()
def send_alert(
    alert_text: str,
    approval_id: int,
    level: str = "WARNING",
) -> dict:
    """
    Send a Monitor-mode alert to the operator's Telegram chat.
    Used by Monitor mode to notify the operator of anomalies detected in
    the spine (stale orders, stock issues, etc.).
    REQUIRES approval_id — alerts are WRITE actions.
    level: WARNING, HIGH, or CRITICAL.
    """
    if not approval_id:
        return {"error": "approval_id is required even for alerts"}
    if not BOT_TOKEN or not OPERATOR_ID:
        return {"error": "TELEGRAM_BOT_TOKEN and TELEGRAM_OPERATOR_CHAT_ID must be set"}

    icons = {"WARNING": "⚠️", "HIGH": "🔴", "CRITICAL": "🚨"}
    icon = icons.get(level, "⚠️")
    formatted = f"{icon} *SpineAgent Alert — {level}*\n\n{alert_text}"

    try:
        result = _post("sendMessage", {
            "chat_id": OPERATOR_ID,
            "text": formatted,
            "parse_mode": "Markdown",
        })
        return {
            "message_id": result["message_id"],
            "status": "sent",
            "level": level,
            "approval_id_used": approval_id,
        }
    except Exception as e:
        return {"error": str(e), "status": "failed"}


@mcp.tool()
def get_chat_id() -> dict:
    """
    Retrieve recent updates from the bot to find your chat ID.
    Use this once during setup: message your bot on Telegram, then call
    this tool — it will return the chat_id you should set as
    TELEGRAM_OPERATOR_CHAT_ID in your .env file.
    """
    if not BOT_TOKEN:
        return {"error": "TELEGRAM_BOT_TOKEN not set"}

    try:
        updates = _get("getUpdates", {"limit": 5, "offset": -5})
        if not updates:
            return {
                "instruction": "No messages found. Open Telegram, message your bot "
                               "with /start, then call this tool again."
            }
        chats = [
            {
                "chat_id": u["message"]["chat"]["id"],
                "from": u["message"]["from"].get("username", u["message"]["from"]["id"]),
                "text": u["message"].get("text", ""),
            }
            for u in updates
            if "message" in u
        ]
        return {
            "recent_chats": chats,
            "instruction": "Copy the chat_id from your message and set TELEGRAM_OPERATOR_CHAT_ID in .env",
        }
    except Exception as e:
        return {"error": str(e)}


# ── CLI helper for first-time setup ──────────────────────────────────────────

if __name__ == "__main__":
    if "--get-chat-id" in sys.argv:
        import json
        result = get_chat_id()
        print(json.dumps(result, indent=2))
        sys.exit(0)

    if not BOT_TOKEN:
        print("[telegram] WARNING: TELEGRAM_BOT_TOKEN not set")
        print("[telegram] Message @BotFather on Telegram to create a bot and get a token")
    else:
        print(f"[telegram] Bot token loaded. Operator chat ID: {OPERATOR_ID or '(not set — run --get-chat-id)'}")

    mcp.run()
