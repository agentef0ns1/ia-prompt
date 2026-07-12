from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import httpx

from ia_local_prompt.config_loader import get_prompt_generator_config


@dataclass
class EnrichmentResult:
    prompt: str
    enhanced: bool
    model_used: str | None
    latency_ms: int
    fallback_used: bool
    validation_passed: bool
    error: str | None = None


META_PROMPT_TEMPLATE = """Eres un experto en prompt engineering para agentes de código locales (Cline/Continue).
Tu tarea: enriquecer el siguiente borrador de prompt para maximizar la probabilidad
de que el agente complete la tarea con éxito.

REGLAS:
- Mantén la estructura del borrador (preámbulo @url, bloque Stack, rol, skill, criterios, tools, persistencia)
- Si el borrador empieza con líneas @https://..., CONSÉRVALAS al inicio sin modificar
- Si existe el bloque "## Stack", CONSÉRVALO sin cambiar los backends LLM (Ollama/vLLM) indicados
- Añade pasos concretos y ordenados que el agente local pueda seguir
- Define criterios de éxito MEDIBLES (no "mejorar" sino "archivo X existe y pasa Y")
- Incluye advertencias específicas para el modelo destino: {target_model}
- Incluye regla explícita: "No declares la tarea completada hasta cumplir TODOS los criterios"
- NO elimines el bloque de formato de tools ni la referencia a la skill
- NO simplifiques ni alteres la arquitectura LLM descrita en el Stack
- Si el borrador incluye instrucciones de lectura web, CONSÉRVALAS (fetch_web_content, firecrawl_scrape; NUNCA firecrawl_fetch)
- Si existe el bloque "Flujo obligatorio" o "FASE 1/FASE 2", CONSÉRVALO sin acortar
- NO elimines el bloque "Estado de sesión" ni las reglas anti-pérdida de hilo
- NO acortes el borrador: la respuesta debe conservar TODAS sus secciones y ser al menos tan larga
- CONSERVA íntegramente el bloque final (tools, persistencia, skills) sin cortar frases
- Responde SOLO con el prompt enriquecido, sin explicaciones ni comentarios adicionales

BORRADOR:
{draft}
"""

SEQ_META_PROMPT_TEMPLATE = """Eres un experto en prompt engineering para agentes locales (Cline/Continue).
Enriquece UNA tarea de una secuencia ordenada. El código ya fijó la estructura; tú añades detalle útil.

CONTEXTO DE LA SECUENCIA:
- Tarea {step_num} de {step_total}: {step_title} ({step_id})
- Modelo destino del agente: {target_model}
- Siguiente archivo tras esta tarea: {next_file}

REGLAS ESTRICTAS (incumplir = inválido):
1. CONSERVA el título exacto "Tarea {step_num}/{step_total}: ..."
2. CONSERVA la línea "> **Modo secuencial Cline**" y la referencia al siguiente archivo
3. CONSERVA todas las secciones del borrador (## Rol, ## Qué hacer, ## Qué NO hacer, criterios, ## Cierre)
4. CONSERVA líneas @https://... al inicio (si existen en el borrador)
5. CONSERVA el bloque "## Stack" sin cambiar modelos ni endpoints
6. CONSERVA placeholders como [PEGA AQUÍ el ## PLAN DE IMPLEMENTACIÓN...]
7. Si el borrador tiene "## ⛔ ALCANCE ESTRICTO" o tabla Permitido/Prohibido: CONSÉRVALA íntegra
8. Si step_id=research: NO suavices prohibiciones; la fase 1 es SOLO plan, SIN archivos ni código
9. PUEDES enriquecer: pasos concretos, criterios medibles, nombres de archivos previstos, advertencias
10. NO fusiones secciones ni elimines restricciones de la fase
11. NO cambies el número de tarea ni el archivo siguiente
12. NO acortes el borrador; conserva todas las secciones y el bloque final completo
13. Responde SOLO con el prompt enriquecido

BORRADOR:
{draft}
"""


def _compute_llm_limits(meta_prompt: str, draft: str, pg: dict[str, Any]) -> tuple[int, int]:
    """Calcula num_predict y num_ctx según tamaño del borrador."""
    base = int(pg.get("max_tokens", 8192))
    cap = int(pg.get("max_tokens_cap", 16384))
    min_out = max(base, int(len(draft) * 1.15))
    max_tokens = min(min_out, cap)

    est_in = (len(meta_prompt) + len(draft)) // 3
    ctx_min = int(pg.get("num_ctx_min", 8192))
    ctx_max = int(pg.get("num_ctx_max", 32768))
    num_ctx = max(ctx_min, est_in + max_tokens + 1024)
    num_ctx = min(num_ctx, ctx_max)
    return max_tokens, num_ctx


def _is_truncated(enriched: str, draft: str) -> bool:
    if not enriched:
        return True
    if len(enriched) < len(draft) * 0.92:
        return True

    tail = enriched.rstrip()
    if tail:
        last = tail.split()[-1] if tail.split() else ""
        if len(last) <= 3 and last[-1:].isalpha():
            return True
        if tail[-1].isalnum() and not tail.endswith((".", ")", "]", "`", '"', "'")):
            if len(tail) > 20 and " " in tail[-30:]:
                last_word = tail.split()[-1]
                if len(last_word) < 4:
                    return True

    draft_lower = draft.lower()
    enriched_lower = enriched.lower()
    for marker in (
        "## formato de herramientas",
        "## reglas de persistencia",
        "## skills activas",
        "## skill",
        "persistencia",
    ):
        if marker in draft_lower and marker not in enriched_lower:
            return True

    return False


def _validate_enriched(text: str, config: dict[str, Any], draft: str = "") -> bool:
    validation = config.get("validation", {})
    min_len = validation.get("min_length_chars", 200)
    if len(text) < min_len:
        return False

    lower = text.lower()
    required = validation.get("required_sections", [])
    checks = {
        "criterios de éxito": "criterios de éxito" in lower or "criterios de exito" in lower,
        "skill": "skill" in lower,
        "persistencia": "persistencia" in lower or "no declares" in lower or "escribe" in lower,
    }
    for section in required:
        if section in checks and not checks[section]:
            return False

    if draft:
        if _is_truncated(text, draft):
            return False
        for line in draft.splitlines():
            stripped = line.strip()
            if stripped.startswith("@"):
                if stripped not in text:
                    return False
        if "## stack" in draft.lower() and "## stack" not in lower:
            return False

    return True


def _validate_research_step(text: str, draft: str) -> bool:
    lower = text.lower()
    markers = (
        "alcance estricto",
        "solo plan",
        "sin código",
        "sin codigo",
        "prohibido",
        "plan de implementación",
        "plan de implementacion",
    )
    if not any(m in lower for m in markers):
        return False
    if "editor" not in lower and "prohibido" not in lower:
        return False
    if "## ⛔" in draft and "alcance" not in lower:
        return False
    return True


def _validate_sequential_enriched(
    text: str,
    draft: str,
    step_num: int,
    step_total: int,
    step_title: str,
    next_file: str,
    step_id: str = "",
) -> bool:
    lower = text.lower()
    if len(text) < 150:
        return False

    if f"tarea {step_num}/{step_total}" not in lower:
        return False

    if "modo secuencial" not in lower:
        return False

    if next_file != "(última tarea — fin de secuencia)":
        if next_file.lower() not in lower:
            return False

    for section in ("qué hacer", "qué no hacer"):
        if section not in lower and section.replace("é", "e") not in lower:
            return False

    if "criterios" not in lower:
        return False

    for line in draft.splitlines():
        stripped = line.strip()
        if stripped.startswith("@"):
            if stripped not in text:
                return False

    if "## stack" in draft.lower() and "## stack" not in lower:
        return False

    if "pega aquí" in draft.lower():
        if "pega aquí" not in lower and "pega aqui" not in lower:
            return False

    if step_id == "research" and not _validate_research_step(text, draft):
        return False

    if _is_truncated(text, draft):
        return False

    return True


def _call_ollama(
    api_base: str,
    model: str,
    prompt: str,
    temperature: float,
    max_tokens: int,
    timeout: int,
    num_ctx: int = 8192,
) -> tuple[str, bool]:
    url = f"{api_base.rstrip('/')}/api/chat"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
            "num_ctx": num_ctx,
        },
    }
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        content = data.get("message", {}).get("content", "")
        done = bool(data.get("done", True))
        return content, done


def _call_openai_compat(
    api_base: str,
    model: str,
    prompt: str,
    temperature: float,
    max_tokens: int,
    timeout: int,
) -> str:
    url = f"{api_base.rstrip('/')}/chat/completions"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    headers = {"Authorization": "Bearer sk-local"}
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


def _invoke_llm(
    provider: str,
    api_base: str,
    model: str,
    meta_prompt: str,
    temperature: float,
    max_tokens: int,
    timeout: int,
    num_ctx: int = 8192,
) -> tuple[str, bool]:
    if provider == "openai":
        content = _call_openai_compat(
            api_base, model, meta_prompt, temperature, max_tokens, timeout,
        )
        return content, True
    return _call_ollama(
        api_base, model, meta_prompt, temperature, max_tokens, timeout, num_ctx,
    )


def enrich_prompt(
    draft: str,
    target_model: str,
    enhance_model: str | None = None,
    use_fallback: bool = False,
    api_base_override: str | None = None,
) -> EnrichmentResult:
    config = get_prompt_generator_config()
    pg = config.get("prompt_generator", {})
    provider = pg.get("provider", "ollama")
    model = enhance_model or pg.get("model", "qwen2.5-coder:14b")
    if use_fallback:
        model = pg.get("fallback_model", "gemma3:12b")

    api_base = api_base_override or pg.get("api_base", "http://192.168.1.43:11434")
    temperature = pg.get("temperature", 0.3)
    timeout = pg.get("timeout_seconds", 300)

    meta_prompt = META_PROMPT_TEMPLATE.format(
        target_model=target_model,
        draft=draft,
    )
    max_tokens, num_ctx = _compute_llm_limits(meta_prompt, draft, pg)

    start = time.monotonic()
    try:
        enriched, done = _invoke_llm(
            provider, api_base, model, meta_prompt,
            temperature, max_tokens, timeout, num_ctx,
        )

        latency = int((time.monotonic() - start) * 1000)
        enriched = enriched.strip()

        if not done or _is_truncated(enriched, draft):
            return EnrichmentResult(
                prompt=draft,
                enhanced=False,
                model_used=model,
                latency_ms=latency,
                fallback_used=use_fallback,
                validation_passed=False,
                error="Respuesta truncada por el LLM (usa borrador sin enriquecer)",
            )

        if _validate_enriched(enriched, config, draft):
            return EnrichmentResult(
                prompt=enriched,
                enhanced=True,
                model_used=model,
                latency_ms=latency,
                fallback_used=use_fallback,
                validation_passed=True,
            )

        if not use_fallback and pg.get("fallback_model"):
            return enrich_prompt(
                draft, target_model, enhance_model, use_fallback=True,
                api_base_override=api_base_override,
            )

        return EnrichmentResult(
            prompt=draft,
            enhanced=False,
            model_used=model,
            latency_ms=latency,
            fallback_used=use_fallback,
            validation_passed=False,
            error="Validación fallida: respuesta sin secciones requeridas",
        )

    except Exception as e:
        latency = int((time.monotonic() - start) * 1000)
        if not use_fallback and pg.get("fallback_model"):
            return enrich_prompt(
                draft, target_model, enhance_model, use_fallback=True,
                api_base_override=api_base_override,
            )

        return EnrichmentResult(
            prompt=draft,
            enhanced=False,
            model_used=model,
            latency_ms=latency,
            fallback_used=use_fallback,
            validation_passed=False,
            error=str(e),
        )


def enrich_sequence_step(
    draft: str,
    target_model: str,
    step_num: int,
    step_total: int,
    step_id: str,
    step_title: str,
    next_file: str,
    enhance_model: str | None = None,
    use_fallback: bool = False,
    api_base_override: str | None = None,
) -> EnrichmentResult:
    """Enriquece un paso secuencial preservando la estructura fijada por código."""
    config = get_prompt_generator_config()
    pg = config.get("prompt_generator", {})
    provider = pg.get("provider", "ollama")
    model = enhance_model or pg.get("model", "qwen2.5-coder:14b")
    if use_fallback:
        model = pg.get("fallback_model", "gemma3:12b")

    api_base = api_base_override or pg.get("api_base", "http://192.168.1.43:11434")
    temperature = pg.get("temperature", 0.3)
    timeout = pg.get("timeout_seconds", 300)

    meta_prompt = SEQ_META_PROMPT_TEMPLATE.format(
        target_model=target_model,
        step_num=step_num,
        step_total=step_total,
        step_id=step_id,
        step_title=step_title,
        next_file=next_file,
        draft=draft,
    )
    max_tokens, num_ctx = _compute_llm_limits(meta_prompt, draft, pg)

    start = time.monotonic()
    try:
        enriched, done = _invoke_llm(
            provider, api_base, model, meta_prompt,
            temperature, max_tokens, timeout, num_ctx,
        )

        latency = int((time.monotonic() - start) * 1000)
        enriched = enriched.strip()

        if not done or _is_truncated(enriched, draft):
            return EnrichmentResult(
                prompt=draft,
                enhanced=False,
                model_used=model,
                latency_ms=latency,
                fallback_used=use_fallback,
                validation_passed=False,
                error=f"Respuesta truncada (tarea {step_num}); se usa borrador original",
            )

        if _validate_sequential_enriched(
            enriched, draft, step_num, step_total, step_title, next_file, step_id,
        ):
            return EnrichmentResult(
                prompt=enriched,
                enhanced=True,
                model_used=model,
                latency_ms=latency,
                fallback_used=use_fallback,
                validation_passed=True,
            )

        if not use_fallback and pg.get("fallback_model"):
            return enrich_sequence_step(
                draft, target_model, step_num, step_total,
                step_id, step_title, next_file,
                enhance_model, use_fallback=True,
                api_base_override=api_base_override,
            )

        return EnrichmentResult(
            prompt=draft,
            enhanced=False,
            model_used=model,
            latency_ms=latency,
            fallback_used=use_fallback,
            validation_passed=False,
            error=f"Validación secuencial fallida (tarea {step_num})",
        )

    except Exception as e:
        latency = int((time.monotonic() - start) * 1000)
        if not use_fallback and pg.get("fallback_model"):
            return enrich_sequence_step(
                draft, target_model, step_num, step_total,
                step_id, step_title, next_file,
                enhance_model, use_fallback=True,
                api_base_override=api_base_override,
            )

        return EnrichmentResult(
            prompt=draft,
            enhanced=False,
            model_used=model,
            latency_ms=latency,
            fallback_used=use_fallback,
            validation_passed=False,
            error=str(e),
        )
