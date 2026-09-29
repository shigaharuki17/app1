import json
from pathlib import Path
import tempfile
import unittest

from code_tools import ToolSession, validate_code, valid_filename


class ToolsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.tools = ToolSession(self.root / "generated")

    def tearDown(self):
        self.temp.cleanup()

    def submit(self, code, filename="answer.py"):
        return self.tools.call("submit_code", json.dumps({"filename": filename, "code": code, "explanation": "使用示例"}))

    def test_validated_code_is_saved_exactly(self):
        code = "def add(a, b):\n    return a + b\n"
        self.assertTrue(self.tools.call("check_python", json.dumps({"code": code}))["ok"])
        self.assertTrue(self.submit(code)["ok"])
        self.assertEqual(Path(self.tools.artifact.path).read_bytes(), code.encode("utf-8"))

    def test_save_requires_receipt_for_exact_code(self):
        code = "x = 1\n"
        self.assertFalse(self.submit(code)["ok"])
        self.tools.call("check_python", json.dumps({"code": code}))
        self.assertFalse(self.submit(code + "y = 2\n")["ok"])
        self.assertFalse((self.root / "generated").exists())

    def test_compile_catches_contextual_syntax_error(self):
        self.assertFalse(validate_code("return 42")["ok"])
        result = validate_code("def bad(:\n    pass")
        self.assertFalse(result["ok"])
        self.assertEqual(result["line"], 1)

    def test_checks_never_execute_code(self):
        marker = self.root / "should_not_exist.txt"
        code = f"from pathlib import Path\nPath({str(marker)!r}).write_text('bad')\n"
        self.assertTrue(validate_code(code)["ok"])
        self.assertFalse(marker.exists())

    def test_filename_rejects_traversal_and_reserved_names(self):
        for name in ["../out.py", "D:/out.py", "..\\out.py", "CON.py", "aux.v1.py", "file.txt", "NUL.py"]:
            with self.subTest(name=name):
                self.assertFalse(valid_filename(name))
        self.assertTrue(valid_filename("solution_v2.py"))

    def test_malformed_and_unknown_calls_return_feedback(self):
        for name, args in [("check_python", "{"), ("check_python", "[]"),
                           ("check_python", '{"code": 123}'), ("shell", '{}'), ("check_python", None)]:
            with self.subTest(name=name, args=args):
                self.assertFalse(self.tools.call(name, args)["ok"])

    def test_empty_and_oversized_code(self):
        self.assertFalse(validate_code("  ")["ok"])
        self.assertFalse(validate_code("x" * 30_001)["ok"])

    def test_each_request_saves_to_distinct_folder(self):
        code = "x = 1\n"
        paths = []
        for _ in range(2):
            tool = ToolSession(self.root / "generated")
            tool.call("check_python", json.dumps({"code": code}))
            tool.call("submit_code", json.dumps({"filename": "answer.py", "code": code, "explanation": "说明"}))
            paths.append(tool.artifact.path)
        self.assertNotEqual(paths[0], paths[1])
        self.assertTrue(all(Path(path).exists() for path in paths))


if __name__ == "__main__":
    unittest.main()
