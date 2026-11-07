"""Critical review of AI-generated tests.

We never execute model output. Instead we statically check that it parses,
actually contains tests and assertions, and avoids dangerous constructs.
"""
import ast

from app.schemas import TestCheck

DANGEROUS_MODULES = {"os", "subprocess", "shutil", "socket", "ctypes", "pickle", "requests", "urllib"}
DANGEROUS_CALLS = {"eval", "exec", "compile", "__import__", "open", "input"}


def validate_python_tests(code: str) -> TestCheck:
    problems: list[str] = []
    if not code.strip():
        return TestCheck(valid=False, test_count=0, assertion_count=0,
                         problems=["No tests were suggested."])
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return TestCheck(valid=False, test_count=0, assertion_count=0,
                         problems=[f"Syntax error on line {exc.lineno}: {exc.msg}"])

    test_count = 0
    assertion_count = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
            test_count += 1
        elif isinstance(node, ast.Assert):
            assertion_count += 1
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute):
                if func.attr.startswith("assert") or func.attr == "raises":
                    assertion_count += 1
            elif isinstance(func, ast.Name) and func.id in DANGEROUS_CALLS:
                problems.append(f"Uses dangerous call '{func.id}()' on line {node.lineno}.")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in DANGEROUS_MODULES:
                    problems.append(f"Imports risky module '{alias.name}' on line {node.lineno}.")
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module.split(".")[0] in DANGEROUS_MODULES:
                problems.append(f"Imports from risky module '{node.module}' on line {node.lineno}.")

    if test_count == 0:
        problems.append("No functions named test_* were found.")
    if assertion_count == 0:
        problems.append("Tests contain no assertions, so they cannot fail.")

    return TestCheck(valid=not problems, test_count=test_count,
                     assertion_count=assertion_count, problems=problems)
