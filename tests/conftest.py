import json

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.metrics import Metrics


class FakeLLM:
    """Returns whatever string it was given; records the prompts it receives."""

    def __init__(self, response: str):
        self.response = response
        self.calls = []

    async def complete(self, system, user):
        self.calls.append((system, user))
        return self.response


def good_response(tests="def test_a():\n    assert 1 == 1\n"):
    return json.dumps({
        "summary": "Looks fine.",
        "issues": [{"severity": "high", "line": 3, "message": "Bug", "suggestion": "Fix"}],
        "suggested_tests": tests,
    })


@pytest.fixture
def metrics():
    return Metrics()


@pytest.fixture
def make_client(metrics):
    def _make(llm):
        return TestClient(create_app(llm=llm, metrics=metrics))
    return _make
