## Flujo obligatorio: investigación → implementación

Esta tarea tiene **2 fases secuenciales**. No puedes quedarte solo en la fase 1.

### FASE 1 — Investigación (máximo {{ research_fetch_limit }} lecturas web)

**Objetivo:** entender lo mínimo indispensable para implementar.

**Límites estrictos:**
- Máximo **{{ research_fetch_limit }}** llamadas a `fetch_web_content` / `firecrawl_scrape` en total.
- Máximo **1 mensaje** de resumen (≤ 15 líneas) al cerrar esta fase.
- **PROHIBIDO** seguir leyendo tras alcanzar el límite o tras tener suficiente contexto.

**Salida obligatoria al cerrar FASE 1** (bloque exacto):

```
## PLAN DE IMPLEMENTACIÓN
Archivos a crear:
- requirements.txt
- src/...
- scripts/...
Flujo A2A: [2-3 líneas]
Siguiente archivo a escribir: [ruta]
```

**Inmediatamente después del plan:** escribe el primer archivo en disco. Sin pedir confirmación al usuario.

### FASE 2 — Implementación (OBLIGATORIA; no opcional)

**Objetivo:** crear código funcional en disco.

**Reglas:**
- **DEBES** usar la tool `editor` / escribir archivos en cada paso de implementación.
- **PROHIBIDO** responder solo con explicaciones, resúmenes o análisis sin escribir código.
- **PROHIBIDO** volver a leer documentación una vez iniciada FASE 2.
- **PROHIBIDO** declarar la tarea completada sin archivos en disco verificados.
- Si ya entiendes el protocolo → **deja de leer y empieza a codificar**.

### Estado de sesión (actualizar al INICIO de cada respuesta)

```
FASE: [1-Investigación | 2-Implementación]
Paso plan: N/7
Lecturas web usadas: X/{{ research_fetch_limit }}
Archivos en disco: [lista o "ninguno"]
Siguiente acción: [una sola acción concreta con tool]
```

Si `Archivos en disco: ninguno` y ya usaste ≥ 2 lecturas web → tu siguiente acción **DEBE** ser escribir `requirements.txt` o el primer `.py`.
