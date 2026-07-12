from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import yaml

from ia_local_prompt.optimizer import PromptMetadata
from ia_local_prompt.sequential import SequencePlan


@dataclass
class SequenceMetadata:
    generated_at: str
    slug: str
    profile: str
    step_count: int
    sequential: bool = True
    target_model: str = ""
    target_agent: str = ""
    skill: str = ""
    skills: list[str] = field(default_factory=list)
    task_type: str = ""
    complexity: str = ""
    urls: list[str] = field(default_factory=list)
    steps: list[dict[str, str | int]] = field(default_factory=list)
    enhanced: bool = False
    enhance_model: str | None = None
    enhance_latency_ms: int = 0
    steps_enhanced: int = 0
    enrich_error: str | None = None
    warnings: list[str] = field(default_factory=list)


def export_prompt(
    prompt: str,
    metadata: PromptMetadata,
    output: Path,
) -> tuple[Path, Path | None]:
    output.parent.mkdir(parents=True, exist_ok=True)
    prompt_path = output
    prompt_path.write_text(prompt, encoding="utf-8")

    meta_path = output.with_suffix(".meta.yaml")
    meta_dict = asdict(metadata)
    with open(meta_path, "w", encoding="utf-8") as f:
        yaml.dump(meta_dict, f, allow_unicode=True, default_flow_style=False)

    return prompt_path, meta_path


def export_sequence(
    plan: SequencePlan,
    index_content: str,
    metadata: SequenceMetadata,
    output_dir: Path,
) -> tuple[Path, list[Path], Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    index_path = output_dir / "00-INDEX.md"
    index_path.write_text(index_content, encoding="utf-8")

    step_paths: list[Path] = []
    for step in plan.steps:
        path = output_dir / step.filename
        path.write_text(step.prompt, encoding="utf-8")
        step_paths.append(path)

    meta_path = output_dir / "sequence.meta.yaml"
    with open(meta_path, "w", encoding="utf-8") as f:
        yaml.dump(asdict(metadata), f, allow_unicode=True, default_flow_style=False)

    return index_path, step_paths, meta_path


def build_sequence_metadata(
    plan: SequencePlan,
    selection_model: str,
    selection_skill: str,
    agent: str,
    task_type: str,
    complexity: str,
    urls: list[str],
    selection_skills: list[str] | None = None,
    warnings: list[str] | None = None,
    enhanced: bool = False,
    enhance_model: str | None = None,
    enhance_latency_ms: int = 0,
    steps_enhanced: int = 0,
    enrich_error: str | None = None,
) -> SequenceMetadata:
    return SequenceMetadata(
        generated_at=datetime.now(timezone.utc).isoformat(),
        slug=plan.slug,
        profile=plan.profile,
        step_count=len(plan.steps),
        target_model=selection_model,
        target_agent=agent,
        skill=selection_skill,
        skills=selection_skills or [selection_skill],
        task_type=task_type,
        complexity=complexity,
        urls=urls,
        steps=[
            {
                "order": s.order,
                "id": s.step_id,
                "title": s.title,
                "filename": s.filename,
            }
            for s in plan.steps
        ],
        enhanced=enhanced,
        enhance_model=enhance_model,
        enhance_latency_ms=enhance_latency_ms,
        steps_enhanced=steps_enhanced,
        enrich_error=enrich_error,
        warnings=warnings or [],
    )
