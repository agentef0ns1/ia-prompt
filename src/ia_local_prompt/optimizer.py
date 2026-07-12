from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from ia_local_prompt.analyzer import TaskAnalysis
from ia_local_prompt.skill_selector import SkillSelection


@dataclass
class PromptMetadata:
    generated_at: str
    enhanced: bool
    enhance_model: str | None
    enhance_latency_ms: int
    target_model: str
    target_agent: str
    skill: str
    task_type: str
    complexity: str
    fallback_used: bool
    estimated_tokens: int
    validation_passed: bool
    skills: list[str] = field(default_factory=list)
    error: str | None = None
    warnings: list[str] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)
    is_multi_agent: bool = False
    llm_stack: str = "ollama_only"


def optimize_prompt(
    prompt: str,
    analysis: TaskAnalysis,
    selection: SkillSelection,
    agent: str,
) -> tuple[str, list[str]]:
    warnings: list[str] = []

    if selection.model == "bugtrace-ultra:latest":
        if "no declares" not in prompt.lower():
            prompt += (
                "\n\n## ADVERTENCIA MODELO\n"
                "bugtrace-ultra tiende a parar prematuramente. "
                "Continúa hasta completar TODOS los criterios de éxito."
            )
        warnings.append("Modelo bugtrace-ultra: reglas anti-parada añadidas")

    if selection.preserve_reasoning:
        prompt += (
            "\n\n## Reasoning\n"
            "Preserva el contenido de reasoning entre tool calls en el historial."
        )
        warnings.append("laguna-xs: preservar reasoning activado")

    if selection.compact_prompt:
        warnings.append("Compact Prompt recomendado: ON")

    if analysis.is_vague:
        warnings.append("Objetivo vago detectado: considera usar --enhance")

    if len(analysis.file_mentions) > 3:
        prompt += (
            "\n\n## Tarea multi-archivo\n"
            "Trabaja un archivo a la vez. Verifica cada cambio antes de continuar."
        )

    if analysis.urls and agent == "cline":
        warnings.append("Cline: mensaje incluye @url listo para pegar")

    if analysis.urls or analysis.is_multi_agent:
        warnings.append("Fases 1→2 activas: máx 3 lecturas web, luego escribir en disco")

    if analysis.is_multi_agent:
        warnings.append("Tarea multi-agente: bloque Stack y plan A2A incluidos")

    if agent == "cline":
        warnings.append("Cline: formato XML para tools")

    return prompt, warnings


def build_metadata(
    prompt: str,
    analysis: TaskAnalysis,
    selection: SkillSelection,
    agent: str,
    enhanced: bool = False,
    enhance_model: str | None = None,
    enhance_latency_ms: int = 0,
    fallback_used: bool = False,
    validation_passed: bool = True,
    error: str | None = None,
    warnings: list[str] | None = None,
) -> PromptMetadata:
    return PromptMetadata(
        generated_at=datetime.now(timezone.utc).isoformat(),
        enhanced=enhanced,
        enhance_model=enhance_model,
        enhance_latency_ms=enhance_latency_ms,
        target_model=selection.model,
        target_agent=agent,
        skill=selection.skill,
        skills=list(selection.skills),
        task_type=analysis.task_type.value,
        complexity=analysis.complexity.value,
        fallback_used=fallback_used,
        estimated_tokens=len(prompt.split()) * 2,
        validation_passed=validation_passed,
        error=error,
        warnings=warnings or [],
        urls=analysis.urls,
        is_multi_agent=analysis.is_multi_agent,
        llm_stack=analysis.llm_stack.value,
    )
