"""
Skills registry with progressive disclosure.

Pattern from Agent_Arq/Skills.md (Deep Agents harness):
  - At startup:  scan the skills/ directory, parse only the YAML frontmatter
                 from each SKILL.md so the agent knows *what* skills exist
                 without loading their full bodies into the context window.
  - On demand:   when the agent calls read_skill(skill_name), load and return
                 the full SKILL.md content so it can follow the instructions.

Each skill lives in its own sub-directory:
    skills/
        my-skill/
            SKILL.md          ← frontmatter + instructions
            (other assets)    ← templates, reference docs, etc.

SKILL.md frontmatter shape (YAML between --- delimiters):
    ---
    name: skill-name           # kebab-case, should match folder name
    description: >             # activation trigger — starts with "Use this skill when…"
      Use this skill when ...
    metadata:
      tools:
        - tool_name_1
        - tool_name_2
    ---
"""
from __future__ import annotations

from pathlib import Path

try:
    import yaml as _yaml
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False


# ---------------------------------------------------------------------------
# Frontmatter parser
# ---------------------------------------------------------------------------

def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Split YAML frontmatter from body.  Returns (meta_dict, body_str)."""
    if not text.startswith("---"):
        return {}, text

    # Find the closing ---
    close = text.find("\n---", 3)
    if close == -1:
        return {}, text

    raw_yaml = text[3:close].strip()
    body = text[close + 4:].strip()

    if _HAS_YAML:
        try:
            meta = _yaml.safe_load(raw_yaml) or {}
        except Exception:
            meta = _minimal_parse(raw_yaml)
    else:
        meta = _minimal_parse(raw_yaml)

    return meta, body


def _minimal_parse(raw: str) -> dict:
    """Fallback YAML parser that handles simple key: value lines only."""
    meta: dict = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, _, val = line.partition(":")
            val = val.strip().strip('"').strip("'")
            if val:
                meta[key.strip()] = val
    return meta


# ---------------------------------------------------------------------------
# SkillEntry — one skill directory
# ---------------------------------------------------------------------------

class SkillEntry:
    """Represents a single skill directory with a SKILL.md file."""

    def __init__(self, skill_dir: Path) -> None:
        self.dir = skill_dir
        self.skill_md = skill_dir / "SKILL.md"
        self.meta: dict = {}

        # Folder name is the default name; overridden by frontmatter `name`
        self.name: str = skill_dir.name

        if self.skill_md.exists():
            text = self.skill_md.read_text(errors="replace")
            self.meta, _ = _parse_frontmatter(text)
            if isinstance(self.meta.get("name"), str):
                self.name = self.meta["name"]

    @property
    def description(self) -> str:
        desc = self.meta.get("description", "")
        if isinstance(desc, str):
            # Collapse multi-line YAML block scalars into one paragraph
            return " ".join(desc.split())
        return "(no description)"

    @property
    def tools(self) -> list[str]:
        meta = self.meta.get("metadata") or {}
        t = meta.get("tools", []) if isinstance(meta, dict) else []
        return t if isinstance(t, list) else []

    def full_content(self) -> str:
        if not self.skill_md.exists():
            return f"Error: SKILL.md not found in {self.dir}"
        return self.skill_md.read_text(errors="replace")


# ---------------------------------------------------------------------------
# SkillsRegistry
# ---------------------------------------------------------------------------

class SkillsRegistry:
    """Loads skill frontmatter at startup; serves full content on demand."""

    def __init__(self, skills_dir: str) -> None:
        self._dir = Path(skills_dir)
        # Index by both `name` field and folder name for flexible lookup
        self._by_name: dict[str, SkillEntry] = {}
        self._scan()

    def _scan(self) -> None:
        if not self._dir.is_dir():
            return
        for child in sorted(self._dir.iterdir()):
            if child.is_dir() and (child / "SKILL.md").exists():
                entry = SkillEntry(child)
                self._by_name[entry.name] = entry
                # Also register by folder name in case they differ
                if child.name != entry.name:
                    self._by_name[child.name] = entry

    # ------------------------------------------------------------------
    # System-prompt integration
    # ------------------------------------------------------------------

    def frontmatter_summary(self) -> str:
        """Return the skills section injected into the system prompt.

        Only frontmatter (name + description + tool list) is included — no
        full instructions.  The agent calls read_skill to load those.
        """
        # Deduplicate (folder-name alias points to same SkillEntry)
        seen: set[int] = set()
        unique: list[SkillEntry] = []
        for entry in self._by_name.values():
            if id(entry) not in seen:
                seen.add(id(entry))
                unique.append(entry)

        if not unique:
            return "No skills available."

        lines: list[str] = ["### Available Skills\n"]
        for entry in unique:
            tools_str = (
                f"  *(tools: {', '.join(entry.tools)})*" if entry.tools else ""
            )
            lines.append(f"**`{entry.name}`**{tools_str}")
            lines.append(f"{entry.description}\n")

        lines.append(
            "Call `read_skill` with the exact skill name to load full instructions "
            "when a task matches one of the descriptions above."
        )
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # On-demand loader
    # ------------------------------------------------------------------

    def load(self, name: str) -> str:
        """Return the full SKILL.md content for the named skill."""
        entry = self._by_name.get(name)
        if not entry:
            available = sorted({e.name for e in self._by_name.values()})
            return (
                f"Error: skill '{name}' not found.\n"
                f"Available skills: {', '.join(available) or '(none)'}"
            )
        return entry.full_content()

    def names(self) -> list[str]:
        return sorted({e.name for e in self._by_name.values()})
