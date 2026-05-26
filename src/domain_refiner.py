"""步骤4（可选）：对可注册域名给出修改建议与变体。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from src.config import ROOT_DIR
from src.deepseek_client import chat_completion
from src.domain_cache import collect_avoid_domains, load_cache, should_use_cached_unavailable
from src.domain_parser import parse_json_array
from src.llm_client import (
    format_avoid_domains_for_prompt,
    load_company_context,
    load_naming_prefs,
)

DEFAULT_UNAVAILABLE_TTL_DAYS = 14
MAX_VARIANTS = 15


@dataclass
class VariantSuggestion:
    original: str
    issue: str
    advice: str


@dataclass
class DomainVariant:
    domain: str
    based_on: str
    note: str


@dataclass
class VariantPlan:
    suggestions: list[VariantSuggestion] = field(default_factory=list)
    variants: list[DomainVariant] = field(default_factory=list)


PROMPT_PATH = ROOT_DIR / "prompts" / "domain_refiner.txt"


def _render_prompt(
    business: str,
    available_rows: list[dict[str, Any]],
    *,
    failed_variants: list[str] | None = None,
) -> str:
    template = PROMPT_PATH.read_text(encoding="utf-8")
    company = load_company_context()
    prefs = load_naming_prefs()
    company_block = company if company else "（未配置）"
    if prefs:
        company_block = f"{company_block}\n\n{prefs}"
    avoid = format_avoid_domains_for_prompt()
    if failed_variants:
        company_block += (
            "\n\n【上轮变体已全部不可注册，请勿重复类似造词】\n"
            + ", ".join(failed_variants)
            + "\n请用更虚构、更独特的 coined 名，避免 sol/max/tec/ton/cad 类词典替换。"
        )
    return (
        template.replace("{{business}}", business.strip())
        .replace("{{company_context}}", company_block)
        .replace("{{avoid_domains}}", avoid)
        .replace(
            "{{available_json}}",
            json.dumps(available_rows, ensure_ascii=False, indent=2),
        )
    )


def filter_variants_for_query(
    variants: list[DomainVariant],
    *,
    cache_ttl_days: int = DEFAULT_UNAVAILABLE_TTL_DAYS,
) -> tuple[list[DomainVariant], list[DomainVariant]]:
    """去掉已在缓存中确认为不可注册的变体，少打 API。"""
    cache = load_cache()
    avoid = set(collect_avoid_domains())
    ok: list[DomainVariant] = []
    skipped: list[DomainVariant] = []
    for v in variants:
        key = v.domain.lower()
        if key in avoid:
            skipped.append(v)
            continue
        if should_use_cached_unavailable(key, cache, ttl_days=cache_ttl_days):
            skipped.append(v)
            continue
        ok.append(v)
    if skipped:
        print(
            f"[步骤4] 避让/缓存预筛跳过 {len(skipped)} 个已知不可注册变体",
            flush=True,
        )
    return ok, skipped


def _parse_variant_plan(content: str, original_domains: set[str]) -> VariantPlan:
    text = content.strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        items = parse_json_array(text)
        data = {"suggestions": [], "variants": items}

    suggestions: list[VariantSuggestion] = []
    for item in data.get("suggestions") or []:
        if not isinstance(item, dict):
            continue
        suggestions.append(
            VariantSuggestion(
                original=str(item.get("original", "")).lower(),
                issue=str(item.get("issue", "")),
                advice=str(item.get("advice", "")),
            )
        )

    seen: set[str] = set()
    variants: list[DomainVariant] = []
    for item in data.get("variants") or []:
        if not isinstance(item, dict):
            continue
        domain = str(item.get("domain", "")).strip().lower()
        if not domain or domain in seen or domain in original_domains:
            continue
        seen.add(domain)
        variants.append(
            DomainVariant(
                domain=domain,
                based_on=str(item.get("based_on", "")).lower(),
                note=str(item.get("note", item.get("improvement_note", ""))),
            )
        )

    if not variants:
        raise ValueError("LLM 未返回有效变体域名")
    return VariantPlan(suggestions=suggestions, variants=variants)


def suggest_variants(
    business: str,
    available_rows: list[dict[str, Any]],
    *,
    failed_variants: list[str] | None = None,
    temperature: float = 0.75,
) -> VariantPlan:
    if not available_rows:
        raise ValueError("没有可注册域名，无法生成变体")

    original_domains = {r["domain"].lower() for r in available_rows}
    label = "DeepSeek·终稿变体"
    if failed_variants:
        label = "DeepSeek·终稿变体(重试)"
    print(
        f"\n[步骤4·可选] LLM 修改建议与变体（基于 {len(available_rows)} 个可注册域名）…",
        flush=True,
    )
    content = chat_completion(
        _render_prompt(business, available_rows, failed_variants=failed_variants),
        temperature=temperature,
        label=label,
    )
    plan = _parse_variant_plan(content, original_domains)
    plan.variants, _ = filter_variants_for_query(plan.variants)
    if not plan.variants:
        raise ValueError("变体经避让/缓存预筛后为空，请重试或保留首轮可注册域名")
    print(
        f"[步骤4] 建议 {len(plan.suggestions)} 条，待查变体 {len(plan.variants)} 个",
        flush=True,
    )
    return plan


def variant_domain_names(plan: VariantPlan) -> list[str]:
    return [v.domain for v in plan.variants]
