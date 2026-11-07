import json

import pytest

from app.reviewer import ReviewParseError, build_user_prompt, parse_llm_json


def test_parses_plain_json():
    r = parse_llm_json(json.dumps({"summary": "ok", "issues": [], "suggested_tests": ""}))
    assert r.summary == "ok"


def test_parses_json_wrapped_in_markdown_fence():
    raw = '```json\n{"summary": "ok", "issues": []}\n```'
    assert parse_llm_json(raw).summary == "ok"


def test_parses_json_with_chatter_around_it():
    assert parse_llm_json('Sure! {"summary": "ok"} Hope that helps.').summary == "ok"


def test_severity_aliases_and_bad_values_are_normalised():
    raw = json.dumps({"summary": "s", "issues": [
        {"severity": "CRITICAL", "message": "a"},
        {"severity": "weird", "message": "b", "line": "not-a-number"},
    ]})
    issues = parse_llm_json(raw).issues
    assert issues[0].severity == "high"
    assert issues[1].severity == "info" and issues[1].line is None


@pytest.mark.parametrize("raw", ["", "no json here", "{broken", '{"issues": []}'])
def test_invalid_output_raises(raw):
    with pytest.raises(ReviewParseError):
        parse_llm_json(raw)


def test_prompt_marks_code_as_untrusted_data_block():
    kind, prompt = build_user_prompt("print('hi')", "python", "a.py")
    assert kind == "code" and "<code>" in prompt and "a.py" in prompt


def test_prompt_detects_diff():
    diff = "--- a/x\n+++ b/x\n@@ -1 +1 @@\n+new\n"
    kind, prompt = build_user_prompt(diff, "python", None)
    assert kind == "diff" and "Lines added: 1" in prompt
