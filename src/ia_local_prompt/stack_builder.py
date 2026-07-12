from __future__ import annotations

from ia_local_prompt.analyzer import LlmStack, TaskAnalysis
from ia_local_prompt.config_loader import (
    get_models_registry,
    get_prompt_generator_config,
    get_server_endpoints,
)
from ia_local_prompt.skill_selector import SkillSelection


def _secondary_model(selection: SkillSelection) -> str:
    pg = get_prompt_generator_config().get("agent_message", {})
    if override := pg.get("secondary_ollama_model"):
        return override

    registry = get_models_registry()
    for model in registry.get("models", []):
        model_id = model.get("id", "")
        if model_id != selection.model and model.get("roles"):
            if "agent" in model.get("roles", []) or "long_horizon" in model.get("roles", []):
                return model_id
    return "laguna-xs-2.1:q4_K_M"


def _stack_fragment_name(analysis: TaskAnalysis) -> str | None:
    if analysis.is_multi_agent:
        if analysis.llm_stack == LlmStack.OLLAMA_VLLM:
            return "stack-ollama-vllm.md"
        return "stack-dual-ollama.md"
    if analysis.urls or analysis.llm_stack != LlmStack.OLLAMA_ONLY:
        return "stack-single-ollama.md"
    return None
