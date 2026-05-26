"""最终 list 终端/报告行格式（含读音、释义、来源词）。"""

from __future__ import annotations

from typing import Any


def format_final_list_item(item: dict[str, Any], *, index: int | None = None) -> str:
    prefix = f"  {index}. " if index is not None else ""
    based = f" ← {item['based_on']}" if item.get("based_on") else ""
    pron = (item.get("pronunciation") or "").strip()
    meaning = (item.get("meaning_zh") or item.get("note") or "").strip()
    src = ", ".join(item.get("source_words") or [])
    parts = [f"{prefix}{item['domain']}{based}"]
    if pron:
        parts.append(f"[{pron}]")
    if meaning:
        parts.append(meaning)
    line = "  ".join(parts)
    if src:
        line += f"  ← {src}"
    return line
