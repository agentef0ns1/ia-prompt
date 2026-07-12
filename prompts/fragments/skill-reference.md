## Skills activas

Activa y sigue **todas** estas skills durante la ejecución:

{% for s in skills %}
- `{{ s }}` — lee `.clinerules/skills/{{ s }}.md` en este proyecto
{% endfor %}

**Antes de actuar:** abre y lee cada archivo de skill listado arriba.
Si `.clinerules/skills/` no existe, copia `IA-Local/clinerules/skills/` al proyecto como `.clinerules/skills/`.
