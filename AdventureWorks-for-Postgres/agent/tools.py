"""
Tool implementations for the agent.

Each public method on ToolExecutor maps to a tool name and returns a string
result (success or error message). The agent's agentic loop calls
``ToolExecutor.dispatch(name, inputs)`` for every tool-use block.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from skills import SkillsRegistry


class ToolExecutor:
    def __init__(
        self,
        cwd: str,
        skills: "SkillsRegistry",
        db_host: str = "localhost",
        db_port: int = 5433,
        db_name: str = "Adventureworks",
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
