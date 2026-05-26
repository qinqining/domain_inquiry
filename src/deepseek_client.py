"""DeepSeek Chat Completions 封装。"""

from __future__ import annotations

import httpx

from src.config import get_llm_settings


def chat_completion(
    prompt: str,
    *,
    temperature: float = 0.8,
    timeout: float = 180.0,
    label: str = "DeepSeek",
) -> str:
    settings = get_llm_settings()
    url = f"{settings['base_url']}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings['api_key']}",
        "Content-Type": "application/json",
    }
    body = {
        "model": settings["model"],
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
    }

    print(
        f"[LLM] {label} model={settings['model']} base={settings['base_url']}",
        flush=True,
    )

    response = httpx.post(url, headers=headers, json=body, timeout=timeout)

    try:
        payload = response.json()
    except Exception:
        response.raise_for_status()
        raise

    if response.status_code >= 400:
        detail = payload if isinstance(payload, dict) else response.text
        if isinstance(payload, dict):
            err = payload.get("error") or {}
            if isinstance(err, dict) and err.get("message"):
                raise ValueError(f"DeepSeek 返回错误: {err.get('message')}")
        raise ValueError(f"DeepSeek HTTP {response.status_code}: {detail}")

    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        message = choices[0].get("message") or {}
        content = message.get("content")
        if content:
            return str(content)

    raise ValueError(f"无法从 DeepSeek 响应中解析文本: {payload}")
