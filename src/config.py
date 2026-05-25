import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

DEFAULT_BASE_URL_CN = "https://api.minimaxi.com"
DEFAULT_BASE_URL_GLOBAL = "https://api.minimax.io"
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


def get_llm_provider() -> str:
    """deepseek | minimax，未指定时优先 deepseek（若已配置 Key）。"""
    explicit = os.getenv("LLM_PROVIDER", "").strip().lower()
    if explicit in {"deepseek", "minimax"}:
        return explicit
    if _normalize_api_key(os.getenv("DEEPSEEK_API_KEY", "")):
        return "deepseek"
    if _normalize_api_key(
        os.getenv("MINIMAX_API_KEY", "") or os.getenv("MINIMAX_CP_API_KEY", "")
    ):
        return "minimax"
    raise ValueError(
        "请在 .env 配置 LLM：\n"
        "  LLM_PROVIDER=deepseek + DEEPSEEK_API_KEY=sk-...（推荐）\n"
        "  或 LLM_PROVIDER=minimax + MINIMAX_API_KEY=..."
    )


def get_deepseek_settings() -> dict[str, str]:
    api_key = _normalize_api_key(os.getenv("DEEPSEEK_API_KEY", ""))
    if not api_key:
        raise ValueError("请在 .env 配置 DEEPSEEK_API_KEY（https://platform.deepseek.com API Keys）")
    base_url = (
        os.getenv("DEEPSEEK_BASE_URL", DEFAULT_DEEPSEEK_BASE_URL).strip()
        or DEFAULT_DEEPSEEK_BASE_URL
    ).rstrip("/")
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip() or "deepseek-chat"
    return {
        "provider": "deepseek",
        "api_key": api_key,
        "base_url": base_url,
        "model": model,
        "api_mode": "openai",
    }


def _detect_key_kind(api_key: str) -> str:
    if api_key.startswith("sk-cp-"):
        return "token_plan"
    return "open_platform"


def get_minimax_settings() -> dict[str, str]:
    api_key = _normalize_api_key(
        os.getenv("MINIMAX_API_KEY", "") or os.getenv("MINIMAX_CP_API_KEY", "")
    )
    if not api_key:
        raise ValueError(
            "请在 .env 配置 MINIMAX_API_KEY（Token Plan sk-cp- 或开放平台接口密钥）"
        )

    key_kind = _detect_key_kind(api_key)
    region = os.getenv("MINIMAX_REGION", "").strip().lower()
    if not region:
        region = "global" if key_kind == "token_plan" else "cn"

    if os.getenv("MINIMAX_BASE_URL", "").strip():
        base_url = os.getenv("MINIMAX_BASE_URL", "").strip().rstrip("/")
    elif key_kind == "token_plan":
        base_url = DEFAULT_BASE_URL_GLOBAL
    else:
        base_url = (
            DEFAULT_BASE_URL_CN
            if region in {"cn", "china", "国内"}
            else DEFAULT_BASE_URL_GLOBAL
        )

    model = os.getenv("MINIMAX_MODEL", "MiniMax-M2.7").strip() or "MiniMax-M2.7"
    group_id = os.getenv("MINIMAX_GROUP_ID", "").strip()
    api_mode = os.getenv("MINIMAX_API_MODE", "").strip().lower()
    if not api_mode:
        api_mode = (
            "openai"
            if model.startswith("MiniMax-") or model.startswith("M2")
            else "native"
        )

    return {
        "provider": "minimax",
        "api_key": api_key,
        "base_url": base_url,
        "model": model,
        "group_id": group_id,
        "api_mode": api_mode,
        "region": region,
        "key_kind": key_kind,
    }


def get_llm_settings() -> dict[str, str]:
    provider = get_llm_provider()
    if provider == "deepseek":
        return get_deepseek_settings()
    return get_minimax_settings()
