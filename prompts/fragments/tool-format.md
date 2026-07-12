## Formato de herramientas

{% if agent == "cline" %}
Cuando invoques herramientas en Cline, usa el formato XML que espera el agente.
NUNCA uses bloques ```json para invocar herramientas.
Si una tool falla, reintenta UNA vez con parámetros corregidos.
{% else %}
Usa el formato de function calling estándar (OpenAI-compatible).
Asegúrate de que `capabilities: [tool_use]` está activo en la configuración.
{% endif %}

## Regla de persistencia

Escribe todos los cambios en disco ANTES de declarar la tarea completada.
