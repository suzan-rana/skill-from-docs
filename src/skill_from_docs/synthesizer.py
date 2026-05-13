from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass

from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field, model_validator
from rich.console import Console

from .extractor import ExtractedPage

console = Console()

DEFAULT_MODEL = "anthropic/claude-sonnet-4.5"
DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
MAX_CORPUS_CHARS = 200_000  # ~50k tokens — keeps TTFT low on non-cached models


class SkillFile(BaseModel):
    model_config = ConfigDict(extra="ignore")

    path: str = Field(description="Relative path inside skill folder, e.g. 'SKILL.md' or 'references/api.md'")
    purpose: str = Field(default="", description="Why this file exists; what it covers")

    @model_validator(mode="before")
    @classmethod
    def _coerce_purpose(cls, data):
        if not isinstance(data, dict):
            return data
        if "purpose" not in data:
            for alt in ("description", "summary", "desc", "details", "content"):
                if alt in data and isinstance(data[alt], str):
                    data["purpose"] = data[alt]
                    break
        return data


class SkillPlan(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    description: str
    when_to_use: str = ""
    files: list[SkillFile]
    allowed_tools: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _coerce_aliases(cls, data):
        if not isinstance(data, dict):
            return data
        if "allowed_tools" not in data and "allowed-tools" in data:
            data["allowed_tools"] = data["allowed-tools"]
        return data


@dataclass
class GeneratedFile:
    path: str
    content: str


def _build_corpus(pages: list[ExtractedPage]) -> str:
    pages_sorted = sorted(pages, key=lambda p: p.word_count, reverse=True)
    chunks: list[str] = []
    used = 0
    for p in pages_sorted:
        block = f"\n\n===== PAGE: {p.url} =====\nTitle: {p.title}\n\n{p.markdown}\n"
        if used + len(block) > MAX_CORPUS_CHARS:
            remaining = MAX_CORPUS_CHARS - used
            if remaining > 2000:
                chunks.append(block[:remaining])
            break
        chunks.append(block)
        used += len(block)
    return "".join(chunks)


def _extract_json(text: str) -> str:
    m = re.search(r"```json\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    if m:
        return m.group(1)
    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not m:
        raise ValueError("No JSON object found in model output")
    return m.group(0)


def _extract_markdown(text: str) -> str:
    m = re.search(r"```(?:markdown|md)?\s*\n(.*?)```\s*$", text, flags=re.DOTALL)
    if m:
        return m.group(1).strip()
    return text.strip()


class Synthesizer:
    """OpenRouter-backed synthesizer.

    Uses the OpenAI-compatible chat completions API. For Anthropic models,
    OpenRouter passes through `cache_control` blocks for prompt caching.
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        key = api_key or os.environ.get("OPENROUTER_API_KEY")
        if not key:
            raise RuntimeError("OPENROUTER_API_KEY not set")
        self.client = OpenAI(
            api_key=key,
            base_url=base_url or os.environ.get("OPENROUTER_BASE_URL", DEFAULT_BASE_URL),
            default_headers={
                "HTTP-Referer": os.environ.get("OPENROUTER_REFERRER", "https://github.com/skill-from-docs"),
                "X-Title": os.environ.get("OPENROUTER_APP_TITLE", "skill-from-docs"),
            },
        )
        self.model = model
        self._corpus: str = ""
        self._library_name: str = ""

    def load(self, pages: list[ExtractedPage], library_name: str) -> None:
        self._corpus = _build_corpus(pages)
        self._library_name = library_name
        console.log(f"corpus packed: {len(self._corpus):,} chars across {len(pages)} pages")

    def _is_anthropic_model(self) -> bool:
        return self.model.lower().startswith("anthropic/")

    _SKILL_SPEC = """\
You build Claude Code skills from technical documentation, following the Agent Skills open standard.

CANONICAL SKILL STRUCTURE
- Folder: <skill-name>/ containing SKILL.md (required) + optional supporting files.
- Supporting files use any path; common conventions: `references/*.md`, `templates/*.py`, `scripts/*.sh`.

SKILL.md FORMAT
1. YAML frontmatter between `---` markers. All fields optional; `description` is recommended.
2. Concise markdown body with procedural instructions.

FRONTMATTER FIELDS
- `name`: lowercase letters, numbers, hyphens only. Max 64 chars. Defaults to directory name.
- `description`: third-person, says WHAT the skill does AND WHEN to use it. Put the key use case FIRST.
  Combined with `when_to_use` it is truncated at 1,536 chars in the skill listing.
  Include concrete trigger phrases the user would say (e.g. "scrape this page", "build a DEX").
- `when_to_use`: extra trigger phrases / example requests; appended to description.
- `allowed-tools`: space-separated string of tools auto-approved while skill is active.
  Examples: `Bash(python*) Bash(uv*) Read Grep WebFetch`.

SKILL.md BODY RULES (CRITICAL)
- Keep under 500 lines. Move detailed reference material to separate files.
- Once invoked, SKILL.md content stays in context for the whole session — every line is a recurring token cost.
- State WHAT to do, not WHY. Write standing instructions, not one-time steps.
- Reference supporting files inline so Claude knows what they contain AND when to load them.
  Pattern: `For complete API details, see [references/api.md](references/api.md).`
- Use `${CLAUDE_SKILL_DIR}` when referencing bundled scripts in bash commands.
- Prefer decision trees, tables, and bullet lists over prose.

SUPPORTING FILES
- Reference docs: terse, lookup-oriented; tables of API signatures, parameters, error codes.
- Templates: runnable scaffolds with `{{PLACEHOLDER}}` markers and a `if __name__ == "__main__":` block.
- Scripts: executed (via Bash), not loaded as context.
"""

    def _system_messages(self) -> list[dict]:
        system_text = self._SKILL_SPEC
        corpus_text = f"=== DOCUMENTATION CORPUS for {self._library_name} ===\n{self._corpus}"

        if self._is_anthropic_model():
            return [
                {"role": "system", "content": [{"type": "text", "text": system_text}]},
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "text",
                            "text": corpus_text,
                            "cache_control": {"type": "ephemeral"},
                        }
                    ],
                },
            ]
        return [
            {"role": "system", "content": system_text},
            {"role": "system", "content": corpus_text},
        ]

    def _chat(self, user: str, max_tokens: int) -> str:
        import time
        messages = self._system_messages() + [{"role": "user", "content": user}]
        approx_in_tokens = (sum(len(str(m.get("content", ""))) for m in messages)) // 4
        console.log(
            f"  → sending request: model={self.model}, ~{approx_in_tokens:,} input tokens, max_out={max_tokens}"
        )
        t0 = time.monotonic()
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            stream=True,
            timeout=600,
        )
        chunks: list[str] = []
        first = True
        ttft = None
        with console.status("[cyan]waiting for first token...[/cyan]", spinner="dots") as status:
            for ev in stream:
                try:
                    delta = ev.choices[0].delta.content or ""
                except (AttributeError, IndexError):
                    delta = ""
                if not delta:
                    continue
                if first:
                    ttft = time.monotonic() - t0
                    status.update(f"[cyan]streaming... (TTFT {ttft:.1f}s)[/cyan]")
                    first = False
                chunks.append(delta)
        out = "".join(chunks)
        dt = time.monotonic() - t0
        console.log(
            f"  → done: {len(out):,} chars, {dt:.1f}s total"
            + (f", TTFT {ttft:.1f}s" if ttft else ", no tokens received")
        )
        if not out:
            raise RuntimeError(
                "Empty response from model. Possible causes: context too large, model unavailable, "
                "OpenRouter rate limit. Try a smaller --max-pages or different --model."
            )
        return out

    def plan(self) -> SkillPlan:
        user = (
            f"Design a Claude Code skill for `{self._library_name}` from the corpus above, following the spec above.\n\n"
            "Output a JSON object with this exact shape:\n"
            "{\n"
            '  "name": "<kebab-case, lowercase + hyphens, max 64 chars>",\n'
            '  "description": "<3rd-person, key use case FIRST, then trigger phrases. '
            "Example shape: \\\"Use <X> for <primary purpose>. Triggers: '<phrase 1>', '<phrase 2>'. \"\n"
            "  \"Covers: <capability A>, <capability B>.\\\". Combined with when_to_use must stay under 1,536 chars.\",\n"
            '  "when_to_use": "<optional extra trigger phrases / example requests>",\n'
            '  "allowed_tools": ["Bash(python*)", "Bash(uv*)", "Read", "WebFetch"],\n'
            '  "files": [\n'
            '    {"path": "SKILL.md", "purpose": "<what this entrypoint covers>"},\n'
            '    {"path": "references/<topic>.md", "purpose": "<lookup material, e.g. API signatures>"},\n'
            '    {"path": "templates/<scenario>.py", "purpose": "<runnable scaffold>"}\n'
            "  ]\n"
            "}\n\n"
            "Constraints:\n"
            "- Exactly 1 SKILL.md (must be first entry).\n"
            "- 2-5 reference files under `references/` — each covers ONE topic Claude would look up just-in-time.\n"
            "- 1-4 templates under `templates/` — one per common scenario in the docs.\n"
            "- Pick files Claude will actually need at runtime, not exhaustive docs.\n"
            "- `allowed_tools` must use real Claude Code tool syntax (Bash(cmd*), Read, Grep, WebFetch, etc.).\n\n"
            "Wrap the JSON in a ```json fence. No prose outside the fence."
        )
        raw = self._chat(user, max_tokens=4000)
        data = json.loads(_extract_json(raw))
        return SkillPlan(**data)

    def generate_file(self, plan: SkillPlan, target: SkillFile) -> GeneratedFile:
        is_skill_md = target.path == "SKILL.md"
        is_template = target.path.startswith("templates/")

        if is_skill_md:
            tools_str = " ".join(plan.allowed_tools) if plan.allowed_tools else ""
            instr = (
                f"Write SKILL.md for the `{plan.name}` skill, following the SKILL.md FORMAT and BODY RULES above.\n\n"
                "YAML frontmatter MUST include these fields verbatim:\n"
                f"  name: {plan.name}\n"
                f"  description: {json.dumps(plan.description)}\n"
                + (f"  when_to_use: {json.dumps(plan.when_to_use)}\n" if plan.when_to_use else "")
                + (f"  allowed-tools: {tools_str}\n" if tools_str else "")
                + "\nBody requirements:\n"
                "- Start with a 1-2 sentence statement of what the skill does.\n"
                "- Setup/precondition check (e.g. version check, dependency install) as the first action.\n"
                "- Decision tree (ASCII or bullet branch) for picking the right API/function for a user's task.\n"
                "- Execution workflow: numbered steps that reference templates + references inline.\n"
                "- Reference index: table listing every reference file with a 'When to read' column.\n"
                "- Template index: table listing every template with a 'When to use' column.\n"
                "- Stay under 500 lines. Terse — tables, bullets, code fences, no marketing prose.\n\n"
                "Files in this skill (link to these from the indexes — use relative paths):\n"
                + "\n".join(f"- {f.path}: {f.purpose}" for f in plan.files)
                + "\n\nReturn ONLY the SKILL.md content (frontmatter + body). No outer code fence."
            )
        elif is_template:
            instr = (
                f"Write the file `{target.path}`.\n"
                f"Purpose: {target.purpose}\n\n"
                "Runnable Python template. Include:\n"
                "- Top docstring describing what it does and how to fill placeholders.\n"
                "- Imports from the actual library based on the corpus.\n"
                "- Placeholders like {{URL}}, {{SELECTOR}} where the user customizes.\n"
                "- A `if __name__ == \"__main__\":` block.\n"
                "Return ONLY the Python code, optionally wrapped in ```python fence."
            )
        else:
            instr = (
                f"Write the reference file `{target.path}`.\n"
                f"Purpose: {target.purpose}\n\n"
                "Terse, lookup-oriented: tables, bullet lists, code snippets. "
                "Cite concrete API names, parameters, and patterns from the corpus. "
                "No marketing language. Return ONLY the markdown content."
            )

        raw = self._chat(instr, max_tokens=8000)

        if is_template:
            content = _extract_markdown(raw)
            content = re.sub(r"^```python\s*\n", "", content)
            content = re.sub(r"\n```\s*$", "", content)
        elif is_skill_md:
            content = raw.strip()
            content = re.sub(r"^```(?:markdown|md)?\s*\n", "", content)
            content = re.sub(r"\n```\s*$", "", content)
        else:
            content = _extract_markdown(raw)

        return GeneratedFile(path=target.path, content=content)
