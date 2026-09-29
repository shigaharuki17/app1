"""Agent tools. Generated Python is parsed and compiled, never executed."""
import ast
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import uuid

MAX_CODE_CHARS = 30_000

TOOLS = [
    {"type": "function", "function": {
        "name": "check_python",
        "description": "检查完整 Python 源码的语法及编译有效性，不执行代码。错误时返回行号。提交前必须调用。",
        "parameters": {"type": "object", "properties": {
            "code": {"type": "string", "description": "完整 Python 源码，不含 Markdown 围栏，最多 30000 字符"}},
            "required": ["code"], "additionalProperties": False}}},
    {"type": "function", "function": {
        "name": "submit_code",
        "description": "保存并交付本轮已经通过 check_python 的完全相同的代码。代码有改动必须重新检查。",
        "parameters": {"type": "object", "properties": {
            "filename": {"type": "string", "description": "简单英文文件名，如 solution.py，禁止目录路径"},
            "code": {"type": "string", "description": "与通过检查的版本逐字相同的完整 Python 源码"},
            "explanation": {"type": "string", "description": "中文说明功能、运行方法、示例和仍需手动验证的情况；不要声称实际执行过"}},
            "required": ["filename", "code", "explanation"], "additionalProperties": False}}},
]


@dataclass
class Artifact:
    filename: str
    code: str
    explanation: str
    path: str
    sha256: str
    lines: int

    def to_dict(self) -> dict:
        return asdict(self)


def validate_code(code: str) -> dict:
    if not isinstance(code, str) or not code.strip():
        return {"ok": False, "error": "代码不能为空。"}
    if len(code) > MAX_CODE_CHARS:
        return {"ok": False, "error": f"代码超过 {MAX_CODE_CHARS} 字符，请简化为一个脚本。"}
    try:
        tree = ast.parse(code, filename="generated.py")
        compile(tree, "generated.py", "exec", dont_inherit=True)
    except (SyntaxError, ValueError, RecursionError, MemoryError) as exc:
        return {"ok": False, "error": getattr(exc, "msg", "无法解析代码，请简化嵌套结构。"),
                "line": getattr(exc, "lineno", None), "column": getattr(exc, "offset", None)}
    digest = hashlib.sha256(code.encode("utf-8")).hexdigest()
    return {"ok": True, "sha256": digest, "lines": len(code.splitlines()),
            "functions": [n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))][:30],
            "note": "仅通过语法和编译检查，未运行代码，尚未验证业务逻辑及第三方依赖。"}


def valid_filename(filename: str) -> bool:
    if not isinstance(filename, str) or not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,74}\.py", filename):
        return False
    stem = filename.split(".")[0].upper()
    return stem not in {"CON", "PRN", "AUX", "NUL", *[f"COM{i}" for i in range(1, 10)], *[f"LPT{i}" for i in range(1, 10)]}


class ToolSession:
    """Per-request validation receipts prevent saving unvalidated replacements."""
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.checked: dict[str, dict] = {}
        self.artifact: Artifact | None = None

    def call(self, name: str, arguments: str) -> dict:
        if not isinstance(arguments, str):
            return {"ok": False, "error": "工具参数必须是 JSON 字符串。"}
        if len(arguments) > MAX_CODE_CHARS * 8:
            return {"ok": False, "error": "工具参数过长，请缩短代码。"}
        try:
            args = json.loads(arguments)
        except (json.JSONDecodeError, TypeError, RecursionError):
            return {"ok": False, "error": "工具参数必须是有效 JSON，请重新调用。"}
        expected = {"check_python": {"code"}, "submit_code": {"filename", "code", "explanation"}}
        if name not in expected:
            return {"ok": False, "error": "未知工具，请使用 check_python 或 submit_code。"}
        if not isinstance(args, dict) or set(args) != expected[name] or not all(isinstance(v, str) for v in args.values()):
            return {"ok": False, "error": "参数字段或类型不正确，请按工具定义传入字符串。"}
        if name == "check_python":
            result = validate_code(args["code"])
            if result["ok"]:
                self.checked[result["sha256"]] = result
            return result
        if self.artifact is not None:
            return {"ok": False, "error": "本轮已经交付一个文件。"}
        if not valid_filename(args["filename"]):
            return {"ok": False, "error": "请使用简单英文 .py 文件名，不能包含路径或系统保留名称。"}
        if not args["explanation"].strip() or len(args["explanation"]) > 6000:
            return {"ok": False, "error": "请提供 1–6000 字符的中文使用说明。"}
        digest = hashlib.sha256(args["code"].encode("utf-8")).hexdigest()
        if digest not in self.checked:
            return {"ok": False, "error": "该版本尚未通过检查。请先调用 check_python 检查逐字相同的代码。"}
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid.uuid4().hex[:12]
        try:
            root = self.output_dir.resolve()
            folder = root / run_id
            folder.mkdir(parents=True, exist_ok=False)
            target = folder / args["filename"]
            if not target.resolve().is_relative_to(root):
                return {"ok": False, "error": "保存路径超出生成目录。"}
            with target.open("x", encoding="utf-8", newline="") as handle:
                handle.write(args["code"])
        except OSError:
            return {"ok": False, "error": "文件保存失败，请检查 generated 目录的写入权限和磁盘空间。"}
        self.artifact = Artifact(filename=args["filename"], code=args["code"], explanation=args["explanation"],
                                 path=str(target), sha256=digest, lines=self.checked[digest]["lines"])
        return {"ok": True, "filename": args["filename"], "sha256": digest,
                "note": "代码已保存，语法检查通过，未执行生成代码。"}
