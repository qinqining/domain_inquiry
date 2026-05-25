"""域名查询缓存与 LLM 避让列表。"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.aliyun_checker import (
    AVAIL_LABELS,
    DomainCheckResult,
    check_domains,
    dry_run_check,
)
from src.config import ROOT_DIR

CACHE_PATH = ROOT_DIR / "data" / "domain_cache.json"
BLOCKED_PATH = ROOT_DIR / "data" / "blocked_domains.txt"

# 仅「不可注册」走缓存跳过 API；可注册结果不用于跳过查询
UNAVAILABLE_FOR_CACHE = {"0", "-3"}
DEFAULT_UNAVAILABLE_TTL_DAYS = 14
MAX_AVOID_IN_PROMPT = 80


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(value: str) -> datetime | None:
    if not value:
        return None
    try:
        text = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def load_cache() -> dict[str, dict]:
    if not CACHE_PATH.exists():
        return {}
    try:
        data = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k).lower(): v for k, v in data.items() if isinstance(v, dict)}


def save_cache(cache: dict[str, dict]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def clear_cache(*, remove_file: bool = True) -> None:
    """清空查询缓存文件。"""
    if CACHE_PATH.exists():
        CACHE_PATH.unlink()
    elif not remove_file:
        save_cache({})


def load_blocked_domains() -> list[str]:
    if not BLOCKED_PATH.exists():
        return []
    domains: list[str] = []
    seen: set[str] = set()
    for line in BLOCKED_PATH.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        name = text.split("#", 1)[0].strip().lower()
        if name and name not in seen:
            seen.add(name)
            domains.append(name)
    return domains


def _is_cache_fresh(entry: dict, *, ttl_days: int) -> bool:
    checked_at = _parse_iso(str(entry.get("checked_at", "")))
    if not checked_at:
        return False
    return _utc_now() - checked_at < timedelta(days=ttl_days)


def should_use_cached_unavailable(
    domain: str, cache: dict[str, dict], *, ttl_days: int
) -> bool:
    entry = cache.get(domain.lower())
    if not entry:
        return False
    avail = str(entry.get("avail", ""))
    if avail not in UNAVAILABLE_FOR_CACHE:
        return False
    return _is_cache_fresh(entry, ttl_days=ttl_days)


def result_from_cache(domain: str, entry: dict) -> DomainCheckResult:
    avail = str(entry.get("avail", "0"))
    label = AVAIL_LABELS.get(avail, f"未知({avail})")
    return DomainCheckResult(
        domain=domain.lower(),
        avail=avail,
        avail_label=f"{label}（缓存）",
        premium=entry.get("premium"),
        price=entry.get("price"),
        reason=str(entry.get("reason") or ""),
        raw=entry.get("raw") if isinstance(entry.get("raw"), dict) else {},
        from_cache=True,
    )


def update_cache_from_results(
    cache: dict[str, dict], results: list[DomainCheckResult]
) -> None:
    for r in results:
        if r.from_cache:
            continue
        cache[r.domain.lower()] = {
            "avail": r.avail,
            "avail_label": r.avail_label,
            "premium": r.premium,
            "price": r.price,
            "reason": r.reason,
            "checked_at": _utc_now().isoformat(),
        }


def collect_avoid_domains(*, max_count: int = MAX_AVOID_IN_PROMPT) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []

    def add(name: str) -> None:
        key = name.strip().lower()
        if not key or key in seen:
            return
        seen.add(key)
        ordered.append(key)

    for name in load_blocked_domains():
        add(name)
    cache = load_cache()
    cached_unavail = [
        (d, e)
        for d, e in cache.items()
        if str(e.get("avail", "")) in UNAVAILABLE_FOR_CACHE
    ]
    cached_unavail.sort(
        key=lambda x: str(x[1].get("checked_at", "")),
        reverse=True,
    )
    for domain, _ in cached_unavail:
        add(domain)
        if len(ordered) >= max_count:
            break
    return ordered[:max_count]


def format_avoid_domains_for_prompt() -> str:
    names = collect_avoid_domains()
    if not names:
        return "（无）"
    return ", ".join(names)


def check_domains_with_cache(
    domains: list[str],
    *,
    use_cache: bool = True,
    cache_ttl_days: int = DEFAULT_UNAVAILABLE_TTL_DAYS,
    update_cache: bool = True,
    dry_run: bool = False,
    **check_kwargs,
) -> list[DomainCheckResult]:
    cache = load_cache() if use_cache and not dry_run else {}
    to_query: list[str] = []
    cached_results: dict[str, DomainCheckResult] = {}
    verbose = check_kwargs.get("verbose", True)

    for domain in domains:
        key = domain.lower()
        if use_cache and not dry_run and should_use_cached_unavailable(
            key, cache, ttl_days=cache_ttl_days
        ):
            entry = cache[key]
            cached_results[key] = result_from_cache(key, entry)
            if verbose:
                print(
                    f"[缓存] 跳过 API: {format_result_line_cached(cached_results[key])}",
                    flush=True,
                )
        else:
            to_query.append(key)

    api_results: list[DomainCheckResult] = []
    if to_query:
        if dry_run:
            api_results = dry_run_check(to_query, **check_kwargs)
        else:
            if verbose and cached_results:
                print(
                    f"[缓存] 命中 {len(cached_results)} 个不可注册，"
                    f"待 API 查询 {len(to_query)} 个",
                    flush=True,
                )
            api_results = check_domains(to_query, **check_kwargs)
            if update_cache and use_cache:
                update_cache_from_results(cache, api_results)
                save_cache(cache)
    elif verbose and cached_results:
        print(
            f"[缓存] 全部 {len(cached_results)} 个均命中缓存，未调用阿里云 API",
            flush=True,
        )

    api_by_domain = {r.domain.lower(): r for r in api_results}
    merged: list[DomainCheckResult] = []
    for domain in domains:
        key = domain.lower()
        if key in cached_results:
            merged.append(cached_results[key])
        else:
            merged.append(api_by_domain[key])

    return merged


def format_result_line_cached(result: DomainCheckResult) -> str:
    extra = result.reason or "-"
    return f"{result.domain} -> {result.avail_label} [Avail={result.avail}] ({extra})"
