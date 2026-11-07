"""LLM provider clients. All implement `async complete(system, user) -> str`."""
import json
import os
import re

import httpx

from app import config

DEFAULT_MODELS = {"anthropic": "claude-sonnet-5-5", "openai": "gpt-4o-mini"}


class LLMError(RuntimeError):
    """Raised when the provider call fails."""


class MockLLM:
    """Deterministic offline reviewer so the app and tests run without an API key."""

    RULES = [
        (r"\beval\(|\bexec\(", "high", "eval/exec runs arbitrary code.",
         "Use ast.literal_eval or an explicit parser."),
        (r"^\s*except\s*:", "medium", "Bare except hides real errors.",
         "Catch specific exceptions."),
        (r"(password|secret|api_key|token)\s*=\s*['\"].+['\"]", "high",
         "Possible hard-coded secret.", "Load it from an environment variable."),
        (r"\bprint\(", "low", "print() used for output.", "Use the logging module."),
        (r"TODO|FIXME", "info", "Unresolved TODO/FIXME.", "Resolve it or open a ticket."),
    ]

    async def complete(self, system: str, user: str) -> str:
        issues = []
        body = user.split("<code>", 1)[-1]
        for i, line in enumerate(body.splitlines(), start=0):
            for pattern, sev, msg, fix in self.RULES:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append({"severity": sev, "line": i, "message": msg, "suggestion": fix})
        tests = (
            "def test_example_runs():\n"
            "    result = 1 + 1\n"
            "    assert result == 2\n"
        )
        return json.dumps({
            "summary": f"Mock review found {len(issues)} potential issue(s).",
            "issues": issues,
            "suggested_tests": tests,
        })


class AnthropicLLM:
    URL = "https://api.anthropic.com/v1/messages"

    def __init__(self, api_key: str, model: str):
        self.api_key, self.model = api_key, model

    async def complete(self, system: str, user: str) -> str:
        payload = {"model": self.model, "max_tokens": 2000, "system": system,
                   "messages": [{"role": "user", "content": user}]}
        headers = {"x-api-key": self.api_key, "anthropic-version": "2023-06-01",
                   "content-type": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=config.LLM_TIMEOUT_S) as client:
                resp = await client.post(self.URL, json=payload, headers=headers)
                resp.raise_for_status()
            return "".join(b.get("text", "") for b in resp.json()["content"])
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise LLMError(f"Anthropic request failed: {exc}") from exc


class OpenAILLM:
    URL = "https://api.openai.com/v1/chat/completions"

    def __init__(self, api_key: str, model: str):
        self.api_key, self.model = api_key, model

    async def complete(self, system: str, user: str) -> str:
        payload = {"model": self.model,
                   "messages": [{"role": "system", "content": system},
                                {"role": "user", "content": user}]}
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            async with httpx.AsyncClient(timeout=config.LLM_TIMEOUT_S) as client:
                resp = await client.post(self.URL, json=payload, headers=headers)
                resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            raise LLMError(f"OpenAI request failed: {exc}") from exc


def get_llm():
    provider = config.LLM_PROVIDER
    if provider == "anthropic":
        key = os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise LLMError("ANTHROPIC_API_KEY is not set.")
        return AnthropicLLM(key, config.LLM_MODEL or DEFAULT_MODELS["anthropic"])
    if provider == "openai":
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            raise LLMError("OPENAI_API_KEY is not set.")
        return OpenAILLM(key, config.LLM_MODEL or DEFAULT_MODELS["openai"])
    return MockLLM()
