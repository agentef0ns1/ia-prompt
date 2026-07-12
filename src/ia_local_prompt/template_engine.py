from __future__ import annotations

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ia_local_prompt.analyzer import TaskAnalysis, analyze_objective
from ia_local_prompt.config_loader import (
    PROMPTS_DIR,
    get_prompt_generator_config,
    get_server_endpoints,
)
from ia_local_prompt.skill_selector import SkillSelection, format_skills_line
from ia_local_prompt.stack_builder import _secondary_model, _stack_fragment_name


def _research_fetch_limit() -> int:
    pg = get_prompt_generator_config().get("agent_message", {})
    return int(pg.get("research_fetch_limit", 3))


def _create_env() -> Environment:
    return Environment(
        loader=FileSystemLoader([
            str(PROMPTS_DIR / "templates"),
            str(PROMPTS_DIR / "fragments"),
        ]),
        autoescape=select_autoescape([]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def _load_fragment(env: Environment, name: str, **ctx: object) -> str:
    try:
        template = env.get_template(name)
        return template.render(**ctx).strip()
    except Exception:
        path = PROMPTS_DIR / "fragments" / name
        if path.exists():
            return path.read_text(encoding="utf-8").strip()
        return ""


def _render_stack(
    env: Environment,
    analysis: TaskAnalysis,
    selection: SkillSelection,
) -> str:
    fragment = _stack_fragment_name(analysis)
    if not fragment:
        return ""

    endpoints = get_server_endpoints().get("endpoints", {})
    secondary = _secondary_model(selection)
    return _load_fragment(
        env,
        fragment,
        ollama_endpoint=endpoints.get("ollama", "http://SERVER_IP:11434"),
        vllm_endpoint=endpoints.get("vllm", "http://SERVER_IP:8000/v1"),
        primary_model=selection.model,
        secondary_model=secondary,
    )


def render_prompt(
    objective: str,
    selection: SkillSelection,
    analysis: TaskAnalysis | None = None,
    agent: str = "cline",
    context_limit: int = 32768,
) -> str:
    env = _create_env()
    template_name = f"{selection.template}.md"
    analysis = analysis or analyze_objective(objective)
    fetch_limit = _research_fetch_limit()

    tool_format = _load_fragment(env, "tool-format.md", agent=agent)
    persistence = _load_fragment(env, "persistence.md")
    web_fetch = ""
    phase_gate = ""
    if agent == "cline" and (analysis.urls or analysis.is_multi_agent):
        phase_gate = _load_fragment(
            env, "phase-gate.md", research_fetch_limit=fetch_limit,
        )
    if agent == "cline" and analysis.urls:
        web_fetch = _load_fragment(env, "web-fetch-cline.md")
    scope = _load_fragment(
        env, "scope.md",
        file_count=len(objective.split()),
    )

    execution_plan = ""
    if analysis.is_multi_agent:
        endpoints = get_server_endpoints().get("endpoints", {})
        execution_plan = _load_fragment(
            env,
            "plan-multi-agent.md",
            ollama_endpoint=endpoints.get("ollama", "http://SERVER_IP:11434"),
            primary_model=selection.model,
            secondary_model=_secondary_model(selection),
            research_fetch_limit=fetch_limit,
        )

    template = env.get_template(template_name)
    skills_line = format_skills_line(selection.skills)
    prompt = template.render(
        objective=objective,
        skill=selection.skill,
        skills=selection.skills,
        skills_line=skills_line,
        model=selection.model,
        agent=agent,
        context_limit=context_limit,
        compact_prompt=selection.compact_prompt,
        preserve_reasoning=selection.preserve_reasoning,
        tool_format=tool_format,
        persistence=persistence,
        web_fetch=web_fetch,
        phase_gate=phase_gate,
        scope=scope,
        urls=analysis.urls,
        is_multi_agent=analysis.is_multi_agent,
        llm_stack=analysis.llm_stack.value,
        execution_plan=execution_plan,
    )

    skill_ref = _load_fragment(
        env, "skill-reference.md", skills=selection.skills,
    )
    if skill_ref:
        prompt = f"{prompt}\n\n{skill_ref}"

    return prompt.strip()


def assemble_agent_message(
    body: str,
    analysis: TaskAnalysis,
    selection: SkillSelection,
    agent: str = "cline",
) -> str:
    if agent != "cline":
        return body

    env = _create_env()
    parts: list[str] = []

    if analysis.urls:
        preamble = _load_fragment(
            env,
            "cline-preamble.md",
            urls=analysis.urls,
            research_fetch_limit=_research_fetch_limit(),
        )
        if preamble:
            parts.append(preamble)
            parts.append("")

    stack = _render_stack(env, analysis, selection)
    if stack:
        parts.append(stack)
        parts.append("")

    if parts:
        parts.append("---")
        parts.append("")

    parts.append(body)
    return "\n".join(parts).strip()
