from pathlib import Path
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from agent import AgentError, GenerationResult
from code_tools import Artifact
from config import Settings

ROOT = Path(__file__).resolve().parents[1]


class AppTestCase(unittest.TestCase):
    def setUp(self):
        self.config = patch("config.load_settings", return_value=Settings(api_key="unit-test-key"))
        self.config.start()
        self.addCleanup(self.config.stop)

    def test_initial_view_and_empty_prompt(self):
        app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=20).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.title[0].value, "代码生成助手")
        app.button(key="FormSubmitter:generation_form-生成并检查").click().run()
        self.assertFalse(app.exception)
        self.assertIn("请先输入", app.error[0].value)

    def test_success_and_new_conversation(self):
        artifact = Artifact("add.py", "def add(a,b):\n    return a+b\n", "运行说明", "generated/add.py", "test-hash", 2)
        result = GenerationResult(artifact=artifact, rounds=2, total_tokens=100, seconds=1.0, model="deepseek-flash")
        with patch("agent.CodeGenerator.run", return_value=result):
            app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=20).run()
            app.text_area(key="request").set_value("写加法函数")
            app.button(key="FormSubmitter:generation_form-生成并检查").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.session_state["turns"]), 1)
            self.assertTrue(any("def add" in block.value for block in app.code))
            next(button for button in app.button if button.label == "开始新对话").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["turns"], [])

    def test_service_error_is_displayed_without_crashing(self):
        with patch("agent.CodeGenerator.run", side_effect=AgentError("DeepSeek API 余额不足，请检查账户余额。")):
            app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=20).run()
            app.text_area(key="request").set_value("写加法函数")
            app.button(key="FormSubmitter:generation_form-生成并检查").click().run()
            self.assertFalse(app.exception)
            self.assertIn("余额不足", app.error[0].value)
            self.assertEqual(app.session_state["turns"], [])


if __name__ == "__main__":
    unittest.main()
