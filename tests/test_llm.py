import asyncio
import json

import pytest

from app import llm
from app.llm import LLMError, MockLLM, get_llm


def test_mock_flags_known_risky_patterns():
    code = "<code>\nx = eval(input())\npassword = 'abc'\n"
    out = json.loads(asyncio.run(MockLLM().complete("sys", code)))
    sev = {i["severity"] for i in out["issues"]}
    assert "high" in sev and len(out["issues"]) == 2


def test_mock_clean_code_has_no_issues():
    out = json.loads(asyncio.run(MockLLM().complete("sys", "<code>\nx = 1\n")))
    assert out["issues"] == []


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.setattr(llm.config, "LLM_PROVIDER", "anthropic")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(LLMError):
        get_llm()


def test_default_provider_is_mock(monkeypatch):
    monkeypatch.setattr(llm.config, "LLM_PROVIDER", "mock")
    assert isinstance(get_llm(), MockLLM)
