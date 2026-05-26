import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com"


def _normalize_api_key(raw: str) -> str:
    key = raw.strip().strip('"').strip("'")
    if key.lower().startswith("bearer "):
        key = key[7:].strip()
    return key


def get_aliyun_credentials() -> tuple[str, str, str]:
    access_key_id = os.getenv("ALIYUN_ACCESS_KEY_ID", "").strip()
    access_key_secret = os.getenv("ALIYUN_ACCESS_KEY_SECRET", "").strip()
    region = os.getenv("ALIYUN_REGION", "cn-hangzhou").strip() or "cn-hangzhou"
    if not access_key_id or not access_key_secret:
        raise ValueError(
            "请在项目根目录创建 .env 并填写 ALIYUN_ACCESS_KEY_ID / ALIYUN_ACCESS_KEY_SECRET"
        )
    return access_key_id, access_key_secret, region


def get_llm_settings() -> dict[str, str]:
    api_key = _normalize_api_key(os.getenv("DEEPSEEK_API_KEY", ""))
    if not api_key:
        raise ValueError(
            "请在 .env 配置 DEEPSEEK_API_KEY（https://platform.deepseek.com API Keys）"
        )
    base_url = (
        os.getenv("DEEPSEEK_BASE_URL", DEFAULT_DEEPSEEK_BASE_URL).strip()
        or DEFAULT_DEEPSEEK_BASE_URL
    ).rstrip("/")
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip() or "deepseek-chat"
    return {
        "api_key": api_key,
        "base_url": base_url,
        "model": model,
    }
