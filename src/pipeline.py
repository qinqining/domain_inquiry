"""
一条流水线：
  1 LLM 生成 → 2 LLM 自检 → 3 阿里云
  → 4 [可选] LLM 修改建议+变体 → 阿里云查变体 → 最终 list
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from src.domain_cache import check_domains_with_cache
from src.domain_refiner import DomainVariant, VariantPlan, suggest_variants, variant_domain_names
from src.domain_reviewer import DomainReview, passed_domains, review_domains
from src.llm_client import generate_domains
from src.final_list_format import format_final_list_item
from src.output_writer import TaskOutputPaths, save_task_output, save_variants_output


@dataclass
class FullPipelineResult:
    business: str
    candidates: list[str]
    reviews: list[DomainReview]
    checks: list[Any]
    output: TaskOutputPaths | None = None
    # 步骤4（可选）
    variant_plan: VariantPlan | None = None
    variant_checks: list[Any] = field(default_factory=list)
    final_list: list[dict[str, Any]] = field(default_factory=list)

    def available_rows(self) -> list[dict[str, Any]]:
        review_map = {r.domain: r for r in self.reviews}
        rows: list[dict[str, Any]] = []
        for c in self.checks:
            if c.avail != "1":
                continue
            r = review_map.get(c.domain)
            rows.append(
                {
                    "domain": c.domain,
                    "pronunciation": r.pronunciation if r else "",
                    "meaning_zh": r.meaning_zh if r else "",
                    "source_words": r.source_words if r else [],
                    "stage": "首轮可注册",
                }
            )
        return rows

    def _build_final_list(self) -> list[dict[str, Any]]:
        review_map = {r.domain: r for r in self.reviews}
        items: list[dict[str, Any]] = []
        seen: set[str] = set()

        if self.variant_plan and self.variant_checks:
            variant_map = {v.domain: v for v in self.variant_plan.variants}
            for c in self.variant_checks:
                if c.avail != "1":
                    continue
                v = variant_map.get(c.domain)
                if not v or c.domain in seen:
                    continue
                seen.add(c.domain)
                base = review_map.get(v.based_on)
                items.append(
                    {
                        "domain": c.domain,
                        "based_on": v.based_on,
                        "pronunciation": base.pronunciation if base else "",
                        "meaning_zh": v.note,
                        "source_words": list(base.source_words) if base else [],
                        "note": v.note,
                        "stage": "变体可注册（推荐优先）",
                        "kind": "variant",
                    }
                )

        for row in self.available_rows():
            if row["domain"] in seen:
                continue
            seen.add(row["domain"])
            items.append(
                {
                    "domain": row["domain"],
                    "based_on": "",
                    "pronunciation": row.get("pronunciation", ""),
                    "meaning_zh": row.get("meaning_zh", ""),
                    "source_words": list(row.get("source_words") or []),
                    "note": row.get("meaning_zh", ""),
                    "stage": "首轮可注册",
                    "kind": "original",
                }
            )
        return items


def _aliyun_check(
    domains: list[str],
    check_args: SimpleNamespace,
    *,
    label: str,
) -> list[Any]:
    if not domains:
        return []
    print(f"\n[步骤3/4·阿里云] {label}，共 {len(domains)} 个\n", flush=True)
    limit = getattr(check_args, "limit", 0) or 0
    if limit > 0:
        domains = domains[:limit]
    return check_domains_with_cache(
        domains,
        use_cache=not check_args.no_cache,
        cache_ttl_days=check_args.cache_ttl_days,
        update_cache=not check_args.dry_run,
        dry_run=check_args.dry_run,
        lang=check_args.lang,
        verbose=not check_args.quiet,
    )


def run_variants_on_result(
    result: FullPipelineResult,
    check_args: SimpleNamespace,
    *,
    save_output: bool = True,
) -> FullPipelineResult:
    """在同一条流水线上追加步骤4，不重复 1~3。"""
    available_rows = result.available_rows()
    if not available_rows:
        print("[步骤4·可选] 无可注册域名，跳过。", flush=True)
        return result

    plan = suggest_variants(result.business, available_rows)
    variant_names = variant_domain_names(plan)
    variant_checks = _aliyun_check(
        variant_names, check_args, label="步骤4·查询变体域名"
    )

    variant_avail = [c for c in variant_checks if c.avail == "1"]
    if not variant_avail and variant_checks:
        failed = [c.domain for c in variant_checks]
        print(
            f"\n[步骤4] 变体 {len(failed)} 个均不可注册，自动重试一轮（更虚构造词）…",
            flush=True,
        )
        try:
            plan_retry = suggest_variants(
                result.business,
                available_rows,
                failed_variants=failed,
                temperature=0.85,
            )
            retry_names = variant_domain_names(plan_retry)
            retry_checks = _aliyun_check(
                retry_names, check_args, label="步骤4·重试变体"
            )
            plan = plan_retry
            variant_checks = variant_checks + retry_checks
        except ValueError as exc:
            print(f"[步骤4] 重试跳过: {exc}", flush=True)

    result.variant_plan = plan
    result.variant_checks = variant_checks

    if save_output and result.output:
        save_variants_output(
            task_dir=result.output.task_dir,
            plan=plan,
            variant_checks=variant_checks,
        )

    result.final_list = result._build_final_list()
    if save_output and result.output and result.final_list:
        from src.output_writer import save_final_list

        save_final_list(result.output.task_dir, result.final_list)

    return result


def run_full_pipeline(
    business: str,
    check_args: SimpleNamespace,
    *,
    save_output: bool = True,
    run_variants: bool = False,
) -> FullPipelineResult:
    print("[步骤1] LLM 生成候选…", flush=True)
    candidates = generate_domains(business)

    print("[步骤2] LLM 自检…", flush=True)
    reviews = review_domains(business, candidates)
    to_check = passed_domains(reviews)

    checks = _aliyun_check(to_check, check_args, label="步骤3·查询自检通过域名")

    result = FullPipelineResult(
        business=business,
        candidates=candidates,
        reviews=reviews,
        checks=checks,
    )

    output_paths = None
    if save_output:
        output_paths = save_task_output(
            business=business,
            candidates=candidates,
            reviews=reviews,
            checks=checks,
        )
    result.output = output_paths

    if run_variants:
        result = run_variants_on_result(result, check_args, save_output=save_output)
    else:
        result.final_list = result._build_final_list()
        if save_output and output_paths and result.final_list:
            from src.output_writer import save_final_list

            save_final_list(output_paths.task_dir, result.final_list)

    return result


def print_pipeline_summary(result: FullPipelineResult) -> None:
    review_map = {r.domain: r for r in result.reviews}
    available_checks = [c for c in result.checks if c.avail == "1"]

    print("\n── 步骤1~3 完成 ──", flush=True)
    print("\n【首轮 · 可注册 · 带释义】", flush=True)
    if not available_checks:
        print("  （暂无）", flush=True)
    for index, c in enumerate(available_checks, start=1):
        r = review_map.get(c.domain)
        if r:
            src = ", ".join(r.source_words)
            print(
                f"  {index}. {c.domain}  [{r.pronunciation}]  "
                f"{r.meaning_zh}  ← {src}",
                flush=True,
            )
        else:
            print(f"  {index}. {c.domain}", flush=True)

    if result.variant_plan:
        print("\n── 步骤4（可选）已执行 ──", flush=True)
        if result.variant_plan.suggestions:
            print("\n【修改建议】", flush=True)
            for s in result.variant_plan.suggestions:
                print(f"  · {s.original}：{s.issue} → {s.advice}", flush=True)
        print("\n【变体候选】", flush=True)
        for v in result.variant_plan.variants:
            print(f"  · {v.domain} ← {v.based_on}（{v.note}）", flush=True)

        variant_avail = [c for c in result.variant_checks if c.avail == "1"]
        print("\n【变体 · 可注册】", flush=True)
        if variant_avail:
            for index, c in enumerate(variant_avail, start=1):
                print(f"  {index}. {c.domain}", flush=True)
        else:
            print("  （暂无）", flush=True)
            print(
                "  说明: 短 .com 好读音变体极难抢注；可保留上方「首轮可注册」或换行业再跑一轮。",
                flush=True,
            )

    print("\n【最终 list · 带释义】", flush=True)
    if result.final_list:
        for index, item in enumerate(result.final_list, start=1):
            tag = item.get("stage", "")
            print(f"{format_final_list_item(item, index=index)}  ({tag})", flush=True)
        print(
            "\nlist: " + ", ".join(i["domain"] for i in result.final_list),
            flush=True,
        )
    else:
        print("  （暂无）", flush=True)
        print("\nlist: （无）", flush=True)

    if result.output:
        print(f"\n报告目录: {result.output.task_dir}", flush=True)
        print(f"最新报告副本: output/latest/report.md", flush=True)
    if not result.variant_plan and result.available_rows():
        print(
            "\n提示: 步骤4 可选 — 对可注册域名生成修改建议与变体后再查阿里云。",
            flush=True,
        )


# 兼容旧 import
PipelineResult = FullPipelineResult
run_pipeline = run_full_pipeline
