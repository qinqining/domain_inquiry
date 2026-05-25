#!/usr/bin/env python3
"""域名生成 + 阿里云可注册性查询 CLI。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.domain_cache import (
    BLOCKED_PATH,
    CACHE_PATH,
    DEFAULT_UNAVAILABLE_TTL_DAYS,
    check_domains_with_cache,
    clear_cache,
)
from src.domain_parser import parse_domain_list
from src.llm_client import generate_domains


def _read_text(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def _print_results(results: list, *, as_json: bool) -> None:
    if as_json:
        payload = [
            {
                "domain": r.domain,
                "avail": r.avail,
                "avail_label": r.avail_label,
                "premium": r.premium,
                "price": r.price,
                "reason": r.reason,
                "from_cache": r.from_cache,
            }
            for r in results
        ]
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    cached_n = sum(1 for r in results if r.from_cache)
    available = [r for r in results if r.avail == "1"]
    api_n = len(results) - cached_n
    print(
        f"\n共 {len(results)} 个（API 查询 {api_n}，缓存命中 {cached_n}），"
        f"可注册 {len(available)} 个\n"
    )
    print(f"{'域名':<32} {'状态':<16} {'溢价':<6} {'价格':<8} 原因")
    print("-" * 84)
    for r in results:
        premium = "" if r.premium is None else ("是" if r.premium else "否")
        price = "" if r.price is None else str(r.price)
        reason = r.reason or "-"
        mark = " *" if r.avail == "1" else ""
        print(
            f"{r.domain:<32} {r.avail_label:<16} {premium:<6} {price:<8} {reason}{mark}"
        )
    if available:
        print("\n可注册列表:")
        for r in available:
            print(f"  - {r.domain}")


def _add_cache_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="禁用查询缓存，全部走阿里云 API",
    )
    parser.add_argument(
        "--cache-ttl-days",
        type=int,
        default=DEFAULT_UNAVAILABLE_TTL_DAYS,
        metavar="N",
        help=f"不可注册结果缓存天数（默认 {DEFAULT_UNAVAILABLE_TTL_DAYS}）",
    )


def _run_domain_check(
    domains: list[str],
    args: argparse.Namespace,
) -> list:
    use_cache = not args.no_cache
    verbose = not args.quiet
    return check_domains_with_cache(
        domains,
        use_cache=use_cache,
        cache_ttl_days=args.cache_ttl_days,
        update_cache=use_cache and not args.dry_run,
        dry_run=args.dry_run,
        lang=args.lang,
        verbose=verbose,
    )


def cmd_parse(args: argparse.Namespace) -> int:
    raw = _read_text(args.input)
    domains = parse_domain_list(raw)
    print(json.dumps(domains, ensure_ascii=False, indent=2))
    print(f"\n解析成功: {len(domains)} 个域名", file=sys.stderr)
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    if args.input:
        raw = _read_text(args.input)
        domains = parse_domain_list(raw)
    elif args.domains:
        domains = [d.strip().lower() for d in args.domains if d.strip()]
    else:
        print("请指定 --input 或 --domains", file=sys.stderr)
        return 1

    if args.limit and args.limit > 0:
        domains = domains[: args.limit]

    results = _run_domain_check(domains, args)
    _print_results(results, as_json=args.json)
    return 0


def cmd_cache_clear(args: argparse.Namespace) -> int:
    clear_cache()
    print(f"已清空查询缓存: {CACHE_PATH}", flush=True)
    if args.reset_blocked:
        BLOCKED_PATH.write_text(
            "# 人工维护：主观否决的域名（每行一个，# 为注释）\n",
            encoding="utf-8",
        )
        print(f"已重置避让列表: {BLOCKED_PATH}", flush=True)
    print("提示: 请用 generate --check 查「本次新生成」的域名，勿用旧的 user_domains.json。", flush=True)
    return 0


def cmd_generate(args: argparse.Namespace) -> int:
    domains = generate_domains(args.business)
    print(json.dumps(domains, ensure_ascii=False, indent=2))
    print(f"\n生成 {len(domains)} 个域名", file=sys.stderr)

    if args.check:
        limit = args.limit if args.limit and args.limit > 0 else len(domains)
        results = _run_domain_check(domains[:limit], args)
        _print_results(results, as_json=args.json)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="AI 域名列表解析 + 阿里云 CheckDomain 可注册查询"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_parse = sub.add_parser("parse", help="仅解析 LLM 输出的 JSON 域名列表")
    p_parse.add_argument(
        "--input", "-i", default="-", help="输入文件路径，- 表示 stdin"
    )
    p_parse.set_defaults(func=cmd_parse)

    p_check = sub.add_parser("check", help="查询域名是否可注册（CheckDomain）")
    p_check.add_argument(
        "--input", "-i", help="LLM JSON 或域名数组文件；不填则用 --domains"
    )
    p_check.add_argument(
        "--domains", "-d", nargs="+", help="直接指定要查询的域名"
    )
    p_check.add_argument(
        "--limit", "-n", type=int, default=0, help="最多查询前 N 个（0=全部）"
    )
    p_check.add_argument(
        "--dry-run",
        action="store_true",
        help="不调用阿里云，不写入缓存",
    )
    p_check.add_argument("--json", action="store_true", help="以 JSON 输出结果")
    p_check.add_argument(
        "--quiet", "-q", action="store_true", help="关闭逐条查询日志"
    )
    p_check.add_argument("--lang", default="zh", choices=["zh", "en"])
    _add_cache_arguments(p_check)
    p_check.set_defaults(func=cmd_check)

    p_gen = sub.add_parser(
        "generate", help="调用 LLM 生成域名（DeepSeek 或 MiniMax，见 .env）"
    )
    p_gen.add_argument("--business", "-b", required=True, help="业务描述")
    p_gen.add_argument(
        "--check", action="store_true", help="生成后立即查询可注册性"
    )
    p_gen.add_argument("--dry-run", action="store_true")
    p_gen.add_argument("--limit", "-n", type=int, default=0)
    p_gen.add_argument("--json", action="store_true")
    p_gen.add_argument(
        "--quiet", "-q", action="store_true", help="关闭逐条查询日志"
    )
    p_gen.add_argument("--lang", default="zh", choices=["zh", "en"])
    _add_cache_arguments(p_gen)
    p_gen.set_defaults(func=cmd_generate)

    p_cache = sub.add_parser("cache", help="管理域名查询缓存")
    p_cache_sub = p_cache.add_subparsers(dest="cache_command", required=True)
    p_clear = p_cache_sub.add_parser("clear", help="清空 domain_cache.json")
    p_clear.add_argument(
        "--reset-blocked",
        action="store_true",
        help="同时重置 blocked_domains.txt 为空白模板",
    )
    p_clear.set_defaults(func=cmd_cache_clear)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except ValueError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"执行失败: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
