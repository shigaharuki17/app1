import copy
import json
from pathlib import Path
from types import SimpleNamespace as NS
import tempfile
import unittest

import httpx2 as httpx
from openai import APIStatusError

from agent import AgentError, CodeGenerator
from config import Settings


def reply(name=None, args=None, *, raw=None, content=None, finish="tool_calls"):
    calls = [] if name is None else [NS(id="call_test", type="function", function=NS(
        name=name, arguments=raw if raw is not None else json.dumps(args)))]
    return NS(usage=NS(total_tokens=10), choices=[NS(finish_reason=finish,
              message=NS(content=content, tool_calls=calls))])


class ScriptedClient:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.requests = []
        self.chat = NS(completions=NS(create=self.create))

    def create(self, **kwargs):
        self.requests.append(copy.deepcopy(kwargs))
        item = next(self.responses)
        if isinstance(item, Exception):
            raise item
        return item


class AgentTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.settings = Settings(api_key="test-key", output_dir=Path(self.temp.name), max_rounds=5)

    def tearDown(self):
        self.temp.cleanup()

    def test_real_tool_feedback_repairs_bad_code(self):
        code = "def add(a, b):\n    return a + b\n"
        client = ScriptedClient([
            reply("check_python", {"code": "def bad(:\n pass"}),
            reply("check_python", {"code": code}),
            reply("submit_code", {"filename": "add.py", "code": code, "explanation": "两个数相加。"}),
        ])
        result = CodeGenerator(self.settings, client).run("生成加法函数")
        self.assertEqual(result.rounds, 3)
        self.assertEqual(result.artifact.code, code)
        self.assertEqual(result.total_tokens, 30)
        feedback = json.loads(client.requests[1]["messages"][-1]["content"])
        self.assertFalse(feedback["ok"])
        self.assertEqual(feedback["line"], 1)
        self.assertEqual(client.requests[0]["extra_body"], {"thinking": {"type": "disabled"}})

    def test_bad_json_is_recovered(self):
        code = "x = 1\n"
        client = ScriptedClient([reply("check_python", raw="{"), reply("check_python", {"code": code}),
                                 reply("submit_code", {"filename": "x.py", "code": code, "explanation": "说明"})])
        self.assertEqual(CodeGenerator(self.settings, client).run("写一个例子").rounds, 3)

    def test_context_contains_previous_result(self):
        code = "x = 2\n"
        client = ScriptedClient([reply("check_python", {"code": code}),
                                 reply("submit_code", {"filename": "x.py", "code": code, "explanation": "说明"})])
        previous = [{"prompt": "第一次需求", "result": {"artifact": {
            "filename": "old.py", "code": "x = 1", "explanation": "旧版"}}}]
        CodeGenerator(self.settings, client).run("改成2", previous)
        messages = client.requests[0]["messages"]
        self.assertEqual(messages[1]["content"], "第一次需求")
        self.assertIn("x = 1", messages[2]["content"])

    def test_empty_prompt_never_calls_api(self):
        client = ScriptedClient([])
        with self.assertRaises(AgentError):
            CodeGenerator(self.settings, client).run(" ")
        self.assertEqual(client.requests, [])

    def test_iteration_limit_stops_runaway_calls(self):
        client = ScriptedClient([reply(content="未调用工具", finish="stop") for _ in range(5)])
        with self.assertRaisesRegex(AgentError, "轮上限"):
            CodeGenerator(self.settings, client).run("写代码")
        self.assertEqual(len(client.requests), 5)

    def test_partial_tool_output_is_not_executed(self):
        code = "x = 1\n"
        client = ScriptedClient([reply("submit_code", raw="{", finish="length"),
                                 reply("check_python", {"code": code}),
                                 reply("submit_code", {"filename": "x.py", "code": code, "explanation": "说明"})])
        result = CodeGenerator(self.settings, client).run("写代码")
        self.assertEqual(result.rounds, 3)
        self.assertNotIn("tool_calls", client.requests[1]["messages"][-1])

    def test_retryable_error_is_retried(self):
        response = httpx.Response(429, request=httpx.Request("POST", "https://api.deepseek.com/chat/completions"))
        error = APIStatusError("internal detail", response=response, body=None)
        code = "x = 1\n"
        client = ScriptedClient([error, reply("check_python", {"code": code}),
                                 reply("submit_code", {"filename": "x.py", "code": code, "explanation": "说明"})])
        waits = []
        result = CodeGenerator(self.settings, client, sleep=waits.append).run("写代码")
        self.assertEqual(waits, [1])
        self.assertEqual(result.events[1]["kind"], "retry")

    def test_auth_error_does_not_leak_detail_or_retry(self):
        response = httpx.Response(401, request=httpx.Request("POST", "https://api.deepseek.com/chat/completions"))
        error = APIStatusError("private credential value", response=response, body=None)
        client = ScriptedClient([error])
        with self.assertRaises(AgentError) as caught:
            CodeGenerator(self.settings, client).run("写代码")
        self.assertNotIn("private credential", str(caught.exception))
        self.assertEqual(len(client.requests), 1)


if __name__ == "__main__":
    unittest.main()
