# Tarea {{ step_num }}/{{ step_total }}: Demo, pruebas y verificación

> **Modo secuencial Cline** — ejecuta solo esta tarea. Al terminar, pasa a `{{ next_file }}`.

## Rol

Desarrollador / QA. Modelo: `{{ model }}`. Skills: {{ skills_line }}.

## Objetivo de la tarea

Crear script de demostración, ejecutar verificaciones y confirmar que la implementación funciona.

{{ objective }}

{% if stack %}
{{ stack }}
{% endif %}

## Qué hacer

1. Crea `scripts/demo_a2a.py` (o el script de demo del plan) con trazas visibles.
2. Ejecuta verificación de sintaxis en todos los `.py`.
3. Si es posible, ejecuta el demo y captura salida/trazas.
4. Corrige errores evidentes encontrados.

## Qué NO hacer

- NO reescribir toda la arquitectura (solo fixes menores).
- NO leer documentación web.
- NO escribir README final (siguiente tarea).

## Criterios de éxito de ESTA tarea

- [ ] Script de demo existe y está guardado en disco
- [ ] Sintaxis verificada en archivos del proyecto
- [ ] Demo ejecutado o justificación clara si no se pudo ejecutar
{% if is_multi_agent %}
- [ ] Trazas de comunicación A2A visibles en logs o salida
{% endif %}

## Cierre

Resume resultados de pruebas. Continúa en `{{ next_file }}`.
