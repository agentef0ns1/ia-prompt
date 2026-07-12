# Tarea {{ step_num }}/{{ step_total }}: Investigación — SOLO PLAN, SIN CÓDIGO

> **Modo secuencial Cline** — FASE 1 de {{ step_total }}. Al terminar, pasa a `{{ next_file }}`.
> **NO implementes nada en esta tarea. NO escribas archivos.**

## ⛔ ALCANCE ESTRICTO (incumplir = fallo de fase)

Esta tarea es **únicamente lectura + planificación en texto**. El código va en las tareas 2-5.

| Permitido | Prohibido |
|-----------|-----------|
| Responder en el chat | `editor`, escribir archivos |
| `fetch_web_content` (máx. {{ research_fetch_limit }}) | `run_command`, `pip install` |
| Leer archivos ya existentes | `attempt_completion` de proyecto |
| Bloque `## PLAN DE IMPLEMENTACIÓN` | `requirements.txt`, `src/`, `README.md`, scripts |

**Si creas cualquier archivo en disco en esta tarea, has fallado la secuencia.**

## Rol

Investigador técnico (solo análisis). Modelo: `{{ model }}`. Skills: {{ skills_line }}.

## Objetivo de esta fase

Leer documentación y entregar **únicamente** un plan de implementación para las fases siguientes.

{{ objective }}

{% if urls %}
{% for url in urls %}
@{{ url }}
{% endfor %}
{% endif %}

{% if stack %}
{{ stack }}
{% endif %}

## Qué hacer (solo esto)

1. Lee las URLs (`@url` o `fetch_web_content`; máximo {{ research_fetch_limit }} lecturas).
2. Resume hallazgos en ≤ 15 líneas (opcional, antes del plan).
3. Escribe **solo** el bloque `## PLAN DE IMPLEMENTACIÓN` (formato abajo).
4. Indica al usuario: copiar el plan a `{{ next_file }}`.

## Qué NO hacer — PROHIBIDO

- NO crear `requirements.txt`, `src/`, `scripts/`, `README.md` ni ningún archivo.
- NO usar herramientas de escritura ni terminal.
- NO incluir código Python, bash ni ejemplos ejecutables en tu respuesta.
- NO escribir tablas de "archivos creados" (no hay archivos en esta fase).
- NO decir "tarea completada", "implementado" ni "listo para usar".
- NO adelantar trabajo de las tareas 2 (scaffold), 3 (implement), 4 (verify) o 5 (finalize).

{{ web_fetch }}

## Formato de respuesta (ÚNICO entregable válido)

Tu mensaje final debe contener **exclusivamente** esto (puedes añadir 1 párrafo breve de contexto antes):

```markdown
## PLAN DE IMPLEMENTACIÓN

### Archivos a crear (en fases posteriores, NO ahora)
- requirements.txt — [dependencias previstas]
- src/... — [descripción]
- scripts/... — [descripción]

### Flujo técnico
[2-5 líneas del flujo A2A / arquitectura]

### Criterios de éxito por fase
- [ ] Fase 2 scaffold: ...
- [ ] Fase 3 implement: ...
- [ ] Fase 4 verify: ...

### Notas de la documentación
[Puntos clave de las URLs leídas]
```

## Verificación antes de responder

- [ ] ¿He creado algún archivo? → Si sí, **borrar y no responder hasta corregir**
- [ ] ¿Mi respuesta es solo plan + texto? → Debe ser Sí
- [ ] ¿Incluí el bloque `## PLAN DE IMPLEMENTACIÓN`? → Debe ser Sí

## Cierre de esta tarea

Responde: "Fase 1 completada. Copia el PLAN a `{{ next_file }}`." **No cierres el proyecto global.**
