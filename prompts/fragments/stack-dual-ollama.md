## Stack

- Servidor LLM único: Ollama → {{ ollama_endpoint }}
- Agente A (orquestador): Ollama, modelo `{{ primary_model }}`
- Agente B (especialista): Ollama, modelo `{{ secondary_model }}`
- Comunicación entre agentes: protocolo A2A con SDK a2a-python (HTTP entre servicios A2A; no confundir con la API de Ollama)
- Python 3.11+
- Estructura: `src/`, `requirements.txt`, `README.md` con diagrama del flujo A2A y trazas de comunicación
