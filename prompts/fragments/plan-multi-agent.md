## Plan de ejecución

> **FASE 1** = pasos 1 (máx. {{ research_fetch_limit }} lecturas web + plan).
> **FASE 2** = pasos 2-7 (escritura obligatoria en disco). No vuelvas al paso 1.

1. **Investigación acotada** (FASE 1 — máx. {{ research_fetch_limit }} fetch):
   - Lee solo lo necesario de las URLs del preámbulo.
   - Escribe el bloque `## PLAN DE IMPLEMENTACIÓN` con lista de archivos.
   - **Inmediatamente** crea `requirements.txt` — esto cierra FASE 1.

2. **Configuración inicial** (FASE 2):
   - Crea `requirements.txt` con `a2a-python` y dependencias.
   - Configura acceso a Ollama: `OLLAMA_HOST={{ ollama_endpoint }}`.
   - Cada agente A2A apunta a su modelo correspondiente.

3. **Implementación Agente A** (`{{ primary_model }}`):
   - Crea `src/agent_a.py` con servidor/cliente A2A y llamadas al LLM.
   - Implementa las funciones propias del orquestador.

4. **Implementación Agente B** (`{{ secondary_model }}`):
   - Crea `src/agent_b.py` con servidor/cliente A2A y llamadas al LLM.
   - Implementa las funciones propias del especialista.

5. **Pruebas y verificación**:
   - Script `scripts/demo_a2a.py` que arranca ambos agentes y muestra trazas A2A.
   - Verifica sintaxis y que el intercambio sigue el protocolo.

6. **Documentación**:
   - README con arquitectura, puertos A2A, modelos por agente y diagrama de flujo.

7. **Finalización**:
   - Guarda todo en disco y verifica el checklist de criterios de éxito.
