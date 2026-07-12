from __future__ import annotations

import io
import uuid
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import httpx

from ia_local_prompt.analyzer import analyze_objective
from ia_local_prompt.config_loader import (
    PROJECT_ROOT,
    get_models_registry,
    get_prompt_generator_config,
    get_server_endpoints,
)
from ia_local_prompt.exporters import (
    build_sequence_metadata,
    export_prompt,
    export_sequence,
)
from ia_local_prompt.llm_enricher import enrich_prompt, enrich_sequence_step
from ia_local_prompt.optimizer import build_metadata, optimize_prompt
from ia_local_prompt.sequential import (
    SequencePlan,
    build_sequence,
    render_sequence_index,
    select_sequence_profile,
    should_use_sequential,
)
from ia_local_prompt.skill_selector import (
    AVAILABLE_SKILLS,
    PERSISTENCE_SKILL,
    SKILL_HINTS,
    select_skill,
    should_auto_enhance,
)
from ia_local_prompt.template_engine import assemble_agent_message, render_prompt

WEBUI_OUTPUT_DIR = PROJECT_ROOT / "prompts" / "generated" / "webui"


@dataclass
class GenerateOptions:
    objective: str
    agent: str = "cline"
    model: str | None = None
    skill: str | None = None
    skills: list[str] | None = None
    context_limit: int = 32768
    enhance_mode: str = "off"
    enhance_model: str | None = None
    enhance_api_base: str | None = None
    output_mode: str = "auto"
    profile: str | None = None


def _resolve_do_enhance(enhance_mode: str, analysis) -> bool:
    if enhance_mode == "off":
        return False
    if enhance_mode == "on":
        return True
    if enhance_mode == "auto":
        return should_auto_enhance(analysis)
    return False


def _resolve_sequential(
    output_mode: str,
    analysis,
    sequential: bool = False,
    single: bool = False,
) -> bool:
    if output_mode == "single":
        return False
    if output_mode == "sequential":
        return True
    return should_use_sequential(analysis, sequential=False, single=False)


def get_ui_config() -> dict[str, Any]:
    registry = get_models_registry()
    endpoints = get_server_endpoints()
    pg = get_prompt_generator_config().get("prompt_generator", {})

    target_models = [
        {
            "id": m["id"],
            "roles": m.get("roles", []),
            "skill": m.get("skill"),
            "rank": m.get("rank"),
        }
        for m in registry.get("models", [])
        if m.get("roles") and m.get("rank") is not None
    ]

    enhance_models = [
        m["id"]
        for m in registry.get("models", [])
        if "meta_prompting" in m.get("roles", [])
        or "chat_only" in m.get("roles", [])
    ]
    default_enhance = pg.get("model", "qwen2.5-coder:14b")
    if default_enhance not in enhance_models:
        enhance_models.insert(0, default_enhance)

    host = endpoints.get("server", {}).get("host", "192.168.1.43")
    ollama_port = endpoints.get("server", {}).get("ollama_port", 11434)

    return {
        "target_models": target_models,
        "enhance_models": enhance_models,
        "default_enhance_model": default_enhance,
        "default_enhance_api_base": pg.get("api_base", f"http://{host}:{ollama_port}"),
        "servers": {
            "ollama": endpoints.get("endpoints", {}).get("ollama", f"http://{host}:{ollama_port}"),
            "vllm": endpoints.get("endpoints", {}).get("vllm", f"http://{host}:8000/v1"),
        },
        "skills": [
            {
                "id": skill_id,
                "hint": SKILL_HINTS.get(skill_id, ""),
                "always_on": skill_id == PERSISTENCE_SKILL,
            }
            for skill_id in AVAILABLE_SKILLS
        ],
        "agents": ["cline", "continue"],
        "profiles": ["full", "with_urls", "simple"],
        "enhance_modes": [
            {"id": "off", "label": "No", "hint": "Solo plantillas determinísticas"},
            {"id": "on", "label": "Sí", "hint": "El LLM mejora el texto (estructura fijada por código)"},
        ],
        "output_modes": [
            {"id": "sequential", "label": "Dividir en subtareas", "hint": "Recomendado con URLs o multi-agente"},
            {"id": "single", "label": "Prompt completo", "hint": "Un solo archivo"},
        ],
    }


def fetch_ollama_models(api_base: str) -> dict[str, Any]:
    """Lista modelos instalados vía GET {api_base}/v1/models (OpenAI-compatible)."""
    base = api_base.strip().rstrip("/")
    if not base:
        raise ValueError("URL del servidor Ollama vacía")

    url = f"{base}/v1/models"
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(url)
            resp.raise_for_status()
            payload = resp.json()
    except httpx.HTTPStatusError as e:
        raise ValueError(f"HTTP {e.response.status_code} al consultar {url}") from e
    except httpx.RequestError as e:
        raise ValueError(f"No se pudo conectar a {url}: {e}") from e

    models = [item["id"] for item in payload.get("data", []) if item.get("id")]
    if not models:
        raise ValueError(f"Sin modelos en la respuesta de {url}")

    return {"models": models, "source": url, "count": len(models)}


def run_analyze(objective: str) -> dict[str, Any]:
    analysis = analyze_objective(objective)
    selection = select_skill(analysis)
    profile = select_sequence_profile(analysis)
    seq_default = should_use_sequential(analysis, sequential=False, single=False)

    return {
        "task_type": analysis.task_type.value,
        "complexity": analysis.complexity.value,
        "word_count": analysis.word_count,
        "is_vague": analysis.is_vague,
        "is_multi_domain": analysis.is_multi_domain,
        "file_mentions": analysis.file_mentions,
        "urls": analysis.urls,
        "is_multi_agent": analysis.is_multi_agent,
        "llm_stack": analysis.llm_stack.value,
        "skill": selection.skill,
        "skills": selection.skills,
        "model": selection.model,
        "sequential": seq_default,
        "profile": profile,
        "auto_enhance": should_auto_enhance(analysis),
    }


def _enrich_sequence_plan(
    plan: SequencePlan,
    target_model: str,
    enhance_model: str | None,
    api_base: str | None,
) -> tuple[int, int, str | None, str | None]:
    total_latency = 0
    steps_enhanced = 0
    model_used: str | None = None
    first_error: str | None = None

    for step in plan.steps:
        result = enrich_sequence_step(
            draft=step.prompt,
            target_model=target_model,
            step_num=step.order,
            step_total=len(plan.steps),
            step_id=step.step_id,
            step_title=step.title,
            next_file=step.next_file,
            enhance_model=enhance_model,
            api_base_override=api_base,
        )
        total_latency += result.latency_ms
        if result.model_used:
            model_used = result.model_used
        if result.enhanced:
            step.prompt = result.prompt
            steps_enhanced += 1
        elif first_error is None:
            first_error = result.error

    return steps_enhanced, total_latency, model_used, first_error


@dataclass
class GenerateResult:
    mode: str
    session_id: str
    files: list[dict[str, str]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


def get_session_dir(session_id: str) -> Path | None:
    path = WEBUI_OUTPUT_DIR / session_id
    return path if path.exists() else None


def run_generate(options: GenerateOptions) -> GenerateResult:
    session_id = str(uuid.uuid4())[:8]
    analysis = analyze_objective(options.objective)
    selection = select_skill(
        analysis,
        model_override=options.model or None,
        skill_override=options.skill or None,
        skills_override=options.skills or None,
    )
    do_enhance = _resolve_do_enhance(options.enhance_mode, analysis)
    use_sequential = _resolve_sequential(options.output_mode, analysis)
    warnings: list[str] = []

    if use_sequential:
        plan = build_sequence(
            objective=options.objective,
            analysis=analysis,
            selection=selection,
            agent=options.agent,
            profile=options.profile,
        )

        steps_enhanced = 0
        enhance_latency = 0
        enhance_model_used = None
        enrich_error = None

        if do_enhance:
            steps_enhanced, enhance_latency, enhance_model_used, enrich_error = (
                _enrich_sequence_plan(
                    plan,
                    selection.model,
                    options.enhance_model,
                    options.enhance_api_base,
                )
            )

        index_content = render_sequence_index(
            plan, options.objective, selection, options.agent,
        )

        if selection.compact_prompt:
            warnings.append("Compact Prompt recomendado: ON")
        if options.agent == "cline":
            warnings.append("Cline: una tarea por sesión; copiar 00-INDEX.md primero")
            warnings.append("Cline: copiar .clinerules/skills/ al proyecto destino")
        if do_enhance:
            warnings.append(
                f"Enriquecido: {steps_enhanced}/{len(plan.steps)} tareas "
                f"({enhance_model_used or 'N/A'})"
            )
            if enrich_error and "truncad" in enrich_error.lower():
                warnings.append(
                    f"Enriquecimiento truncado en alguna tarea: se usó borrador original. "
                    f"({enrich_error})"
                )

        seq_meta = build_sequence_metadata(
            plan=plan,
            selection_model=selection.model,
            selection_skill=selection.skill,
            selection_skills=selection.skills,
            agent=options.agent,
            task_type=analysis.task_type.value,
            complexity=analysis.complexity.value,
            urls=analysis.urls,
            warnings=warnings,
            enhanced=steps_enhanced > 0,
            enhance_model=enhance_model_used,
            enhance_latency_ms=enhance_latency,
            steps_enhanced=steps_enhanced,
            enrich_error=enrich_error,
        )

        output_dir = WEBUI_OUTPUT_DIR / session_id / "sequence"
        export_sequence(plan, index_content, seq_meta, output_dir)

        files = []
        for step in plan.steps:
            path = output_dir / step.filename
            files.append({
                "name": step.filename,
                "path": str(path.relative_to(PROJECT_ROOT)),
                "content": path.read_text(encoding="utf-8"),
                "title": step.title,
            })
        index_path = output_dir / "00-INDEX.md"
        files.insert(0, {
            "name": "00-INDEX.md",
            "path": str(index_path.relative_to(PROJECT_ROOT)),
            "content": index_path.read_text(encoding="utf-8"),
            "title": "Índice de tareas",
        })

        return GenerateResult(
            mode="sequential",
            session_id=session_id,
            files=files,
            metadata={
                "profile": plan.profile,
                "step_count": len(plan.steps),
                "skill": selection.skill,
                "skills": selection.skills,
                "model": selection.model,
                "enhanced": steps_enhanced > 0,
                "steps_enhanced": steps_enhanced,
                "enhance_model": enhance_model_used,
                "enhance_api_base": options.enhance_api_base,
                "enrich_error": enrich_error,
                **{k: v for k, v in asdict(seq_meta).items() if k != "warnings"},
            },
            warnings=warnings,
        )

    draft = render_prompt(
        objective=options.objective,
        selection=selection,
        analysis=analysis,
        agent=options.agent,
        context_limit=options.context_limit,
    )
    draft = assemble_agent_message(draft, analysis, selection, agent=options.agent)

    enriched = False
    enhance_model_used = None
    enhance_latency = 0
    error = None
    final_prompt = draft

    if do_enhance:
        result = enrich_prompt(
            draft=draft,
            target_model=selection.model,
            enhance_model=options.enhance_model,
            api_base_override=options.enhance_api_base,
        )
        if result.enhanced:
            final_prompt = result.prompt
            enriched = True
        else:
            error = result.error
            if error and "truncad" in error.lower():
                warnings.append(
                    "Enriquecimiento truncado: se entrega el borrador completo sin LLM"
                )
        enhance_model_used = result.model_used
        enhance_latency = result.latency_ms

    final_prompt, opt_warnings = optimize_prompt(
        final_prompt, analysis, selection, options.agent,
    )
    warnings.extend(opt_warnings)

    metadata = build_metadata(
        prompt=final_prompt,
        analysis=analysis,
        selection=selection,
        agent=options.agent,
        enhanced=enriched,
        enhance_model=enhance_model_used,
        enhance_latency_ms=enhance_latency,
        error=error,
        warnings=warnings,
    )

    slug = analysis.task_type.value.replace("_", "-")
    output_path = WEBUI_OUTPUT_DIR / session_id / f"{slug}.md"
    export_prompt(final_prompt, metadata, output_path)

    meta_path = output_path.with_suffix(".meta.yaml")
    return GenerateResult(
        mode="single",
        session_id=session_id,
        files=[
            {
                "name": output_path.name,
                "path": str(output_path.relative_to(PROJECT_ROOT)),
                "content": final_prompt,
                "title": "Prompt generado",
            },
            {
                "name": meta_path.name,
                "path": str(meta_path.relative_to(PROJECT_ROOT)),
                "content": meta_path.read_text(encoding="utf-8"),
                "title": "Metadata",
            },
        ],
        metadata={
            "skill": selection.skill,
            "skills": selection.skills,
            "model": selection.model,
            "enhanced": enriched,
            "enhance_model": enhance_model_used,
            "enhance_api_base": options.enhance_api_base,
            "task_type": analysis.task_type.value,
            "complexity": analysis.complexity.value,
            "error": error,
        },
        warnings=warnings,
    )


def create_session_zip(session_id: str) -> bytes | None:
    session_dir = get_session_dir(session_id)
    if not session_dir:
        return None

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in session_dir.rglob("*"):
            if file_path.is_file():
                arcname = file_path.relative_to(session_dir)
                zf.write(file_path, arcname)
    buffer.seek(0)
    return buffer.getvalue()
