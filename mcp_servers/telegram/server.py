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
import re
import sys

import httpx
import yaml
from mcp.server.fastmcp import FastMCP

# Resolve config/providers.yaml from any working directory
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PROVIDERS_PATH = os.path.join(_ROOT, "config", "providers.yaml")


def _load_providers() -> dict:
    """Return providers dict keyed by provider_id."""
    with open(_PROVIDERS_PATH) as f:
        data = yaml.safe_load(f)
    return data.get("providers", {})


def _get_provider(provider_id: str) -> dict | None:
    providers = _load_providers()
    return providers.get(provider_id)

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


# ── Provider tools ────────────────────────────────────────────────────────────

# Keywords used to interpret free-form provider replies
_YES = {
    "si", "sí", "yes", "confirmo", "confirmado", "confirmamos",
    "ok", "dale", "va", "acepto", "afirmativo", "correcto",
    "adelante", "disponible", "tenemos",
}
_NO = {
    "no", "rechazo", "rechazado", "rechazamos", "negativo",
    "imposible", "cancelar", "cancelamos",
}
_NO_PHRASES = [
    "no puedo", "no podemos", "no disponible", "sin stock",
    "no tenemos", "lo siento", "disculpa", "no hay",
]
_YES_PHRASES = [
    "de acuerdo", "claro que si", "claro que sí", "por supuesto",
    "sin problema", "confirmado el pedido", "con gusto",
]


def _interpret_response(text: str) -> str:
    """Return 'confirmed', 'rejected', or 'unclear' from free-form text."""
    t = re.sub(r"[^\w\s]", " ", text.lower().strip())
    words = set(t.split())

    if words & _YES or any(p in t for p in _YES_PHRASES):
        return "confirmed"
    if words & _NO or any(p in t for p in _NO_PHRASES):
        return "rejected"
    return "unclear"


@mcp.tool()
def send_provider_request(
    provider_id: str,
    product_name: str,
    quantity: int,
    unit_price: float,
    description: str,
    request_id: int,
    approval_id: int,
) -> dict:
    """
    Send a formatted stock-request message to a provider via Telegram.
    The provider is looked up from config/providers.yaml by provider_id.

    WRITE action — requires approval_id (the request_id from create_restock_request).
    Returns telegram message_id; store it via spineagent.update_restock_state.

    provider_id: key in providers.yaml (e.g. 'bike_provider')
    request_id:  restock request ID (for reference in the message)
    approval_id: must equal request_id — operator must have approved first
    """
    if not approval_id:
        return {
            "error": "approval_id required. Call spineagent.create_restock_request "
                     "and get operator approval before contacting the provider."
        }
    if not BOT_TOKEN:
        return {"error": "TELEGRAM_BOT_TOKEN not set in environment"}

    provider = _get_provider(provider_id)
    if not provider:
        return {"error": f"Provider '{provider_id}' not found in config/providers.yaml"}

    chat_id = provider["telegram_chat_id"]

    message = (
        f"🚲 *Solicitud de Stock — SpineAgent*\n\n"
        f"Hola! Los contactamos desde nuestra tienda para una consulta de stock.\n\n"
        f"📦 *Producto:* {product_name}\n"
        f"🔢 *Cantidad solicitada:* {quantity} unidades\n"
        f"💰 *Precio objetivo:* ${unit_price:,.2f} c/u\n\n"
        f"📋 *Descripción:* {description}\n\n"
        f"¿Pueden proveer este stock? Por favor respondan:\n"
        f"✅ *SI* — pueden proveer el stock\n"
        f"❌ *NO* — no está disponible\n\n"
        f"Referencia de solicitud: *#{request_id}*\n\n"
        f"Gracias! — SpineAgent"
    )

    try:
        result = _post("sendMessage", {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown",
        })
        return {
            "message_id": result["message_id"],
            "chat_id": chat_id,
            "provider": provider["name"],
            "status": "sent",
            "approval_id_used": approval_id,
            "note": "Store message_id via spineagent.update_restock_state",
        }
    except Exception as e:
        return {"error": str(e), "status": "failed"}


@mcp.tool()
def poll_provider_response(
    provider_id: str,
    last_update_id: int = 0,
) -> dict:
    """
    Poll Telegram for messages from a specific provider and interpret the reply.

    Calls getUpdates with offset = last_update_id + 1 so already-read messages
    are skipped. Filters only messages from the provider's chat_id.
    Interprets free-form text (Spanish/English) as 'confirmed', 'rejected',
    or 'unclear'.

    Always store the returned new_update_id via spineagent.update_restock_state
    so the next poll doesn't re-read the same messages.

    Returns:
      found          — bool, whether a new message was found
      response_type  — 'confirmed' | 'rejected' | 'unclear' | 'none'
      raw_text       — the provider's actual message text (if any)
      new_update_id  — update_id to store for the next poll
    """
    if not BOT_TOKEN:
        return {"error": "TELEGRAM_BOT_TOKEN not set in environment"}

    provider = _get_provider(provider_id)
    if not provider:
        return {"error": f"Provider '{provider_id}' not found in config/providers.yaml"}

    provider_chat_id = str(provider["telegram_chat_id"])

    params: dict = {"limit": 20, "timeout": 0}
    if last_update_id > 0:
        params["offset"] = last_update_id + 1

    try:
        updates = _get("getUpdates", params)
    except Exception as e:
        return {"error": str(e), "found": False, "response_type": "none", "new_update_id": last_update_id}

    if not updates:
        return {"found": False, "response_type": "none", "raw_text": "", "new_update_id": last_update_id}

    # Track max update_id seen regardless of source (needed to advance offset)
    max_update_id = max(u["update_id"] for u in updates)

    # Filter: only text messages from the provider's chat
    provider_msgs = [
        u for u in updates
        if "message" in u
        and str(u["message"]["chat"]["id"]) == provider_chat_id
        and "text" in u["message"]
    ]

    if not provider_msgs:
        return {
            "found": False,
            "response_type": "none",
            "raw_text": "",
            "new_update_id": max_update_id,
        }

    # Take the most recent message from the provider
    latest = max(provider_msgs, key=lambda u: u["update_id"])
    raw_text = latest["message"]["text"]
    response_type = _interpret_response(raw_text)

    return {
        "found": True,
        "response_type": response_type,
        "raw_text": raw_text,
        "new_update_id": max_update_id,
        "provider": provider["name"],
        "note": (
            "Interpretation is 'unclear' — review raw_text and decide manually."
            if response_type == "unclear" else
            f"Provider replied: {response_type}. "
            "Call spineagent.confirm_restock_request or cancel_restock_request accordingly."
        ),
    }


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
