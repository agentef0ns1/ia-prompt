from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ia_local_prompt.analyzer import analyze_objective
from ia_local_prompt.config_loader import PROJECT_ROOT
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
from ia_local_prompt.skill_selector import format_skills_line, select_skill, should_auto_enhance
from ia_local_prompt.template_engine import assemble_agent_message, render_prompt

app = typer.Typer(
    name="ia-prompt",
    help="Generador de prompts optimizados para agentes locales (Cline/Continue)",
    no_args_is_help=True,
)
console = Console()


class EnhanceMode(str, Enum):
    off = "off"
    on = "on"
    auto = "auto"


def _resolve_do_enhance(
    no_enhance: bool,
    enhance: bool,
    auto_enhance: bool,
    analysis,
) -> bool:
    if no_enhance:
        return False
    if enhance:
        return True
    if auto_enhance:
        return should_auto_enhance(analysis)
    return False


def _generate_single(
    objective: str,
    analysis,
    selection,
    agent: str,
    context_limit: int,
    do_enhance: bool,
    enhance_model: str | None,
    output: Path | None,
) -> None:
    draft = render_prompt(
        objective=objective,
        selection=selection,
        analysis=analysis,
        agent=agent,
        context_limit=context_limit,
    )
    draft = assemble_agent_message(draft, analysis, selection, agent=agent)

    enriched = False
    enhance_result_model = None
    enhance_latency = 0
    fallback_used = False
    validation_passed = True
    error = None
    final_prompt = draft

    if do_enhance:
        console.print("[dim]Enriqueciendo prompt vía API local...[/dim]")
        result = enrich_prompt(
            draft=draft,
            target_model=selection.model,
            enhance_model=enhance_model,
        )
        if result.enhanced:
            final_prompt = result.prompt
            enriched = True
            console.print(
                f"[green]Enriquecido[/green] con {result.model_used} "
                f"({result.latency_ms}ms)"
            )
        else:
            console.print(
                f"[yellow]Fallback al borrador determinístico[/yellow]"
                + (f": {result.error}" if result.error else "")
            )
        enhance_result_model = result.model_used
        enhance_latency = result.latency_ms
        fallback_used = result.fallback_used
        validation_passed = result.validation_passed
        error = result.error

    final_prompt, warnings = optimize_prompt(
        final_prompt, analysis, selection, agent,
    )

    metadata = build_metadata(
        prompt=final_prompt,
        analysis=analysis,
        selection=selection,
        agent=agent,
        enhanced=enriched,
        enhance_model=enhance_result_model,
        enhance_latency_ms=enhance_latency,
        fallback_used=fallback_used,
        validation_passed=validation_passed,
        error=error,
        warnings=warnings,
    )

    if output is None:
        slug = analysis.task_type.value.replace("_", "-")
        output = PROJECT_ROOT / "prompts" / "generated" / f"{slug}.md"

    prompt_path, meta_path = export_prompt(final_prompt, metadata, output)

    console.print(Panel(
        f"[bold]Modo:[/bold] prompt único\n"
        f"[bold]Skills:[/bold] {format_skills_line(selection.skills)}\n"
        f"[bold]Modelo:[/bold] {selection.model}\n"
        f"[bold]Tipo:[/bold] {analysis.task_type.value} "
        f"({analysis.complexity.value})\n"
        f"[bold]Enriquecido:[/bold] {'Sí' if enriched else 'No'}\n"
        f"[bold]Prompt:[/bold] {prompt_path}\n"
        f"[bold]Metadata:[/bold] {meta_path}",
        title="Prompt generado",
        border_style="green",
    ))

    if warnings:
        for w in warnings:
            console.print(f"[yellow]⚠ {w}[/yellow]")


def _enrich_sequence_plan(
    plan: SequencePlan,
    target_model: str,
    enhance_model: str | None,
) -> tuple[int, int, str | None, str | None]:
    """Enriquece cada paso; devuelve (pasos_ok, latencia_total, modelo, primer_error)."""
    total_latency = 0
    steps_enhanced = 0
    model_used: str | None = None
    first_error: str | None = None

    console.print(
        f"[dim]Enriqueciendo {len(plan.steps)} tareas secuenciales vía API local...[/dim]"
    )

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
        )
        total_latency += result.latency_ms
        if result.model_used:
            model_used = result.model_used

        if result.enhanced:
            step.prompt = result.prompt
            steps_enhanced += 1
            console.print(
                f"  [green]✓[/green] {step.filename} "
                f"({result.latency_ms}ms)"
            )
        else:
            if first_error is None:
                first_error = result.error
            console.print(
                f"  [yellow]○[/yellow] {step.filename} "
                f"borrador determinístico"
                + (f": {result.error}" if result.error else "")
            )

    return steps_enhanced, total_latency, model_used, first_error


def _generate_sequential(
    objective: str,
    analysis,
    selection,
    agent: str,
    output: Path | None,
    profile: str | None,
    do_enhance: bool,
    enhance_model: str | None,
) -> None:
    plan = build_sequence(
        objective=objective,
        analysis=analysis,
        selection=selection,
        agent=agent,
        profile=profile,
    )

    steps_enhanced = 0
    enhance_latency = 0
    enhance_result_model = None
    enrich_error = None

    if do_enhance:
        steps_enhanced, enhance_latency, enhance_result_model, enrich_error = (
            _enrich_sequence_plan(plan, selection.model, enhance_model)
        )

    index_content = render_sequence_index(
        plan, objective, selection, agent,
    )

    warnings: list[str] = []
    if selection.compact_prompt:
        warnings.append("Compact Prompt recomendado: ON")
    if agent == "cline":
        warnings.append("Cline: una tarea por sesión; copiar 00-INDEX.md primero")
    if analysis.urls:
        warnings.append("Tarea 1: investigación con @url / fetch_web_content")
    if plan.profile == "full":
        warnings.append("Perfil full: 5 tareas (research → scaffold → implement → verify → finalize)")
    if do_enhance:
        warnings.append(
            f"Enriquecido: {steps_enhanced}/{len(plan.steps)} tareas "
            f"({enhance_result_model or 'N/A'})"
        )

    seq_meta = build_sequence_metadata(
        plan=plan,
        selection_model=selection.model,
        selection_skill=selection.skill,
        selection_skills=selection.skills,
        agent=agent,
        task_type=analysis.task_type.value,
        complexity=analysis.complexity.value,
        urls=analysis.urls,
        warnings=warnings,
        enhanced=steps_enhanced > 0,
        enhance_model=enhance_result_model,
        enhance_latency_ms=enhance_latency,
        steps_enhanced=steps_enhanced,
        enrich_error=enrich_error,
    )

    if output is None:
        output_dir = (
            PROJECT_ROOT / "prompts" / "generated" / plan.slug / "sequence"
        )
    else:
        output_dir = output if output.suffix == "" else output.parent
        if output.suffix == ".md":
            output_dir = output.parent / (output.stem + "-sequence")

    index_path, step_paths, meta_path = export_sequence(
        plan, index_content, seq_meta, output_dir,
    )

    table = Table(title="Tareas secuenciales", show_header=True)
    table.add_column("#", style="cyan", width=4)
    table.add_column("Archivo", style="green")
    table.add_column("Descripción")
    table.add_column("LLM", style="dim")

    for step in plan.steps:
        llm_mark = "✓" if do_enhance and step.prompt else "—"
        table.add_row(
            str(step.order),
            step.filename,
            step.title,
            llm_mark if do_enhance else "—",
        )

    console.print(Panel(
        f"[bold]Modo:[/bold] secuencial ({plan.profile})\n"
        f"[bold]Skills:[/bold] {format_skills_line(selection.skills)}\n"
        f"[bold]Modelo:[/bold] {selection.model}\n"
        f"[bold]Tareas:[/bold] {len(plan.steps)}\n"
        f"[bold]Enriquecido:[/bold] "
        f"{'Sí' if steps_enhanced else 'No'}"
        f"{f' ({steps_enhanced}/{len(plan.steps)})' if do_enhance else ''}\n"
        f"[bold]Índice:[/bold] {index_path}\n"
        f"[bold]Carpeta:[/bold] {output_dir}\n"
        f"[bold]Metadata:[/bold] {meta_path}",
        title="Secuencia generada",
        border_style="green",
    ))
    console.print(table)
    console.print(
        "\n[bold]Uso:[/bold] Abre `00-INDEX.md`, luego ejecuta cada `NN-*.md` "
        "en orden en Cline (un chat por tarea)."
    )

    if warnings:
        for w in warnings:
            console.print(f"[yellow]⚠ {w}[/yellow]")


@app.command("generate")
def generate(
    objective: str = typer.Option(..., "--objective", "-o", help="Objetivo de la tarea"),
    agent: str = typer.Option("cline", "--agent", "-a", help="Agente: cline | continue"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Modelo destino"),
    skill: Optional[str] = typer.Option(None, "--skill", "-s", help="Skill principal (legacy)"),
    skills: Optional[str] = typer.Option(
        None, "--skills",
        help="Skills separadas por coma (ej: local-coding-agent,local-repo-explore)",
    ),
    context_limit: int = typer.Option(32768, "--context-limit", help="Límite de contexto"),
    enhance: bool = typer.Option(False, "--enhance", help="Enriquecer vía LLM local"),
    no_enhance: bool = typer.Option(False, "--no-enhance", help="Nunca enriquecer"),
    auto_enhance: bool = typer.Option(False, "--auto-enhance", help="Enriquecer si tarea compleja"),
    enhance_model: Optional[str] = typer.Option(
        None, "--enhance-model", help="Modelo para meta-prompting",
    ),
    sequential: bool = typer.Option(
        False, "--sequential", "--seq",
        help="Generar tareas secuenciales (varios prompts ordenados)",
    ),
    single: bool = typer.Option(
        False, "--single",
        help="Forzar un solo prompt (desactiva secuencial automático)",
    ),
    profile: Optional[str] = typer.Option(
        None, "--profile", "-p",
        help="Perfil secuencial: full | with_urls | simple",
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", help="Ruta de salida (.md único o carpeta secuencia)",
    ),
) -> None:
    """Genera prompt(s) optimizados para agentes locales."""
    analysis = analyze_objective(objective)
    skills_override = [s.strip() for s in skills.split(",")] if skills else None
    selection = select_skill(
        analysis,
        model_override=model,
        skill_override=skill,
        skills_override=skills_override,
    )
    do_enhance = _resolve_do_enhance(no_enhance, enhance, auto_enhance, analysis)

    use_sequential = should_use_sequential(analysis, sequential, single)

    if use_sequential:
        _generate_sequential(
            objective=objective,
            analysis=analysis,
            selection=selection,
            agent=agent,
            output=output,
            profile=profile,
            do_enhance=do_enhance,
            enhance_model=enhance_model,
        )
        return

    _generate_single(
        objective=objective,
        analysis=analysis,
        selection=selection,
        agent=agent,
        context_limit=context_limit,
        do_enhance=do_enhance,
        enhance_model=enhance_model,
        output=output,
    )


@app.command("analyze")
def analyze_cmd(
    objective: str = typer.Option(..., "--objective", "-o", help="Objetivo a analizar"),
) -> None:
    """Analiza un objetivo sin generar prompt."""
    analysis = analyze_objective(objective)
    selection = select_skill(analysis)
    auto = should_auto_enhance(analysis)
    profile = select_sequence_profile(analysis)
    seq_default = should_use_sequential(analysis, sequential=False, single=False)

    console.print(Panel(
        f"[bold]Tipo:[/bold] {analysis.task_type.value}\n"
        f"[bold]Complejidad:[/bold] {analysis.complexity.value}\n"
        f"[bold]Palabras:[/bold] {analysis.word_count}\n"
        f"[bold]Vago:[/bold] {'Sí' if analysis.is_vague else 'No'}\n"
        f"[bold]Multi-dominio:[/bold] {'Sí' if analysis.is_multi_domain else 'No'}\n"
        f"[bold]Archivos:[/bold] {', '.join(analysis.file_mentions) or 'ninguno'}\n"
        f"[bold]URLs:[/bold] {', '.join(analysis.urls) or 'ninguna'}\n"
        f"[bold]Multi-agente:[/bold] {'Sí' if analysis.is_multi_agent else 'No'}\n"
        f"[bold]Stack LLM:[/bold] {analysis.llm_stack.value}\n"
        f"[bold]Skills sugeridas:[/bold] {format_skills_line(selection.skills)}\n"
        f"[bold]Modelo sugerido:[/bold] {selection.model}\n"
        f"[bold]Secuencial:[/bold] {'Sí' if seq_default else 'No'} "
        f"(perfil: {profile})\n"
        f"[bold]Auto-enhance:[/bold] {'Sí' if auto else 'No'}",
        title="Análisis de tarea",
    ))


if __name__ == "__main__":
    app()


@app.command("serve")
def serve(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host de la WebUI"),
    port: int = typer.Option(8765, "--port", "-p", help="Puerto de la WebUI"),
) -> None:
    """Inicia la interfaz web de ia-prompt."""
    import uvicorn

    console.print(Panel(
        f"[bold]WebUI:[/bold] http://{host}:{port}\n"
        f"[dim]Ctrl+C para detener[/dim]",
        title="ia-prompt serve",
        border_style="green",
    ))
    uvicorn.run(
        "ia_local_prompt.webapp:app",
        host=host,
        port=port,
        reload=False,
    )
