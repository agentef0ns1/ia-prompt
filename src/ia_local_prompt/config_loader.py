from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

# ia-prompt/ (paquete de la herramienta)
PACKAGE_ROOT = Path(__file__).resolve().parents[2]
# IA-Local/ (workspace: configs compartidos del stack)
WORKSPACE_ROOT = PACKAGE_ROOT.parent

TOOL_CONFIG_DIR = PACKAGE_ROOT / "config"
SHARED_CONFIG_DIR = WORKSPACE_ROOT / "config"
PROMPTS_DIR = PACKAGE_ROOT / "prompts"

# Compatibilidad con código que usaba PROJECT_ROOT
PROJECT_ROOT = PACKAGE_ROOT


def load_yaml(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_tool_config(name: str) -> dict[str, Any]:
    return load_yaml(TOOL_CONFIG_DIR / name)


def load_shared_config(name: str) -> dict[str, Any]:
    return load_yaml(SHARED_CONFIG_DIR / name)


def load_config(name: str) -> dict[str, Any]:
    """Carga config de la herramienta; fallback al workspace compartido."""
    tool_path = TOOL_CONFIG_DIR / name
    if tool_path.exists():
        return load_yaml(tool_path)
    return load_shared_config(name)


def get_models_registry() -> dict[str, Any]:
    return load_shared_config("models-registry.yaml")


def get_hardware_profile() -> dict[str, Any]:
    return load_shared_config("hardware-profile.yaml")


def get_server_endpoints() -> dict[str, Any]:
    return load_shared_config("server-endpoints.yaml")


def get_prompt_generator_config() -> dict[str, Any]:
    return load_tool_config("prompt-generator.yaml")
