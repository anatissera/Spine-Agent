#!/usr/bin/env python3
"""
Agent built with the Anthropic SDK following Deep Agents harness patterns.

Architecture (from Agent_Arq/):
  - Progressive skill disclosure: frontmatter summaries in the system prompt;
    full skill content loaded via read_skill only when the agent decides it's
    relevant to the current task.
  - Virtual filesystem tools: ls, read_file, write_file, edit_file, glob, grep
  - Planning tool: write_todos
  - Streaming agentic loop with adaptive thinking (claude-opus-4-6)

Usage:
    python agent.py                         # interactive REPL
    python agent.py "list all .sql files"  # single task, then exit
    python agent.py --cwd /some/path --skills ./skills "your task"
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

import anthropic
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

from tools import ToolExecutor
from skills import SkillsRegistry

_console = Console(highlight=False)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MODEL = "claude-opus-4-6"
MAX_TOKENS = 16000

# ---------------------------------------------------------------------------
# Tool schemas (sent to the API every turn)
# ---------------------------------------------------------------------------

TOOL_SCHEMAS: list[dict] = [
    {
        "name": "ls",
        "description": "List files in a directory with kind, size, and name.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory to list. Defaults to the current working directory.",
                }
            },
        },
    },
    {
        "name": "read_file",
        "description": (
            "Read a file with line numbers. "
            "Use offset + limit to page through large files without loading everything."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path"},
                "offset": {
                    "type": "integer",
                    "description": "First line to read (1-indexed). Default: 1",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of lines to return.",
                },
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Create or overwrite a file with the given content.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Destination path"},
                "content": {"type": "string", "description": "File content"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "edit_file",
        "description": (
            "Perform an exact string replacement inside a file. "
            "Fails with an error if old_string is not present. "
            "Set replace_all=true to replace every occurrence."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File to edit"},
                "old_string": {"type": "string", "description": "Exact string to find"},
                "new_string": {"type": "string", "description": "Replacement string"},
                "replace_all": {
                    "type": "boolean",
                    "description": "Replace all occurrences. Default: false",
                },
            },
            "required": ["path", "old_string", "new_string"],
        },
    },
    {
        "name": "glob",
        "description": (
            "Find files matching a glob pattern, e.g. **/*.py or src/**/*.ts. "
            "Returns relative paths."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Glob pattern"},
                "path": {
                    "type": "string",
                    "description": "Root directory to search. Defaults to cwd.",
                },
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "grep",
        "description": "Search file contents using a regular expression.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Regex pattern"},
                "path": {
                    "type": "string",
                    "description": "File or directory. Defaults to cwd.",
                },
                "output_mode": {
                    "type": "string",
                    "enum": ["files_with_matches", "content", "count"],
                    "description": (
                        "files_with_matches (default) — paths only; "
                        "content — matching lines with optional context; "
                        "count — match count per file"
                    ),
                },
                "context_lines": {
                    "type": "integer",
                    "description": "Lines of context around each match (content mode only).",
                },
                "include": {
                    "type": "string",
                    "description": "Glob to restrict which files are searched, e.g. *.py",
                },
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "write_todos",
        "description": (
            "Replace the entire task list. "
            "Call at the start of any multi-step task and after each completed step. "
            "Statuses: pending | in_progress | completed."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "todos": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "content": {"type": "string"},
                            "status": {
                                "type": "string",
                                "enum": ["pending", "in_progress", "completed"],
                            },
                        },
                        "required": ["id", "content", "status"],
                    },
                }
            },
            "required": ["todos"],
        },
    },
    {
        "name": "read_skill",
        "description": (
            "Load the full instructions for a skill. "
            "Call this when the user's request matches a skill's activation description. "
            "The skill name must exactly match one listed in the Available Skills section."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "skill_name": {
                    "type": "string",
                    "description": "Exact skill name as listed in the system prompt",
                }
            },
            "required": ["skill_name"],
        },
    },
    {
        "name": "run_sql",
        "description": (
            "Execute a SQL query against the AdventureWorks PostgreSQL database. "
            "Use for any question that requires live data: counts, aggregations, filters, "
            "date ranges, JOINs, and also INSERT/UPDATE/DELETE writes. "
            "Returns rows as a formatted table for SELECT, or row count for DML. "
            "Results are truncated at 100 rows."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "SQL query to execute",
                },
                "params": {
                    "type": "array",
                    "items": {"type": ["string", "number", "boolean", "null"]},
                    "description": "Optional positional parameters (%s placeholders in query)",
                },
            },
            "required": ["query"],
        },
    },
]

# ---------------------------------------------------------------------------
# System prompt builder
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_TEMPLATE = """\
{memory}
## Filesystem Tools

- **ls** — list directory contents with file sizes
- **read_file** — read a file with line numbers; use offset + limit for large files
- **write_file** — create or overwrite a file
- **edit_file** — exact string replacement; fails if the string isn't found
- **glob** — find files by pattern (e.g. `**/*.py`, `src/**/*.ts`)
- **grep** — search file content by regex with three output modes:
  - `files_with_matches` (default) — just the file paths
  - `content` — matching lines with optional context
  - `count` — number of matches per file

## Planning

Use **write_todos** to track progress on any task with three or more steps.

Rules:
1. Write the plan before starting work.
2. Update statuses after each completed step (replace the full list every time).
3. Mark tasks `in_progress` while you work, `completed` when done.

## Skills

Skills provide specialized, step-by-step workflows for specific domains.
Only their descriptions are loaded at startup.
Call **read_skill** with the exact skill name when the task matches.

{skills_summary}

## Working Directory

`{cwd}`

## General Guidelines

- Plan first for multi-step tasks.
- Read a file before editing it.
- Use glob + grep to explore unfamiliar codebases.
- Load a skill when the user's request matches its activation description.
- Page through large files with offset/limit rather than reading everything at once.
"""


def _load_memory(memory_file: str | None) -> str:
    """Read AGENTS.md and return its content formatted for the system prompt."""
    if not memory_file:
        return ""
    path = Path(memory_file)
    if not path.exists():
        return ""
    content = path.read_text(errors="replace").strip()
    return content + "\n\n---\n\n"


def build_system_prompt(skills_summary: str, cwd: str, memory: str = "") -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(
        memory=memory,
        skills_summary=skills_summary,
        cwd=cwd,
    )


# ---------------------------------------------------------------------------
# Rich display helpers
# ---------------------------------------------------------------------------


def _flush() -> None:
    sys.stdout.flush()


def _print_thinking(content: str) -> None:
    """Print a thinking block as a dim panel."""
    if not content.strip():
        return
    _flush()
    _console.print(
        Panel(
            content,
            title="[dim]Reasoning[/dim]",
            border_style="dim",
            padding=(0, 1),
        )
    )


def _format_inputs(inputs: dict) -> str:
    """Format tool inputs as coloured key=value pairs."""
    parts: list[str] = []
    for k, v in inputs.items():
        if isinstance(v, str):
            short = v[:80] + ("…" if len(v) > 80 else "")
            parts.append(f"[dim]{k}=[/dim][green]\"{short}\"[/green]")
        elif isinstance(v, bool):
            parts.append(f"[dim]{k}=[/dim][cyan]{v}[/cyan]")
        elif isinstance(v, (int, float)):
            parts.append(f"[dim]{k}=[/dim][cyan]{v}[/cyan]")
        elif isinstance(v, list):
            parts.append(f"[dim]{k}=[/dim][yellow][{len(v)} items][/yellow]")
        else:
            parts.append(f"[dim]{k}=[/dim][yellow]…[/yellow]")
    return "  ".join(parts)


def _print_tool_call(name: str, inputs: dict) -> None:
    """Print a tool invocation header before executing."""
    _flush()
    if name == "read_skill":
        skill_name = inputs.get("skill_name", "?")
        _console.print(
            f"\n[bold cyan]◆ skill[/bold cyan]  [bold cyan]{skill_name}[/bold cyan]",
            end="",
        )
    elif name == "write_todos":
        _console.print(f"\n[bold blue]☑ todos[/bold blue]", end="")
    else:
        args = _format_inputs(inputs)
        _console.print(f"\n[bold yellow]⚙ {name}[/bold yellow]  {args}", end="")
    _flush()


def _print_tool_result(name: str, result: str) -> None:
    """Print the result of a tool call."""
    _flush()
    if name == "read_skill":
        kb = len(result) / 1024
        lines = result.count("\n") + 1
        _console.print(f"\n  [dim]→ {kb:.1f} KB loaded  ({lines} lines)[/dim]")
    elif name == "write_todos":
        # The executor already formats the todo list; skip the first header line
        body_lines = result.splitlines()
        _console.print()
        for line in body_lines[1:]:
            _console.print(f"  {line}")
    else:
        preview = result.replace("\n", " ")[:200]
        ellipsis = "…" if len(result) > 200 else ""
        _console.print(f"\n  [dim]→ {preview}{ellipsis}[/dim]")
    _flush()


def _bold(text: str) -> str:
    return f"[bold]{text}[/bold]"


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class Agent:
    """
    Streaming agentic loop over the Anthropic Messages API.

    The loop runs until Claude returns stop_reason == "end_turn".
    On each tool-use turn:
      1. Append the assistant turn (including thinking blocks) to messages.
      2. Execute every tool_use block via ToolExecutor.dispatch().
      3. Append a user turn with all tool_result blocks.
      4. Continue.
    """

    def __init__(
        self,
        skills_dir: str | None = None,
        cwd: str | None = None,
        memory_file: str | None = None,
        db_host: str = "localhost",
        db_port: int = 5433,
        db_name: str = "Adventureworks",
        db_user: str = "postgres",
        db_password: str = "postgres",
    ) -> None:
        self.client = anthropic.Anthropic()
        self.cwd = cwd or os.getcwd()
        self.skills_dir = skills_dir or str(Path(__file__).parent / "skills")

        # Default memory file: AGENTS.md next to agent.py
        if memory_file is None:
            default_agents_md = Path(__file__).parent / "AGENTS.md"
            memory_file = str(default_agents_md) if default_agents_md.exists() else None

        self.skills = SkillsRegistry(self.skills_dir)
        self.executor = ToolExecutor(
            cwd=self.cwd,
            skills=self.skills,
            db_host=db_host,
            db_port=db_port,
            db_name=db_name,
            db_user=db_user,
            db_password=db_password,
        )

        self.system_prompt = build_system_prompt(
            skills_summary=self.skills.frontmatter_summary(),
            cwd=self.cwd,
            memory=_load_memory(memory_file),
        )

    # ------------------------------------------------------------------
    # Core run loop (one task / conversation)
    # ------------------------------------------------------------------

    def run(self, user_input: str) -> None:
        """Run a single task to completion, streaming output to stdout."""
        messages: list[dict] = [{"role": "user", "content": user_input}]

        while True:
            response = self._stream_turn(messages)

            if response.stop_reason == "end_turn":
                sys.stdout.write("\n")
                sys.stdout.flush()
                break

            if response.stop_reason != "tool_use":
                # pause_turn or unexpected — end gracefully
                sys.stdout.write("\n")
                sys.stdout.flush()
                break

            # Append assistant turn (preserving thinking blocks for the API)
            messages.append({"role": "assistant", "content": response.content})

            # Execute tools and collect results
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue

                _print_tool_call(block.name, block.input)
                result = self.executor.dispatch(block.name, block.input)
                _print_tool_result(block.name, result)

                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    }
                )

            messages.append({"role": "user", "content": tool_results})

    # ------------------------------------------------------------------
    # Single streaming API call
    # ------------------------------------------------------------------

    def _stream_turn(self, messages: list[dict]):
        """Stream one API turn, printing text as it arrives. Returns the final message."""
        thinking_buf: list[str] = []
        current_block: str | None = None

        with self.client.messages.stream(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=self.system_prompt,
            tools=TOOL_SCHEMAS,
            thinking={"type": "adaptive"},
            messages=messages,
        ) as stream:
            for event in stream:
                if event.type == "content_block_start":
                    current_block = event.content_block.type
                    if current_block == "thinking":
                        thinking_buf = []

                elif event.type == "content_block_delta":
                    if event.delta.type == "thinking_delta":
                        thinking_buf.append(event.delta.thinking)
                    elif event.delta.type == "text_delta":
                        sys.stdout.write(event.delta.text)
                        sys.stdout.flush()

                elif event.type == "content_block_stop":
                    if current_block == "thinking":
                        _print_thinking("".join(thinking_buf))
                    current_block = None

            return stream.get_final_message()

    # ------------------------------------------------------------------
    # Interactive REPL
    # ------------------------------------------------------------------

    def chat(self) -> None:
        """Start an interactive multi-turn REPL."""
        skills_list = self.skills.names()
        skills_str = ", ".join(f"[cyan]{s}[/cyan]" for s in skills_list) if skills_list else "[dim]none[/dim]"

        _console.print(Rule("[bold]Adventure Works Agent[/bold]"))
        _console.print(f"  [dim]Working directory:[/dim] {self.cwd}")
        _console.print(f"  [dim]Model:[/dim]             {MODEL}")
        _console.print(f"  [dim]Skills:[/dim]            {skills_str}")
        _console.print(f"  [dim]Ctrl-C or Ctrl-D to exit[/dim]")
        _console.print(Rule())

        while True:
            try:
                user_input = _console.input("\n[bold]You>[/bold] ").strip()
            except (KeyboardInterrupt, EOFError):
                _console.print("\n[dim]Bye.[/dim]")
                break

            if not user_input:
                continue

            _console.print(Rule(style="dim"))
            try:
                self.run(user_input)
            except anthropic.APIError as e:
                _console.print(f"\n[bold red]API error:[/bold red] {e}")
            except KeyboardInterrupt:
                _console.print("\n[dim](interrupted)[/dim]")
            _console.print(Rule(style="dim"))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Anthropic SDK agent with progressive skills and filesystem tools"
    )
    parser.add_argument(
        "task",
        nargs="?",
        help="Task to run non-interactively. Omit for interactive REPL.",
    )
    parser.add_argument("--cwd", help="Working directory (default: current directory)")
    parser.add_argument(
        "--skills",
        help="Skills directory (default: ./skills next to agent.py)",
    )
    parser.add_argument(
        "--memory",
        help="AGENTS.md memory file (default: AGENTS.md next to agent.py)",
    )
    parser.add_argument("--db-host", default="localhost", help="DB host (default: localhost)")
    parser.add_argument("--db-port", type=int, default=5433, help="DB port (default: 5433)")
    parser.add_argument("--db-name", default="Adventureworks", help="DB name (default: Adventureworks)")
    parser.add_argument("--db-user", default="postgres", help="DB user (default: postgres)")
    parser.add_argument("--db-password", default="postgres", help="DB password (default: postgres)")
    args = parser.parse_args()

    agent = Agent(
        skills_dir=args.skills,
        cwd=args.cwd,
        memory_file=args.memory,
        db_host=args.db_host,
        db_port=args.db_port,
        db_name=args.db_name,
        db_user=args.db_user,
        db_password=args.db_password,
    )

    if args.task:
        agent.run(args.task)
    else:
        agent.chat()


if __name__ == "__main__":
    main()
