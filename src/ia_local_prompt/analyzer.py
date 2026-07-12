from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class TaskType(str, Enum):
    CODING = "coding"
    CODE_REVIEW = "code_review"
    REPO_EXPLORE = "repo_explore"
    SECURITY_REVIEW = "security_review"
    BUG_FIX = "bug_fix"


class Complexity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class LlmStack(str, Enum):
    OLLAMA_ONLY = "ollama_only"
    OLLAMA_VLLM = "ollama_vllm"
    VLLM_ONLY = "vllm_only"


@dataclass
class TaskAnalysis:
    objective: str
    task_type: TaskType
    complexity: Complexity
    word_count: int
    file_mentions: list[str] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)
    is_vague: bool = False
    is_multi_domain: bool = False
    is_multi_agent: bool = False
    llm_stack: LlmStack = LlmStack.OLLAMA_ONLY
    domains: list[str] = field(default_factory=list)


SECURITY_KEYWORDS = {
    "seguridad", "vulnerabilidad", "cve", "exploit", "inyección", "injection",
    "xss", "csrf", "sql injection", "auth", "autenticación", "penetration",
    "auditoría de seguridad", "security", "owasp", "nuclei",
}

REVIEW_KEYWORDS = {
    "revisar", "revisión", "review", "analizar código", "code review",
    "evaluar", "inspeccionar", "auditar código",
}

EXPLORE_KEYWORDS = {
    "explorar", "entender", "comprender", "mapear", "arquitectura",
    "estructura del proyecto", "onboarding", "repositorio", "repo",
    "cómo funciona", "how does", "explain the codebase",
}

BUG_KEYWORDS = {
    "bug", "error", "fallo", "fix", "corregir", "arreglar", "depurar",
    "debug", "no funciona", "broken", "crash", "exception",
}

CODING_KEYWORDS = {
    "implementar", "crear", "desarrollar", "refactorizar", "añadir",
    "agregar", "construir", "escribir", "migrar", "actualizar",
    "implement", "create", "build", "refactor", "add feature",
}

FILE_PATTERN = re.compile(
    r"[\w./\\-]+\.(py|ts|tsx|js|jsx|go|rs|java|kt|rb|php|cs|cpp|c|h|"
    r"yaml|yml|json|toml|md|sql|sh|mod|vue|svelte)\b",
    re.IGNORECASE,
)

URL_PATTERN = re.compile(
    r"https?://[^\s<>\"')\]]+",
    re.IGNORECASE,
)

MULTI_AGENT_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bdos agentes\b",
        r"\b2 agentes\b",
        r"\btwo agents\b",
        r"\bagentes locales\b",
        r"\bprotocolo a2a\b",
        r"\ba2a\b",
        r"\bagent-to-agent\b",
    )
]


def _count_words(text: str) -> int:
    return len(text.split())


def _extract_file_mentions(text: str) -> list[str]:
    return list(dict.fromkeys(m.group(0) for m in FILE_PATTERN.finditer(text)))


def _extract_urls(text: str) -> list[str]:
    urls: list[str] = []
    for match in URL_PATTERN.finditer(text):
        url = match.group(0).rstrip(".,;:")
        if url not in urls:
            urls.append(url)
    return urls


def _detect_multi_agent(text: str) -> bool:
    return any(pattern.search(text) for pattern in MULTI_AGENT_PATTERNS)


def _detect_llm_stack(text: str, is_multi_agent: bool = False) -> LlmStack:
    if is_multi_agent:
        from ia_local_prompt.config_loader import get_prompt_generator_config

        pg = get_prompt_generator_config().get("agent_message", {})
        default = pg.get("default_multi_agent_stack", "ollama_only")
        return LlmStack(default)

    lower = text.lower()
    mentions_ollama = "ollama" in lower
    mentions_vllm = "vllm" in lower
    if mentions_ollama and mentions_vllm:
        return LlmStack.OLLAMA_VLLM
    if mentions_vllm:
        return LlmStack.VLLM_ONLY
    return LlmStack.OLLAMA_ONLY


def _detect_domains(text: str) -> list[str]:
    lower = text.lower()
    domains = []
    if any(k in lower for k in SECURITY_KEYWORDS):
        domains.append("security")
    if any(k in lower for k in REVIEW_KEYWORDS):
        domains.append("review")
    if any(k in lower for k in EXPLORE_KEYWORDS):
        domains.append("explore")
    if any(k in lower for k in BUG_KEYWORDS):
        domains.append("bug_fix")
    if any(k in lower for k in CODING_KEYWORDS):
        domains.append("coding")
    return domains


def _is_vague(text: str, word_count: int) -> bool:
    vague_phrases = [
        "mejorar", "mejora", "optimizar", "arreglar todo", "revisar todo",
        "el proyecto", "el código", "todo el", "general", "overall",
        "improve", "fix everything", "make it better",
    ]
    lower = text.lower()
    if word_count < 8:
        return True
    if any(p in lower for p in vague_phrases) and word_count < 20:
        return True
    return False


def _classify_task_type(text: str, domains: list[str]) -> TaskType:
    lower = text.lower()
    scores = {
        TaskType.SECURITY_REVIEW: sum(1 for k in SECURITY_KEYWORDS if k in lower),
        TaskType.CODE_REVIEW: sum(1 for k in REVIEW_KEYWORDS if k in lower),
        TaskType.REPO_EXPLORE: sum(1 for k in EXPLORE_KEYWORDS if k in lower),
        TaskType.BUG_FIX: sum(1 for k in BUG_KEYWORDS if k in lower),
        TaskType.CODING: sum(1 for k in CODING_KEYWORDS if k in lower),
    }
    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return TaskType.CODING
    return best


def _assess_complexity(
    word_count: int,
    file_mentions: list[str],
    is_vague: bool,
    is_multi_domain: bool,
    url_count: int = 0,
) -> Complexity:
    if is_vague or is_multi_domain or len(file_mentions) > 5:
        return Complexity.HIGH
    if len(file_mentions) > 2 or word_count > 40 or url_count >= 2:
        return Complexity.MEDIUM
    return Complexity.LOW


def analyze_objective(objective: str) -> TaskAnalysis:
    word_count = _count_words(objective)
    file_mentions = _extract_file_mentions(objective)
    urls = _extract_urls(objective)
    domains = _detect_domains(objective)
    is_vague = _is_vague(objective, word_count)
    is_multi_domain = len(domains) > 1
    is_multi_agent = _detect_multi_agent(objective)
    llm_stack = _detect_llm_stack(objective, is_multi_agent)
    task_type = _classify_task_type(objective, domains)
    complexity = _assess_complexity(
        word_count, file_mentions, is_vague, is_multi_domain, len(urls),
    )

    return TaskAnalysis(
        objective=objective,
        task_type=task_type,
        complexity=complexity,
        word_count=word_count,
        file_mentions=file_mentions,
        urls=urls,
        is_vague=is_vague,
        is_multi_domain=is_multi_domain,
        is_multi_agent=is_multi_agent,
        llm_stack=llm_stack,
        domains=domains,
    )
