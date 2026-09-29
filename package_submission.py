"""Build an explicit allowlist archive; never collect the workspace recursively."""
import argparse
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parent
FILES = ["app.py", "agent.py", "code_tools.py", "config.py", "cli.py", "requirements.txt",
         "README.md", "DESIGN.md", "DEMO.md", ".env.example", ".gitignore",
         "run.bat", "setup.bat", "package_submission.py", ".streamlit/config.toml",
         "tests/test_tools.py", "tests/test_agent.py", "tests/test_config.py", "tests/test_app.py"]


def package(output: Path) -> Path:
    missing = [name for name in FILES if not (ROOT / name).is_file()]
    if missing:
        raise FileNotFoundError("缺少提交文件：" + ", ".join(missing))
    if output.resolve().is_relative_to(ROOT / ".venv"):
        raise ValueError("请将压缩包输出到虚拟环境之外。")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in FILES:
            archive.write(ROOT / name, "codegen-agent/" + name)
    return output.resolve()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="打包作业源码及文档，不包含密钥、依赖和生成文件")
    parser.add_argument("--output", type=Path, default=ROOT / "submission" / "codegen-agent.zip")
    print(package(parser.parse_args().output))
