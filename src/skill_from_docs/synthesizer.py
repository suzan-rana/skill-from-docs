from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass

from openai import OpenAI
from pydantic import BaseModel, Field
from rich.console import Console

from .extractor import ExtractedPage

console = Console()

DEFAULT_MODEL = "anthropic/claude-sonnet-4.5"
DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
MAX_CORPUS_CHARS = 600_000  # ~150k tokens


class SkillFile(BaseModel):
    path: str = Field(description="Relative path inside skill folder, e.g. 'SKILL.md' or 'references/api.md'")
    purpose: str = Field(description="Why this file exists; what it covers")


class SkillPlan(BaseModel):
    name: str
    description: str
    files: list[SkillFile]
    allowed_tools: list[str] = Field(default_factory=list)


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

    def _system_messages(self) -> list[dict]:
        system_text = (
            "You build Claude Code skills from technical documentation. "
            "A skill is a folder with SKILL.md (frontmatter + concise procedural guide), "
            "references/*.md (lookup tables, API specs), and templates/*.py (runnable scaffolds). "
            "Skills must be terse, actionable, and optimized for an LLM agent reading them just-in-time."
        )
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
        messages = self._system_messages() + [{"role": "user", "content": user}]
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content or ""

    def plan(self) -> SkillPlan:
        user = (
            f"Design a Claude Code skill for `{self._library_name}` from the corpus above. "
            "Output a JSON object with this exact shape:\n"
            "{\n"
            '  "name": "kebab-case-skill-name",\n'
            '  "description": "One paragraph describing when an LLM should invoke this skill. '
            "Use this skill when: (1) ..., (2) ..., etc. Mention concrete trigger phrases.\",\n"
            '  "allowed_tools": ["Bash(python*)", "Bash(uv*)", ...],\n'
            '  "files": [\n'
            '    {"path": "SKILL.md", "purpose": "..."},\n'
            '    {"path": "references/api-quick-ref.md", "purpose": "..."},\n'
            '    {"path": "templates/basic.py", "purpose": "..."}\n'
            "  ]\n"
            "}\n\n"
            "Rules: 1 SKILL.md, 2-5 reference files, 1-4 templates. Choose files the LLM will need at runtime. "
            "Wrap the JSON in a ```json fence. No prose outside the fence."
        )
        raw = self._chat(user, max_tokens=4000)
        data = json.loads(_extract_json(raw))
        return SkillPlan(**data)

    def generate_file(self, plan: SkillPlan, target: SkillFile) -> GeneratedFile:
        is_skill_md = target.path == "SKILL.md"
        is_template = target.path.startswith("templates/")

        if is_skill_md:
            instr = (
                f"Write SKILL.md for the `{plan.name}` skill.\n\n"
                "Format:\n"
                "1. YAML frontmatter with `name`, `description` (use this verbatim: "
                f"{json.dumps(plan.description)}), and `allowed-tools` "
                f"({', '.join(plan.allowed_tools) or 'omit if none'}).\n"
                "2. A concise procedural body: setup check, decision tree for which "
                "API/function to use, execution workflow, and an index of references/ and templates/ "
                "(list every file from the plan with a one-line 'When to read' column).\n\n"
                "Plan files to reference in the indexes:\n"
                + "\n".join(f"- {f.path}: {f.purpose}" for f in plan.files)
                + "\n\nReturn ONLY the markdown for SKILL.md. No outer fence."
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
