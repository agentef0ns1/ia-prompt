from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ia_local_prompt.analyzer import Complexity, TaskAnalysis
from ia_local_prompt.config_loader import (
    PROMPTS_DIR,
    get_prompt_generator_config,
    get_server_endpoints,
)
from ia_local_prompt.skill_selector import SkillSelection, format_skills_line
from ia_local_prompt.stack_builder import _secondary_model, _stack_fragment_name
from ia_local_prompt.template_engine import _load_fragment, _research_fetch_limit


@dataclass
class SequenceStep:
    order: int
    step_id: str
    title: str
    filename: str
    next_file: str
    prompt: str
    template_name: str


@dataclass
class SequencePlan:
    slug: str
    title: str
    profile: str
    steps: list[SequenceStep] = field(default_factory=list)


_STEP_PROFILES: dict[str, list[tuple[str, str, str]]] = {
    # (step_id, template_file, title)
    "full": [
        ("research", "01-research.md", "Investigación y plan"),
        ("scaffold", "02-scaffold.md", "Scaffold y dependencias"),
        ("implement", "03-implement.md", "Implementación principal"),
        ("verify", "04-verify.md", "Demo y pruebas"),
        ("finalize", "05-finalize.md", "Documentación y cierre"),
    ],
    "with_urls": [
        ("research", "01-research.md", "Investigación y plan"),
        ("implement", "02-implement-simple.md", "Implementación"),
        ("verify", "03-verify-simple.md", "Verificación y cierre"),
    ],
    "simple": [
        ("implement", "02-implement-simple.md", "Implementación"),
        ("verify", "03-verify-simple.md", "Verificación y cierre"),
    ],
}


def _sequences_env() -> Environment:
    return Environment(
        loader=FileSystemLoader([str(PROMPTS_DIR / "sequences")]),
        autoescape=select_autoescape([]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def _render_stack_text(
    env: Environment,
    analysis: TaskAnalysis,
    selection: SkillSelection,
) -> str:
    fragment = _stack_fragment_name(analysis)
    if not fragment:
        return ""
    endpoints = get_server_endpoints().get("endpoints", {})
    return _load_fragment(
        env,
        fragment,
        ollama_endpoint=endpoints.get("ollama", "http://SERVER_IP:11434"),
        vllm_endpoint=endpoints.get("vllm", "http://SERVER_IP:8000/v1"),
        primary_model=selection.model,
        secondary_model=_secondary_model(selection),
    )


def select_sequence_profile(analysis: TaskAnalysis) -> str:
    if analysis.is_multi_agent or (
        analysis.urls and analysis.complexity == Complexity.HIGH
    ):
        return "full"
    if analysis.urls:
        return "with_urls"
    if analysis.complexity == Complexity.HIGH or analysis.is_multi_domain:
        return "with_urls"
    return "simple"


def should_use_sequential(
    analysis: TaskAnalysis,
    sequential: bool,
    single: bool,
) -> bool:
    if single:
        return False
    if sequential:
        return True
    pg = get_prompt_generator_config().get("agent_message", {})
    return bool(pg.get("sequential_default", True))


def build_sequence(
    objective: str,
    analysis: TaskAnalysis,
    selection: SkillSelection,
    agent: str = "cline",
    profile: str | None = None,
) -> SequencePlan:
    profile = profile or select_sequence_profile(analysis)
    step_defs = _STEP_PROFILES.get(profile, _STEP_PROFILES["simple"])
    slug = analysis.task_type.value.replace("_", "-")
    seq_env = _sequences_env()
    tmpl_env = _create_template_env()
    fetch_limit = _research_fetch_limit()
    stack = _render_stack_text(tmpl_env, analysis, selection)
    web_fetch = ""
    if agent == "cline" and analysis.urls:
        web_fetch = _load_fragment(tmpl_env, "web-fetch-cline.md")
    tool_format = _load_fragment(tmpl_env, "tool-format.md", agent=agent)

    steps: list[SequenceStep] = []
    total = len(step_defs)

    for i, (step_id, template_file, title) in enumerate(step_defs, start=1):
        if i < total:
            next_id = step_defs[i][0]
            next_file = f"{i + 1:02d}-{next_id}.md"
        else:
            next_file = "(última tarea — fin de secuencia)"

        ctx = {
            "step_num": i,
            "step_total": total,
            "step_id": step_id,
            "title": title,
            "next_file": next_file,
            "objective": objective,
            "skill": selection.skill,
            "skills": selection.skills,
            "skills_line": format_skills_line(selection.skills),
            "model": selection.model,
            "agent": agent,
            "urls": analysis.urls,
            "stack": stack,
            "is_multi_agent": analysis.is_multi_agent,
            "primary_model": selection.model,
            "secondary_model": _secondary_model(selection),
            "research_fetch_limit": fetch_limit,
            "web_fetch": web_fetch,
            "tool_format": tool_format,
        }
        template = seq_env.get_template(template_file)
        prompt = template.render(**ctx).strip()
        skill_ref = _load_fragment(
            tmpl_env, "skill-reference.md", skills=selection.skills,
        )
        if skill_ref:
            prompt = f"{prompt}\n\n{skill_ref}"
        filename = f"{i:02d}-{step_id}.md"
        steps.append(SequenceStep(
            order=i,
            step_id=step_id,
            title=title,
            filename=filename,
            next_file=next_file,
            prompt=prompt,
            template_name=template_file,
        ))

    title = f"{slug} ({profile})"
    return SequencePlan(slug=slug, title=title, profile=profile, steps=steps)


def render_sequence_index(
    plan: SequencePlan,
    objective: str,
    selection: SkillSelection,
    agent: str,
) -> str:
    env = _sequences_env()
    template = env.get_template("00-index.md")
    return template.render(
        title=plan.title,
        objective=objective,
        skill=selection.skill,
        skills=selection.skills,
        skills_line=format_skills_line(selection.skills),
        model=selection.model,
        agent=agent,
        steps=plan.steps,
    ).strip()


def _create_template_env() -> Environment:
    from ia_local_prompt.template_engine import _create_env
    return _create_env()
