from app.validator import validate_python_tests


def test_valid_tests_pass():
    r = validate_python_tests("def test_a():\n    assert 1 + 1 == 2\n")
    assert r.valid and r.test_count == 1 and r.assertion_count == 1 and r.problems == []


def test_syntax_error_is_reported():
    r = validate_python_tests("def test_a(:\n    pass")
    assert not r.valid
    assert "Syntax error" in r.problems[0]


def test_empty_input_invalid():
    assert not validate_python_tests("   ").valid


def test_no_assertions_flagged():
    r = validate_python_tests("def test_a():\n    x = 1\n")
    assert not r.valid
    assert any("no assertions" in p for p in r.problems)


def test_no_test_functions_flagged():
    r = validate_python_tests("def helper():\n    assert True\n")
    assert not r.valid
    assert any("test_*" in p for p in r.problems)


def test_dangerous_import_and_call_flagged():
    code = "import subprocess\ndef test_a():\n    eval('1')\n    assert True\n"
    r = validate_python_tests(code)
    assert not r.valid
    joined = " ".join(r.problems)
    assert "subprocess" in joined and "eval" in joined


def test_pytest_raises_counts_as_assertion():
    code = "import pytest\ndef test_a():\n    with pytest.raises(ValueError):\n        int('x')\n"
    assert validate_python_tests(code).valid
