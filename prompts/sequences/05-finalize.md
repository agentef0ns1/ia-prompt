# Tarea {{ step_num }}/{{ step_total }}: Documentación y cierre

> **Modo secuencial Cline** — última tarea de la secuencia.

## Rol

Desarrollador. Modelo: `{{ model }}`. Skills: {{ skills_line }}.

## Objetivo de la tarea

Completar README, verificar checklist global y cerrar el proyecto.

{{ objective }}

{% if stack %}
{{ stack }}
{% endif %}

## Qué hacer

1. Escribe o completa `README.md`:
   - Arquitectura y diagrama de flujo
   - Cómo arrancar cada componente
   - Ejemplo de traza de comunicación
2. Recorre el checklist global (abajo).
3. Corrige cualquier hueco pendiente menor.

## Checklist global (OBLIGATORIO antes de cerrar)

- [ ] Código implementado y en disco
- [ ] Sin errores de sintaxis
- [ ] Funcionalidad alineada con el objetivo original
- [ ] Demo o test de verificación ejecutado
{% if is_multi_agent %}
- [ ] README con diagrama A2A y traza de ejemplo
- [ ] Intercambio A2A demostrado entre agentes
{% endif %}
{% if urls %}
- [ ] Implementación coherente con documentación consultada en tarea 1
{% endif %}

## Qué NO hacer

- NO iniciar features nuevas fuera del objetivo.
- NO releer toda la documentación.

## Cierre

Solo declara **PROYECTO COMPLETO** cuando todos los checks estén marcados.
Lista archivos finales del repositorio.
