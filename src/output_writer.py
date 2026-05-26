from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.final_list_format import format_final_list_item
from src.config import ROOT_DIR
from src.domain_reviewer import DomainReview

OUTPUT_ROOT = ROOT_DIR / "output"


@dataclass
class TaskOutputPaths:
    task_dir: Path
    meta: Path
    candidates: Path
    reviews: Path
    availability: Path
    report_md: Path
    report_json: Path


def create_task_dir(business: str) -> TaskOutputPaths:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_hint = "".join(c for c in business[:12] if c.isalnum() or c in "-_") or "task"
    task_dir = OUTPUT_ROOT / f"{stamp}_{safe_hint}"
    task_dir.mkdir(parents=True, exist_ok=True)
    return TaskOutputPaths(
        task_dir=task_dir,
        meta=task_dir / "meta.json",
        candidates=task_dir / "01_candidates.json",
        reviews=task_dir / "02_reviews.json",
        availability=task_dir / "03_availability.json",
        report_md=task_dir / "report.md",
        report_json=task_dir / "report.json",
    )


def _check_to_dict(r: DomainCheckResult) -> dict[str, Any]:
    return {
        "domain": r.domain,
        "avail": r.avail,
        "avail_label": r.avail_label,
        "premium": r.premium,
        "price": r.price,
        "reason": r.reason,
        "from_cache": r.from_cache,
    }


def _build_final_rows(
    reviews: list[DomainReview],
    checks: list[DomainCheckResult],
) -> list[dict[str, Any]]:
    check_map = {c.domain: c for c in checks}
    rows: list[dict[str, Any]] = []

    for review in reviews:
        if not review.pass_:
            continue
        check = check_map.get(review.domain)
        row = {
            **review.to_dict(),
            "avail": check.avail if check else "",
            "avail_label": check.avail_label if check else "未查询",
            "available": bool(check and check.avail == "1"),
            "premium": check.premium if check else None,
            "price": check.price if check else None,
            "check_reason": check.reason if check else "",
            "from_cache": check.from_cache if check else False,
        }
        rows.append(row)

    available = [r for r in rows if r.get("available")]
    unavailable = [r for r in rows if not r.get("available")]
    available.sort(
        key=lambda x: x.get("memorability", 0) + x.get("pronounceability", 0),
        reverse=True,
    )
    return available + unavailable


def _render_report_md(
    business: str,
    task_dir: Path,
    candidates: list[str],
    reviews: list[DomainReview],
    final_rows: list[dict[str, Any]],
) -> str:
    passed = [r for r in reviews if r.pass_]
    available = [r for r in final_rows if r.get("available")]

    lines = [
        "# 域名生成报告",
        "",
        f"- 业务描述：{business}",
        f"- 任务目录：`{task_dir.name}`",
        f"- 生成候选：{len(candidates)} 个",
        f"- 自检通过：{len(passed)} 个",
        f"- 可注册：{len(available)} 个",
        "",
        "## 推荐注册（自检通过且可注册）",
        "",
    ]

    if available:
        lines.append(
            "| 域名 | 读音 | 寓意 | 来源词 | 四维均分 |"
        )
        lines.append("| --- | --- | --- | --- | --- |")
        for r in available:
            avg = (
                r["readability"]
                + r["pronounceability"]
                + r["memorability"]
                + r["uniqueness"]
            ) / 4
            src = ", ".join(r.get("source_words") or [])
            lines.append(
                f"| {r['domain']} | {r.get('pronunciation', '')} | "
                f"{r.get('meaning_zh', '')} | {src} | {avg:.1f} |"
            )
    else:
        lines.append("（暂无）")

    lines.extend(["", "## 自检通过但不可注册", ""])
    blocked = [r for r in final_rows if r.get("pass") and not r.get("available")]
    if blocked:
        for r in blocked:
            lines.append(
                f"- **{r['domain']}** — {r.get('avail_label', '')} "
                f"（{r.get('check_reason') or '-'}）"
            )
    else:
        lines.append("（暂无）")

    lines.extend(["", "## 自检淘汰", ""])
    rejected = [r for r in reviews if not r.pass_]
    if rejected:
        for r in rejected[:30]:
            reason = r.reject_reason or "未通过四维门槛"
            lines.append(f"- {r.domain} — {reason}")
        if len(rejected) > 30:
            lines.append(f"- … 另有 {len(rejected) - 30} 个")
    else:
        lines.append("（无）")

    lines.extend(["", "## 全部候选", "", ", ".join(candidates)])
    return "\n".join(lines) + "\n"


def save_task_output(
    *,
    business: str,
    candidates: list[str],
    reviews: list[DomainReview],
    checks: list[DomainCheckResult],
) -> TaskOutputPaths:
    paths = create_task_dir(business)
    final_rows = _build_final_rows(reviews, checks)

    meta = {
        "business": business,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task_dir": str(paths.task_dir),
        "counts": {
            "candidates": len(candidates),
            "review_passed": sum(1 for r in reviews if r.pass_),
            "available": sum(1 for r in final_rows if r.get("available")),
        },
    }

    paths.meta.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    paths.candidates.write_text(
        json.dumps(candidates, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    paths.reviews.write_text(
        json.dumps([r.to_dict() for r in reviews], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    paths.availability.write_text(
        json.dumps([_check_to_dict(c) for c in checks], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    report = {
        "meta": meta,
        "recommend_available": [r for r in final_rows if r.get("available")],
        "all_passed_with_check": final_rows,
    }
    paths.report_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    paths.report_md.write_text(
        _render_report_md(business, paths.task_dir, candidates, reviews, final_rows),
        encoding="utf-8",
    )

    latest = OUTPUT_ROOT / "latest"
    latest.mkdir(parents=True, exist_ok=True)
    for name in ("report.md", "report.json", "meta.json"):
        src = paths.task_dir / name
        if src.exists():
            shutil.copy2(src, latest / name)
    (latest / "task_path.txt").write_text(str(paths.task_dir), encoding="utf-8")

    print(f"[输出] 已保存至 {paths.task_dir}", flush=True)
    print(f"[输出] 最新副本 output/latest/report.md", flush=True)
    return paths


def save_variants_output(
    *,
    task_dir: Path,
    plan: Any,
    variant_checks: list[DomainCheckResult],
) -> None:
    """步骤4 输出：修改建议 + 变体 + 阿里云结果（不再做第二轮自检）。"""
    task_dir.mkdir(parents=True, exist_ok=True)
    suggestions = [
        {"original": s.original, "issue": s.issue, "advice": s.advice}
        for s in plan.suggestions
    ]
    variants = [
        {"domain": v.domain, "based_on": v.based_on, "note": v.note}
        for v in plan.variants
    ]
    (task_dir / "04_variant_suggestions.json").write_text(
        json.dumps(suggestions, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (task_dir / "05_variants.json").write_text(
        json.dumps(variants, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (task_dir / "06_variant_availability.json").write_text(
        json.dumps([_check_to_dict(c) for c in variant_checks], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def save_final_list(task_dir: Path, final_list: list[dict[str, Any]]) -> None:
    path = task_dir / "07_final_list.json"
    path.write_text(json.dumps(final_list, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# 最终推荐 list（含释义）", ""]
    for index, item in enumerate(final_list, start=1):
        tag = item.get("stage", "")
        lines.append(f"{index}. {format_final_list_item(item).strip()}  ({tag})")
    md = task_dir / "final_list.md"
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    latest = OUTPUT_ROOT / "latest"
    latest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(md, latest / "final_list.md")
    print(f"[输出] 最终 list → {md}", flush=True)
