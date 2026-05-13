from __future__ import annotations

from pathlib import Path

from .synthesizer import GeneratedFile, SkillPlan


def write_skill(out_root: Path, plan: SkillPlan, files: list[GeneratedFile]) -> Path:
    skill_dir = out_root / plan.name
    skill_dir.mkdir(parents=True, exist_ok=True)

    for f in files:
        target = skill_dir / f.path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f.content, encoding="utf-8")

    return skill_dir
