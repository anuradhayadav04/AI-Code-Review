from app.diff_utils import extract_added_lines, is_unified_diff

DIFF = """--- a/app.py
+++ b/app.py
@@ -1,3 +1,4 @@
 import os
-x = 1
+x = 2
+y = 3
 print(x)
"""


def test_detects_diff():
    assert is_unified_diff(DIFF)


def test_plain_code_is_not_diff():
    assert not is_unified_diff("def f():\n    return 1\n")


def test_added_lines_use_new_file_numbers():
    added = extract_added_lines(DIFF)
    assert [(a.file, a.line, a.text) for a in added] == [
        ("app.py", 2, "x = 2"),
        ("app.py", 3, "y = 3"),
    ]


def test_multiple_files_and_hunks():
    diff = DIFF + "--- a/b.py\n+++ b/b.py\n@@ -10,1 +10,2 @@\n a\n+b\n"
    added = extract_added_lines(diff)
    assert added[-1].file == "b.py" and added[-1].line == 11


def test_no_added_lines():
    assert extract_added_lines("--- a/x\n+++ b/x\n@@ -1 +1 @@\n-gone\n") == []
