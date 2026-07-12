# Tarea {{ step_num }}/{{ step_total }}: Implementación principal

> **Modo secuencial Cline** — ejecuta solo esta tarea. Al terminar, pasa a `{{ next_file }}`.

## Rol

Desarrollador. Modelo: `{{ model }}`. Skills: {{ skills_line }}.

## Objetivo de la tarea

Implementar la lógica principal descrita en el plan. **Escribir código funcional en disco.**

## Contexto del plan

```
[PEGA AQUÍ el ## PLAN DE IMPLEMENTACIÓN de la tarea 1, o resume si ya está en el chat]
```

{{ objective }}

{% if stack %}
{{ stack }}
{% endif %}

{{ tool_format }}

## Qué hacer

{% if is_multi_agent %}
1. Implementa `src/agent_a.py` — orquestador + A2A + Ollama (`{{ primary_model }}`).
2. Implementa `src/agent_b.py` — especialista + A2A + Ollama (`{{ secondary_model }}`).
3. Módulo compartido si hace falta: `src/a2a_config.py` o similar.
{% else %}
1. Implementa los archivos principales listados en el plan.
2. Un archivo a la vez; verifica sintaxis tras cada uno.
{% endif %}

## Qué NO hacer

- NO leer documentación web (ya investigada en tarea 1).
- NO escribir README extenso ni demo final (tareas 4 y 5).
- NO declarar el proyecto completo terminado.

## Criterios de éxito de ESTA tarea

{% if is_multi_agent %}
- [ ] `src/agent_a.py` implementado y guardado
- [ ] `src/agent_b.py` implementado y guardado
{% else %}
- [ ] Archivos principales del plan implementados y guardados
{% endif %}
- [ ] Sin errores de sintaxis (`python -m py_compile` o lint)
- [ ] Comunicación A2A / lógica core presente según el plan

## Reglas de persistencia

- Escribe cada archivo en disco antes de continuar.
- Si una tool falla, reintenta UNA vez.
- No respondas solo con explicaciones: usa `editor` en cada paso.

## Cierre

Lista archivos modificados. Continúa en `{{ next_file }}`.
