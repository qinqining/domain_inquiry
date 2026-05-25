import json
import re
from typing import Any


def _strip_markdown_fences(text: str) -> str:
    cleaned = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return cleaned


def parse_domain_list(raw: str) -> list[str]:
    """解析 LLM 返回的 JSON 数组，兼容带 markdown 代码块的情况。"""
    text = _strip_markdown_fences(raw)
    data: Any = json.loads(text)
    if not isinstance(data, list):
        raise ValueError("LLM 输出必须是 JSON 数组")

    domains: list[str] = []
    seen: set[str] = set()
    for item in data:
        if not isinstance(item, str):
            raise ValueError(f"数组元素必须是字符串: {item!r}")
        name = item.strip().lower()
        if not name:
            continue
        if name in seen:
            continue
        seen.add(name)
        domains.append(name)
    if not domains:
        raise ValueError("未解析到任何域名")
    return domains
