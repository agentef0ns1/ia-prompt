# Secuencia de tareas: {{ title }}

Generado por `ia-prompt generate` (modo secuencial).

**Objetivo global:** {{ objective }}

**Skills:** {{ skills_line }} | **Modelo:** `{{ model }}` | **Agente:** {{ agent }}

## Orden de ejecución (obligatorio)

Ejecuta **una tarea por sesión Cline** (o un chat limpio por tarea). No combines fases.

| # | Archivo | Descripción |
|---|---------|-------------|
{% for step in steps -%}
| {{ step.order }} | `{{ step.filename }}` | {{ step.title }} |
{% endfor %}

## Flujo

```
{% for step in steps -%}
{{ step.order }}. {{ step.filename }} → {{ step.title }}
{% endfor %}
```

## Instrucciones

1. Abre Cline en modo **Agente** con `{{ model }}` y Compact Prompt ON.
2. Copia y pega **solo** el contenido de `01-...md` como primer mensaje.
3. **Tarea 1 (research):** solo texto y `## PLAN DE IMPLEMENTACIÓN` — **ningún archivo en disco**.
4. Al terminar cada tarea, copia el entregable indicado en la siguiente.
5. No avances a la siguiente tarea sin cumplir los criterios de la actual.

## Configuración recomendada

- `.clinerules/` copiado al proyecto
- Context window: 32768
- MCP Firecrawl: opcional (tarea 1); usar `fetch_web_content` preferido
