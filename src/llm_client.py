import httpx

from src.config import ROOT_DIR, get_llm_settings
from src.domain_cache import collect_avoid_domains, format_avoid_domains_for_prompt
from src.domain_parser import parse_domain_list

PROMPT_PATH = ROOT_DIR / "prompts" / "domain_generator.txt"


def load_prompt_template() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def render_prompt(business: str) -> str:
    template = load_prompt_template()
    avoid = format_avoid_domains_for_prompt()
    return (
        template.replace("{{business}}", business.strip()).replace(
            "{{avoid_domains}}", avoid
        )
    )


def _auth_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def _build_url(settings: dict[str, str]) -> str:
    base = settings["base_url"]
    provider = settings.get("provider", "")
    mode = settings.get("api_mode", "openai")

    if provider == "deepseek" or (provider != "minimax" and mode == "openai"):
        return f"{base}/v1/chat/completions"

    if mode == "anthropic":
        return f"{base}/anthropic/v1/messages"
    if mode == "openai":
        return f"{base}/v1/chat/completions"

    url = f"{base}/v1/text/chatcompletion_v2"
    group_id = settings.get("group_id") or ""
    if group_id:
        return f"{url}?GroupId={group_id}"
    return url


def _build_headers(settings: dict[str, str]) -> dict[str, str]:
    api_key = settings["api_key"]
    if settings.get("api_mode") == "anthropic":
        return {
            "X-Api-Key": api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }
    return _auth_headers(api_key)


def _build_payload(settings: dict[str, str], prompt: str) -> dict:
    if settings.get("api_mode") == "anthropic":
        return {
            "model": settings["model"],
            "max_tokens": 8192,
            "messages": [{"role": "user", "content": prompt}],
        }
    return {
        "model": settings["model"],
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.8,
    }


def _extract_openai_content(payload: dict) -> str | None:
    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        message = choices[0].get("message") or {}
        content = message.get("content")
        if content:
            return str(content)
    return None


def _extract_content(payload: dict, *, settings: dict[str, str]) -> str:
    api_mode = settings.get("api_mode", "openai")
    provider = settings.get("provider", "")
    key_kind = settings.get("key_kind", "")

    if api_mode == "anthropic":
        content_blocks = payload.get("content")
        if isinstance(content_blocks, list):
            texts = []
            for block in content_blocks:
                if isinstance(block, dict) and block.get("type") == "text":
                    texts.append(str(block.get("text", "")))
            merged = "".join(texts).strip()
            if merged:
                return merged

    content = _extract_openai_content(payload)
    if content:
        return content

    reply = payload.get("reply")
    if reply:
        return str(reply)

    base_resp = payload.get("base_resp") or {}
    status_code = base_resp.get("status_code", 0)
    if status_code != 0:
        status_msg = base_resp.get("status_msg", "未知错误")
        raise ValueError(_format_api_error(provider, status_code, status_msg, key_kind))

    raise ValueError(f"无法从 {provider} 响应中解析文本: {payload}")


def _format_api_error(
    provider: str,
    status_code: int | str,
    status_msg: str,
    key_kind: str = "",
) -> str:
    msg = f"{provider} 返回错误: {status_code} {status_msg}"
    if provider != "minimax":
        return msg

    if str(status_code) == "1004" or "login fail" in status_msg.lower():
        if key_kind == "token_plan":
            msg += (
                "\nToken Plan Key（sk-cp-）鉴权失败，常见原因：Key 复制不完整、套餐无额度、"
                "或 Key 已失效。可改用 DeepSeek：LLM_PROVIDER=deepseek + DEEPSEEK_API_KEY。"
            )
        else:
            msg += (
                "\n请检查 MINIMAX_API_KEY 与 MINIMAX_BASE_URL 是否匹配（国内 minimaxi.com / 国际 minimax.io）。"
            )
    return msg


def _raise_http_error(response: httpx.Response, payload: dict | str, settings: dict) -> None:
    provider = settings.get("provider", "llm")
    key_kind = settings.get("key_kind", "")

    if isinstance(payload, dict):
        err = payload.get("error") or {}
        if isinstance(err, dict) and err.get("message"):
            raise ValueError(
                _format_api_error(
                    provider,
                    err.get("http_code", response.status_code),
                    str(err.get("message")),
                    key_kind,
                )
            )
    raise ValueError(f"{provider} HTTP {response.status_code}: {payload}")


def generate_domains(business: str) -> list[str]:
    settings = get_llm_settings()
    provider = settings["provider"]
    url = _build_url(settings)
    prompt = render_prompt(business)
    headers = _build_headers(settings)

    print(
        f"[LLM] {provider} model={settings['model']} base={settings['base_url']}",
        flush=True,
    )
    if provider == "minimax" and settings.get("api_mode") == "native":
        if not settings.get("group_id"):
            print("[LLM] 提示: native 模式建议配置 MINIMAX_GROUP_ID", flush=True)
    avoid_n = len(collect_avoid_domains())
    if avoid_n:
        print(
            f"[LLM] 避让列表 {avoid_n} 个（blocked_domains.txt + 缓存不可注册）",
            flush=True,
        )
    print(f"[LLM] 业务描述: {business.strip()}", flush=True)

    response = httpx.post(
        url,
        headers=headers,
        json=_build_payload(settings, prompt),
        timeout=180.0,
    )

    try:
        payload = response.json()
    except Exception:
        response.raise_for_status()
        raise

    if response.status_code >= 400:
        detail = payload if isinstance(payload, dict) else response.text
        _raise_http_error(response, detail, settings)

    content = _extract_content(payload, settings=settings)
    domains = parse_domain_list(content)
    print(f"[LLM] 生成完成，共 {len(domains)} 个域名", flush=True)
    return domains
