# Tarea {{ step_num }}/{{ step_total }}: Scaffold y configuración

> **Modo secuencial Cline** — ejecuta solo esta tarea. Al terminar, pasa a `{{ next_file }}`.

## Rol

Desarrollador. Modelo: `{{ model }}`. Skills: {{ skills_line }}.

## Objetivo de la tarea

Crear la estructura base del proyecto y dependencias. **NO implementar lógica A2A completa aún.**

## PLAN DE IMPLEMENTACIÓN (pegar aquí el de la tarea anterior)

```
[PEGA AQUÍ el bloque ## PLAN DE IMPLEMENTACIÓN de 01-research.md]
```

{{ objective }}

{% if stack %}
{{ stack }}
{% endif %}

## Qué hacer

1. Crea `requirements.txt` con dependencias del plan (incluir `a2a-python` si aplica).
2. Crea estructura de directorios: `src/`, `scripts/` (y las del plan).
3. Crea archivos stub vacíos o con imports mínimos si el plan lo indica.
4. Escribe `pyproject.toml` o `.gitignore` solo si el plan lo requiere.

## Qué NO hacer

- NO implementar lógica completa de agentes A2A (eso es la tarea 3).
- NO escribir `demo_a2a.py` funcional aún.
- NO leer más documentación web.

## Criterios de éxito de ESTA tarea

- [ ] `requirements.txt` existe en disco
- [ ] Directorios `src/` y `scripts/` creados
- [ ] Archivos stub del plan creados (pueden estar vacíos o con `pass`)
- [ ] Sin errores de sintaxis en lo creado

## Cierre

Lista los archivos creados. Continúa en `{{ next_file }}`.
