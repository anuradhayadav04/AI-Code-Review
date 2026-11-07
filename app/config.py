import os


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


MAX_CODE_CHARS = _int("MAX_CODE_CHARS", 20000)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "mock").lower()
LLM_MODEL = os.getenv("LLM_MODEL", "")
LLM_TIMEOUT_S = _int("LLM_TIMEOUT_S", 45)
