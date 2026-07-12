## Documentación web (Cline)

Para leer URLs del objetivo:

| Prioridad | Método | Cuándo |
|-----------|--------|--------|
| 1 | `@url` en el prompt | Siempre que sea posible |
| 2 | `fetch_web_content` | Tool nativa Cline; sin API key |
| 3 | `firecrawl_scrape` | Solo si @url/fetch fallan; requiere MCP conectado |

**Firecrawl sin API key (keyless):** `scrape`, `search`, `map` con límites. Sin `monitor_*`, `crawl` profundo ni `agent`.

**Firecrawl con API key:** añade en MCP:
```json
"headers": { "Authorization": "Bearer fc-TU_API_KEY" }
```
Clave gratuita: https://firecrawl.dev/app/api-keys

**Tool incorrecta (falla siempre):** `firecrawl_fetch` — no existe. Usa `firecrawl_scrape`.
