"""Load local configuration without logging or duplicating API credentials."""
from dataclasses import dataclass, field
import os
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent
API_URL = "https://api.deepseek.com"


class ConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class Settings:
    api_key: str = field(repr=False)
    model: str = "deepseek-flash"
    max_rounds: int = 8
    timeout: float = 60.0
    output_dir: Path = ROOT / "generated"


def load_settings(root: Path = ROOT) -> Settings:
    values = dotenv_values(root / ".env", encoding="utf-8-sig")

    def get(name: str, default: str = "") -> str:
        return str(os.environ.get(name, values.get(name) or default)).strip()

    key = get("DEEPSEEK_API_KEY")
    key_file = get("DEEPSEEK_API_KEY_FILE")
    if not key and key_file:
        path = Path(key_file).expanduser()
        if not path.is_absolute():
            path = root / path
        try:
            key = path.read_text(encoding="utf-8-sig").strip()
        except (OSError, UnicodeError):
            raise ConfigurationError("无法读取密钥文件，请检查 .env 中 DEEPSEEK_API_KEY_FILE 的路径。") from None
    if not key or key.startswith("your_") or key.startswith("这里"):
        raise ConfigurationError("请在 .env 中配置 DEEPSEEK_API_KEY 或 DEEPSEEK_API_KEY_FILE。")
    if any(c.isspace() for c in key) or not key.isascii():
        raise ConfigurationError("密钥格式不正确：密钥文件应只包含一行 API Key。")
    try:
        rounds = int(get("AGENT_MAX_ROUNDS", "8"))
        timeout = float(get("API_TIMEOUT_SECONDS", "60"))
    except ValueError:
        raise ConfigurationError("轮数和超时时间必须为数字。") from None
    if not 2 <= rounds <= 12 or not 10 <= timeout <= 180:
        raise ConfigurationError("AGENT_MAX_ROUNDS 应为 2–12，API_TIMEOUT_SECONDS 应为 10–180。")
    model = get("DEEPSEEK_MODEL", "deepseek-flash")
    if not model:
        raise ConfigurationError("请填写 DEEPSEEK_MODEL。")
    return Settings(api_key=key, model=model, max_rounds=rounds,
                    timeout=timeout, output_dir=root / "generated")
