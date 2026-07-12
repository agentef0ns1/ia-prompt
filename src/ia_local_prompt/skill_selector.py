from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ia_local_prompt.analyzer import TaskAnalysis, TaskType
from ia_local_prompt.config_loader import get_models_registry

PERSISTENCE_SKILL = "local-agent-persistence"

AVAILABLE_SKILLS = [
    "local-coding-agent",
    "local-code-review",
    "local-repo-explore",
    "local-security-review",
    PERSISTENCE_SKILL,
]

SKILL_HINTS: dict[str, str] = {
    "local-coding-agent": "Crear, editar y refactorizar código",
    "local-code-review": "Revisar calidad, bugs y patrones",
    "local-repo-explore": "Explorar y entender repositorios",
    "local-security-review": "Auditoría de vulnerabilidades",
    PERSISTENCE_SKILL: "Anti-parada y persistencia (siempre recomendada)",
}


@dataclass
class SkillSelection:
    skills: list[str] = field(default_factory=lambda: ["local-coding-agent"])
    model: str = "qwen3-coder:30b"
    template: str = "coding-task"
    compact_prompt: bool = True
    preserve_reasoning: bool = False

    @property
    def skill(self) -> str:
        return self.skills[0] if self.skills else "local-coding-agent"


def format_skills_line(skills: list[str]) -> str:
    return " + ".join(f"`{s}`" for s in skills)


def resolve_skills(
    auto_skill: str,
    skill_override: str | None = None,
    skills_override: list[str] | None = None,
    *,
    include_persistence: bool = True,
) -> list[str]:
    if skills_override:
        skills = _dedupe([s.strip() for s in skills_override if s and s.strip()])
    elif skill_override:
        skills = [skill_override.strip()]
    else:
        skills = [auto_skill]

    valid = set(AVAILABLE_SKILLS)
    skills = [s for s in skills if s in valid]
    if not skills:
        skills = [auto_skill if auto_skill in valid else "local-coding-agent"]

    if include_persistence and PERSISTENCE_SKILL not in skills:
        skills.append(PERSISTENCE_SKILL)

    return skills


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def select_skill(
    analysis: TaskAnalysis,
    model_override: str | None = None,
    skill_override: str | None = None,
    skills_override: list[str] | None = None,
) -> SkillSelection:
    registry = get_models_registry()
    defaults = registry.get("task_type_defaults", {})
    task_key = analysis.task_type.value
    task_defaults = defaults.get(task_key, defaults.get("coding", {}))

    auto_skill = task_defaults.get("skill", "local-coding-agent")
    model = model_override or task_defaults.get("model", "qwen3-coder:30b")
    template = task_defaults.get("template", "coding-task")

    model_info = _find_model(registry, model)
    compact_prompt = model_info.get("compact_prompt", True) if model_info else True
    preserve_reasoning = model_info.get("preserve_reasoning", False) if model_info else False

    if (
        skill_override is None
        and skills_override is None
        and model_info
        and model_info.get("skill")
        and analysis.task_type == TaskType.SECURITY_REVIEW
    ):
        auto_skill = model_info["skill"]

    skills = resolve_skills(
        auto_skill,
        skill_override=skill_override,
        skills_override=skills_override,
    )

    return SkillSelection(
        skills=skills,
        model=model,
        template=template,
        compact_prompt=compact_prompt,
        preserve_reasoning=preserve_reasoning,
    )


def _find_model(registry: dict[str, Any], model_id: str) -> dict[str, Any] | None:
    for m in registry.get("models", []):
        if m.get("id") == model_id:
            return m
    return None


def should_auto_enhance(analysis: TaskAnalysis, threshold: str = "complex") -> bool:
    if threshold == "always":
        return True
    if threshold == "none":
        return False
    return (
        analysis.is_vague
        or analysis.is_multi_domain
        or analysis.complexity.value == "high"
        or len(analysis.file_mentions) > 3
        or analysis.is_multi_agent
        or len(analysis.urls) >= 1
    )
