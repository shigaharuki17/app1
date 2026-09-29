"""Command-line entry point, including an inexpensive API connectivity check."""
import argparse
import sys

from openai import OpenAI

from agent import AgentError, CodeGenerator, friendly_api_error
from config import API_URL, ConfigurationError, load_settings


def main() -> int:
    parser = argparse.ArgumentParser(description="DeepSeek 代码生成 Agent")
    parser.add_argument("prompt", nargs="?", help="用自然语言描述 Python 代码需求")
    parser.add_argument("--check-api", action="store_true", help="检查密钥及模型访问权限，不生成代码")
    args = parser.parse_args()
    try:
        settings = load_settings()
        if args.check_api:
            try:
                with OpenAI(api_key=settings.api_key, base_url=API_URL, timeout=20, max_retries=0) as client:
                    names = {item.id for item in client.models.list().data}
            except Exception as exc:
                raise AgentError(friendly_api_error(exc)) from None
            if settings.model not in names:
                raise AgentError("密钥有效，但当前模型不在可用列表中，请调整 DEEPSEEK_MODEL。")
            print(f"连接成功，模型可用：{settings.model}")
            return 0
        if not args.prompt:
            parser.error("请提供代码需求，或者使用 --check-api。")
        with CodeGenerator(settings) as generator:
            result = generator.run(args.prompt, on_event=lambda event: print(event["text"], flush=True))
        print(f"\n已保存：{result.artifact.path}\n")
        print(result.artifact.explanation)
        print(f"\n{result.rounds} 轮 · {result.total_tokens} tokens · {result.seconds} 秒")
        return 0
    except (ConfigurationError, AgentError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1
    except Exception:
        print("发生未预期错误，请检查配置后重试。", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
