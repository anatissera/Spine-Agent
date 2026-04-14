"""
Tool implementations for the agent.

Each public method on ToolExecutor maps to a tool name and returns a string
result (success or error message). The agent's agentic loop calls
``ToolExecutor.dispatch(name, inputs)`` for every tool-use block.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

# Restock escalation schedule (minutes between follow-ups)
_ESCALATION_SCHEDULE = [30, 60, 120, 240]

# NLP interpretation sets for provider Telegram replies
_YES_WORDS = {
    "si", "sí", "yes", "confirmo", "confirmado", "confirmamos",
    "ok", "dale", "acepto", "afirmativo", "correcto", "adelante", "disponible",
}
_NO_WORDS = {
    "no", "rechazo", "rechazado", "rechazamos", "negativo",
    "imposible", "cancelar", "cancelamos",
}
_YES_PHRASES = ["de acuerdo", "claro que si", "claro que sí", "por supuesto", "sin problema"]
_NO_PHRASES = ["no puedo", "no podemos", "sin stock", "no disponible", "lo siento", "no hay", "no tenemos"]


def _next_followup_at(retry_count: int) -> str | None:
    """Return ISO timestamp for next follow-up, or None when max retries exceeded."""
    if retry_count >= len(_ESCALATION_SCHEDULE):
        return None
    return (datetime.now(timezone.utc) + timedelta(minutes=_ESCALATION_SCHEDULE[retry_count])).isoformat()


def _interpret_response(text: str) -> str:
    """Classify free-form provider reply as 'confirmed', 'rejected', or 'unclear'."""
    t = re.sub(r"[^\w\s]", " ", text.lower().strip())
    words = set(t.split())
    if words & _YES_WORDS or any(p in t for p in _YES_PHRASES):
        return "confirmed"
    if words & _NO_WORDS or any(p in t for p in _NO_PHRASES):
        return "rejected"
    return "unclear"

if TYPE_CHECKING:
    from skills import SkillsRegistry


class ToolExecutor:
    def __init__(
        self,
        cwd: str,
        skills: "SkillsRegistry",
        db_host: str = "localhost",
        db_port: int = 5433,
        db_name: str = "adventureworks",
        db_user: str = "postgres",
        db_password: str = "postgres",
    ):
        self.cwd = cwd
        self.skills = skills
        self._todos: list[dict] = []
        self._db_host = db_host
        self._db_port = db_port
        self._db_name = db_name
        self._db_user = db_user
        self._db_password = db_password
        self._conn = None

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def dispatch(self, name: str, inputs: dict) -> str:
        try:
            match name:
                case "ls":
                    return self._ls(**inputs)
                case "read_file":
                    return self._read_file(**inputs)
                case "write_file":
                    return self._write_file(**inputs)
                case "edit_file":
                    return self._edit_file(**inputs)
                case "glob":
                    return self._glob(**inputs)
                case "grep":
                    return self._grep(**inputs)
                case "write_todos":
                    return self._write_todos(**inputs)
                case "read_skill":
                    return self._read_skill(**inputs)
                case "run_sql":
                    return self._run_sql(**inputs)
                # ── Restock & Publish ──────────────────────────────────
                case "create_restock_request":
                    return self._create_restock_request(**inputs)
                case "get_restock_request":
                    return self._get_restock_request(**inputs)
                case "update_restock_state":
                    return self._update_restock_state(**inputs)
                case "cancel_restock_request":
                    return self._cancel_restock_request(**inputs)
                case "confirm_restock_request":
                    return self._confirm_restock_request(**inputs)
                case "create_pending_approval":
                    return self._create_pending_approval(**inputs)
                case "send_provider_request":
                    return self._send_provider_request(**inputs)
                case "poll_provider_response":
                    return self._poll_provider_response(**inputs)
                case "create_product":
                    return self._create_product_tn(**inputs)
                case _:
                    return f"Error: unknown tool '{name}'"
        except TypeError as e:
            return f"Error: bad arguments for '{name}': {e}"
        except Exception as e:
            return f"Error: {e}"

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------

    def _resolve(self, path: str) -> Path:
        p = Path(path)
        if not p.is_absolute():
            p = Path(self.cwd) / p
        return p.resolve()

    # ------------------------------------------------------------------
    # Filesystem tools
    # ------------------------------------------------------------------

    def _ls(self, path: str = "") -> str:
        target = self._resolve(path or self.cwd)
        if not target.exists():
            return f"Error: path not found: {target}"
        if not target.is_dir():
            return f"Error: not a directory: {target}"

        entries = []
        for child in sorted(target.iterdir()):
            stat = child.stat()
            kind = "dir " if child.is_dir() else "file"
            name = child.name + ("/" if child.is_dir() else "")
            entries.append(f"{kind}  {stat.st_size:>10}  {name}")

        if not entries:
            return "(empty directory)"
        return "\n".join(entries)

    def _read_file(self, path: str, offset: int = 1, limit: int | None = None) -> str:
        target = self._resolve(path)
        if not target.exists():
            return f"Error: file not found: {target}"
        if not target.is_file():
            return f"Error: not a file: {target}"

        lines = target.read_text(errors="replace").splitlines()
        start = max(0, (offset or 1) - 1)
        end = (start + limit) if limit else len(lines)
        chunk = lines[start:end]

        numbered = [f"{start + i + 1}\t{line}" for i, line in enumerate(chunk)]
        header = f"# {target}  (lines {start + 1}–{min(end, len(lines))} of {len(lines)})\n"
        return header + "\n".join(numbered)

    def _write_file(self, path: str, content: str) -> str:
        target = self._resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        return f"Written {len(content)} bytes to {target}"

    def _edit_file(
        self,
        path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False,
    ) -> str:
        target = self._resolve(path)
        if not target.exists():
            return f"Error: file not found: {target}"

        original = target.read_text()
        if old_string not in original:
            return f"Error: string not found in {target}"

        if replace_all:
            updated = original.replace(old_string, new_string)
            count = original.count(old_string)
        else:
            updated = original.replace(old_string, new_string, 1)
            count = 1

        target.write_text(updated)
        return f"Replaced {count} occurrence(s) in {target}"

    def _glob(self, pattern: str, path: str = "") -> str:
        root = self._resolve(path or self.cwd)
        if not root.exists():
            return f"Error: path not found: {root}"

        matches = sorted(root.glob(pattern))
        if not matches:
            return f"No files match '{pattern}' in {root}"
        return "\n".join(str(m.relative_to(root)) for m in matches)

    def _grep(
        self,
        pattern: str,
        path: str = "",
        output_mode: str = "files_with_matches",
        context_lines: int = 0,
        include: str | None = None,
    ) -> str:
        root = self._resolve(path or self.cwd)
        try:
            regex = re.compile(pattern, re.MULTILINE)
        except re.error as e:
            return f"Error: invalid regex — {e}"

        if root.is_file():
            files = [root]
        else:
            glob_pat = f"**/{include}" if include else "**/*"
            files = [f for f in root.glob(glob_pat) if f.is_file()]

        results: list[str] = []

        for fpath in sorted(files):
            try:
                text = fpath.read_text(errors="replace")
            except Exception:
                continue

            rel = str(fpath.relative_to(root)) if not root.is_file() else str(fpath)

            if output_mode == "files_with_matches":
                if regex.search(text):
                    results.append(rel)

            elif output_mode == "count":
                n = len(regex.findall(text))
                if n:
                    results.append(f"{rel}: {n}")

            elif output_mode == "content":
                lines = text.splitlines()
                prev_end = -1
                for i, line in enumerate(lines):
                    if not regex.search(line):
                        continue
                    start = max(0, i - context_lines)
                    end = min(len(lines), i + context_lines + 1)
                    if start > prev_end + 1 and prev_end >= 0:
                        results.append("--")
                    for j in range(start, end):
                        marker = ">" if j == i else " "
                        results.append(f"{rel}:{j + 1}{marker} {lines[j]}")
                    prev_end = end - 1

        if not results:
            return f"No matches for '{pattern}'"
        return "\n".join(results)

    # ------------------------------------------------------------------
    # Planning tool
    # ------------------------------------------------------------------

    def _write_todos(self, todos: list[dict]) -> str:
        self._todos = todos
        icons = {"pending": "○", "in_progress": "◐", "completed": "●"}
        lines = []
        for t in todos:
            icon = icons.get(t.get("status", ""), "?")
            lines.append(f"{icon} [{t.get('status', '?')}]  {t.get('id', '?')}: {t.get('content', '')}")
        return "Todo list updated:\n" + "\n".join(lines)

    # ------------------------------------------------------------------
    # Database tool
    # ------------------------------------------------------------------

    def _db_connect(self):
        """Lazy-connect and return a live psycopg2 connection."""
        try:
            import psycopg2
            import psycopg2.extras
        except ImportError:
            raise RuntimeError("psycopg2 not installed. Run: pip install psycopg2-binary")

        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(
                host=self._db_host,
                port=self._db_port,
                dbname=self._db_name,
                user=self._db_user,
                password=self._db_password,
                cursor_factory=psycopg2.extras.RealDictCursor,
            )
            self._conn.autocommit = True
        return self._conn

    def _run_sql(self, query: str, params: list | None = None) -> str:
        import psycopg2

        try:
            conn = self._db_connect()
        except Exception as e:
            return f"Error: could not connect to database: {e}"

        try:
            with conn.cursor() as cur:
                cur.execute(query, params or None)

                if cur.description is None:
                    # DML / DDL — no result set
                    return f"{cur.rowcount} row(s) affected"

                rows = cur.fetchmany(100)
                if not rows:
                    return "(no rows returned)"

                headers = [d.name for d in cur.description]
                col_widths = [len(h) for h in headers]
                str_rows: list[list[str]] = []
                for row in rows:
                    cells = [str(row[h]) if row[h] is not None else "NULL" for h in headers]
                    str_rows.append(cells)
                    for i, cell in enumerate(cells):
                        col_widths[i] = max(col_widths[i], min(len(cell), 40))

                def fmt_row(cells: list[str]) -> str:
                    return "| " + " | ".join(
                        cell[:40].ljust(col_widths[i]) for i, cell in enumerate(cells)
                    ) + " |"

                sep = "|-" + "-|-".join("-" * w for w in col_widths) + "-|"
                lines = [fmt_row(headers), sep]
                lines += [fmt_row(r) for r in str_rows]
                if len(rows) == 100:
                    lines.append("(results truncated at 100 rows)")
                return "\n".join(lines)

        except psycopg2.Error as e:
            self._conn = None  # force reconnect on next call
            return f"Error: {e}"

    # ------------------------------------------------------------------
    # Skill loader
    # ------------------------------------------------------------------

    def _read_skill(self, skill_name: str) -> str:
        return self.skills.load(skill_name)

    # ------------------------------------------------------------------
    # Restock & Publish — DB helpers (psycopg2)
    # ------------------------------------------------------------------

    def _load_provider(self, provider_id: str) -> dict | None:
        """Load provider config from config/providers.yaml."""
        try:
            import yaml
        except ImportError:
            return None
        providers_path = Path(self.cwd) / "config" / "providers.yaml"
        if not providers_path.exists():
            return None
        with open(providers_path) as f:
            data = yaml.safe_load(f)
        return data.get("providers", {}).get(provider_id)

    def _create_restock_request(
        self,
        product_name: str,
        product_description: str,
        price: float,
        quantity: int,
        provider_id: str,
        sku: str = "",
    ) -> str:
        provider = self._load_provider(provider_id)
        if not provider:
            return json.dumps({"error": f"Provider '{provider_id}' not found in config/providers.yaml"})

        now = datetime.now(timezone.utc)
        action_payload = {
            "request_type": "provider_restock_request",
            "product": {"name": product_name, "description": product_description,
                        "price": price, "quantity_requested": quantity, "sku": sku},
            "provider": {"id": provider_id, "name": provider["name"],
                         "chat_id": provider["telegram_chat_id"]},
            "telegram": {"sent_messages": [], "last_update_id": 0},
            "escalation": {
                "retry_count": 0,
                "schedule_minutes": _ESCALATION_SCHEDULE,
                "next_followup_at": _next_followup_at(0),
                "started_at": now.isoformat(),
            },
        }

        try:
            conn = self._db_connect()
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO spine_agent.pending_approvals
                        (spine_object_id, action_type, action_payload, context, expires_at)
                    VALUES (%s, 'provider_restock_request', %s::jsonb, %s::jsonb,
                            NOW() + INTERVAL '8 hours')
                    RETURNING id, created_at, expires_at
                """, (
                    f"Product:restock:{product_name}",
                    json.dumps(action_payload),
                    json.dumps({"why": f"User wants to publish '{product_name}' — needs stock from {provider_id}"}),
                ))
                row = cur.fetchone()
            return json.dumps({
                "request_id": row["id"],
                "approval_id": row["id"],
                "status": "pending_operator_approval",
                "product": product_name,
                "provider": provider["name"],
                "quantity": quantity,
                "price": price,
                "next_followup_at": action_payload["escalation"]["next_followup_at"],
                "instruction": f"Show approval #{row['id']} to operator. Wait for APPROVE before calling send_provider_request.",
            }, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)})

    def _get_restock_request(self, request_id: int) -> str:
        try:
            conn = self._db_connect()
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, spine_object_id, action_payload, status,
                           created_at, expires_at, decided_at, decision_note
                    FROM spine_agent.pending_approvals
                    WHERE id = %s AND action_type = 'provider_restock_request'
                """, (request_id,))
                row = cur.fetchone()
        except Exception as e:
            return json.dumps({"error": str(e)})

        if not row:
            return json.dumps({"error": f"Restock request {request_id} not found"})

        payload = row["action_payload"]
        if isinstance(payload, str):
            payload = json.loads(payload)

        next_followup = payload["escalation"].get("next_followup_at")
        is_followup_due = False
        if next_followup and row["status"] == "pending":
            try:
                followup_dt = datetime.fromisoformat(next_followup)
                is_followup_due = datetime.now(timezone.utc) > followup_dt
            except ValueError:
                pass

        return json.dumps({
            "request_id": row["id"],
            "status": row["status"],
            "product": payload["product"],
            "provider": payload["provider"],
            "telegram": payload["telegram"],
            "escalation": payload["escalation"],
            "is_followup_due": is_followup_due,
            "created_at": row["created_at"],
            "expires_at": row["expires_at"],
        }, default=str)

    def _update_restock_state(
        self,
        request_id: int,
        last_telegram_update_id: int,
        new_retry_count: int,
        telegram_message_id: int = 0,
    ) -> str:
        try:
            conn = self._db_connect()
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT action_payload FROM spine_agent.pending_approvals WHERE id = %s",
                    (request_id,),
                )
                row = cur.fetchone()
                if not row:
                    return json.dumps({"error": f"Request {request_id} not found"})

                payload = row["action_payload"]
                if isinstance(payload, str):
                    payload = json.loads(payload)

                payload["telegram"]["last_update_id"] = last_telegram_update_id
                if telegram_message_id:
                    payload["telegram"]["sent_messages"].append({
                        "message_id": telegram_message_id,
                        "sent_at": datetime.now(timezone.utc).isoformat(),
                        "retry_number": new_retry_count,
                    })

                next_followup = _next_followup_at(new_retry_count)
                payload["escalation"]["retry_count"] = new_retry_count
                payload["escalation"]["next_followup_at"] = next_followup

                cur.execute(
                    "UPDATE spine_agent.pending_approvals SET action_payload = %s::jsonb WHERE id = %s",
                    (json.dumps(payload), request_id),
                )
            return json.dumps({
                "request_id": request_id,
                "retry_count": new_retry_count,
                "next_followup_at": next_followup,
                "max_retries_reached": next_followup is None,
            })
        except Exception as e:
            return json.dumps({"error": str(e)})

    def _cancel_restock_request(self, request_id: int, reason: str) -> str:
        try:
            conn = self._db_connect()
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE spine_agent.pending_approvals
                    SET status = 'expired', decision_note = %s, decided_at = NOW()
                    WHERE id = %s AND action_type = 'provider_restock_request'
                    RETURNING id
                """, (reason, request_id))
                row = cur.fetchone()
            if not row:
                return json.dumps({"error": f"Request {request_id} not found"})
            return json.dumps({"request_id": row["id"], "status": "expired", "reason": reason})
        except Exception as e:
            return json.dumps({"error": str(e)})

    def _confirm_restock_request(self, request_id: int, provider_response: str) -> str:
        try:
            conn = self._db_connect()
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE spine_agent.pending_approvals
                    SET status = 'approved', approved_by = 'provider',
                        decision_note = %s, decided_at = NOW()
                    WHERE id = %s AND action_type = 'provider_restock_request'
                    RETURNING id, action_payload
                """, (provider_response, request_id))
                row = cur.fetchone()
            if not row:
                return json.dumps({"error": f"Request {request_id} not found"})
            payload = row["action_payload"]
            if isinstance(payload, str):
                payload = json.loads(payload)
            return json.dumps({
                "request_id": row["id"],
                "status": "approved",
                "provider_response": provider_response,
                "product_to_publish": payload["product"],
                "instruction": "Create a new pending approval with action_type='tiendanube_create_product', get operator sign-off, then call create_product.",
            })
        except Exception as e:
            return json.dumps({"error": str(e)})

    def _create_pending_approval(
        self,
        spine_id: str,
        action_type: str,
        action_payload: dict,
        context_why: str,
    ) -> str:
        try:
            conn = self._db_connect()
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO spine_agent.pending_approvals
                        (spine_object_id, action_type, action_payload, context, expires_at)
                    VALUES (%s, %s, %s::jsonb, %s::jsonb, NOW() + INTERVAL '2 hours')
                    RETURNING id, created_at, expires_at
                """, (
                    spine_id, action_type,
                    json.dumps(action_payload),
                    json.dumps({"why": context_why}),
                ))
                row = cur.fetchone()
            return json.dumps({
                "approval_id": row["id"],
                "status": "pending",
                "instruction": f"Approval #{row['id']} created. Present to operator and wait for APPROVE.",
            }, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)})

    # ------------------------------------------------------------------
    # Restock & Publish — Telegram helpers
    # ------------------------------------------------------------------

    def _send_provider_request(
        self,
        provider_id: str,
        product_name: str,
        quantity: int,
        unit_price: float,
        description: str,
        request_id: int,
        approval_id: int,
    ) -> str:
        if not approval_id:
            return json.dumps({"error": "approval_id required — get operator approval first"})

        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        if not bot_token:
            return json.dumps({"error": "TELEGRAM_BOT_TOKEN not set in .env"})

        provider = self._load_provider(provider_id)
        if not provider:
            return json.dumps({"error": f"Provider '{provider_id}' not found"})

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
            f"Referencia: *#{request_id}*\n\nGracias! — SpineAgent"
        )

        try:
            import httpx
            with httpx.Client(timeout=10.0) as client:
                r = client.post(
                    f"https://api.telegram.org/bot{bot_token}/sendMessage",
                    json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"},
                )
                data = r.json()
                if not data.get("ok"):
                    return json.dumps({"error": data.get("description", data)})
                return json.dumps({
                    "message_id": data["result"]["message_id"],
                    "chat_id": chat_id,
                    "provider": provider["name"],
                    "status": "sent",
                })
        except Exception as e:
            return json.dumps({"error": str(e)})

    def _poll_provider_response(self, provider_id: str, last_update_id: int = 0) -> str:
        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        if not bot_token:
            return json.dumps({"error": "TELEGRAM_BOT_TOKEN not set in .env"})

        provider = self._load_provider(provider_id)
        if not provider:
            return json.dumps({"error": f"Provider '{provider_id}' not found"})

        provider_chat_id = str(provider["telegram_chat_id"])
        params: dict = {"limit": 20, "timeout": 0}
        if last_update_id > 0:
            params["offset"] = last_update_id + 1

        try:
            import httpx
            with httpx.Client(timeout=15.0) as client:
                r = client.get(
                    f"https://api.telegram.org/bot{bot_token}/getUpdates",
                    params=params,
                )
                data = r.json()
                if not data.get("ok"):
                    return json.dumps({"error": data.get("description", data)})
                updates = data["result"]
        except Exception as e:
            return json.dumps({"error": str(e), "found": False, "response_type": "none"})

        if not updates:
            return json.dumps({"found": False, "response_type": "none", "raw_text": "", "new_update_id": last_update_id})

        max_update_id = max(u["update_id"] for u in updates)
        provider_msgs = [
            u for u in updates
            if "message" in u
            and str(u["message"]["chat"]["id"]) == provider_chat_id
            and "text" in u["message"]
        ]

        if not provider_msgs:
            return json.dumps({"found": False, "response_type": "none", "raw_text": "", "new_update_id": max_update_id})

        latest = max(provider_msgs, key=lambda u: u["update_id"])
        raw_text = latest["message"]["text"]
        response_type = _interpret_response(raw_text)

        return json.dumps({
            "found": True,
            "response_type": response_type,
            "raw_text": raw_text,
            "new_update_id": max_update_id,
            "provider": provider["name"],
        })

    # ------------------------------------------------------------------
    # Restock & Publish — Tiendanube helpers
    # ------------------------------------------------------------------

    def _create_product_tn(
        self,
        name: str,
        description: str,
        price: float,
        stock: int,
        approval_id: int,
        sku: str = "",
    ) -> str:
        if not approval_id:
            return json.dumps({"error": "approval_id required — create a pending approval first"})

        store_id = os.environ.get("TIENDANUBE_STORE_ID", "")
        token = os.environ.get("TIENDANUBE_ACCESS_TOKEN", "")
        mock = os.environ.get("TIENDANUBE_MOCK", "false").lower() == "true"
        api_version = os.environ.get("TIENDANUBE_API_VERSION", "2025-03")

        if mock:
            import random
            fake_id = random.randint(10000, 99999)
            slug = re.sub(r"[^\w-]", "-", name.lower())
            return json.dumps({
                "id": fake_id,
                "name": name,
                "permalink": f"https://demo-store.mitiendanube.com/productos/{slug}",
                "stock": stock,
                "price": price,
                "status": "published",
                "approval_id_used": approval_id,
                "mode": "mock",
            })

        if not store_id or not token:
            return json.dumps({"error": "TIENDANUBE_STORE_ID or TIENDANUBE_ACCESS_TOKEN not set"})

        body = {
            "name": {"es": name},
            "description": {"es": description},
            "variants": [{"price": str(price), "stock": stock, **({"sku": sku} if sku else {})}],
        }

        try:
            import httpx
            headers = {
                "Authentication": f"bearer {token}",
                "User-Agent": "SpineAgent/1.0",
                "Content-Type": "application/json",
            }
            with httpx.Client(timeout=15.0) as client:
                r = client.post(
                    f"https://api.tiendanube.com/{api_version}/{store_id}/products",
                    headers=headers,
                    json=body,
                )
                if r.status_code in (400, 422):
                    return json.dumps({"error": f"Tiendanube validation error: {r.json()}"})
                r.raise_for_status()
                data = r.json()
            return json.dumps({
                "id": data["id"],
                "name": data.get("name", {}).get("es", name),
                "permalink": data.get("permalink", ""),
                "status": "published",
                "approval_id_used": approval_id,
            })
        except Exception as e:
            return json.dumps({"error": str(e)})
