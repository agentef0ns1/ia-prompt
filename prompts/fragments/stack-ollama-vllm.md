## Stack

- Agente A (orquestador): LLM vía Ollama → {{ ollama_endpoint }} (modelo `{{ primary_model }}`)
- Agente B (especialista): LLM vía vLLM OpenAI-compatible → {{ vllm_endpoint }} (modelo `{{ secondary_model }}`)
- Comunicación entre agentes: protocolo A2A con SDK a2a-python
- Python 3.11+
- Estructura: `src/`, `requirements.txt`, `README.md` con diagrama del flujo A2A y trazas de comunicación
