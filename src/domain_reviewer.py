from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from typing import Any

from src.config import ROOT_DIR
from src.deepseek_client import chat_completion
from src.domain_parser import parse_json_array
from src.llm_client import load_company_context, load_naming_prefs

PROMPT_PATH = ROOT_DIR / "prompts" / "domain_reviewer.txt"

DEFAULT_MIN_SCORE = 7.0


def get_min_review_score() -> float:
    raw = os.getenv("REVIEW_MIN_SCORE", str(DEFAULT_MIN_SCORE)).strip()
    try:
        return float(raw)
    except ValueError:
        return DEFAULT_MIN_SCORE


@dataclass
class DomainReview:
    domain: str
    pass_: bool
    tier: str
    pronunciation: str
    syllables: int
    source_words: list[str]
    meaning_zh: str
    readability: float
    pronounceability: float
    memorability: float
    uniqueness: float
    reject_reason: str = ""

    @property
    def pass_label(self) -> str:
        return "通过" if self.pass_ else "淘汰"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["pass"] = self.pass_
        del d["pass_"]
        return d

    @classmethod
    def from_dict(cls, item: dict[str, Any]) -> DomainReview:
        domain = str(item.get("domain", "")).strip().lower()
        if not domain:
            raise ValueError(f"评审项缺少 domain: {item}")

        def score(key: str) -> float:
            try:
                return float(item.get(key, 0))
            except (TypeError, ValueError):
                return 0.0

        source = item.get("source_words") or []
        if isinstance(source, str):
            source = [s.strip() for s in source.split(",") if s.strip()]
        elif not isinstance(source, list):
            source = []

        return cls(
            domain=domain,
            pass_=bool(item.get("pass", False)),
            tier=str(item.get("tier", "reject")),
            pronunciation=str(item.get("pronunciation", "")),
            syllables=int(item.get("syllables", 0) or 0),
            source_words=[str(x) for x in source],
            meaning_zh=str(item.get("meaning_zh", "")),
            readability=score("readability"),
            pronounceability=score("pronounceability"),
            memorability=score("memorability"),
            uniqueness=score("uniqueness"),
            reject_reason=str(item.get("reject_reason", "")),
        )


def _render_reviewer_prompt(business: str, domains: list[str]) -> str:
    template = PROMPT_PATH.read_text(encoding="utf-8")
    company = load_company_context()
    prefs = load_naming_prefs()
    company_block = company if company else "（未配置）"
    if prefs:
        company_block = f"{company_block}\n\n{prefs}"
    domain_json = json.dumps(domains, ensure_ascii=False)
    return (
        template.replace("{{business}}", business.strip())
        .replace("{{company_context}}", company_block)
        .replace("{{domain_list}}", domain_json)
    )


def _apply_score_gate(review: DomainReview, min_score: float) -> DomainReview:
    scores = (
        review.readability,
        review.pronounceability,
        review.memorability,
        review.uniqueness,
    )
    if review.pass_ and any(s < min_score for s in scores):
        review.pass_ = False
        review.tier = "reject"
        if not review.reject_reason:
            review.reject_reason = f"四维分数需均≥{min_score:g}"
    if review.tier == "reject":
        review.pass_ = False
    return review


def review_domains(
    business: str,
    domains: list[str],
    *,
    min_score: float | None = None,
) -> list[DomainReview]:
    if not domains:
        return []

    threshold = min_score if min_score is not None else get_min_review_score()
    prompt = _render_reviewer_prompt(business, domains)
    print(f"[LLM-2] 自检评审 {len(domains)} 个候选…", flush=True)
    content = chat_completion(prompt, temperature=0.3, label="DeepSeek·评审")
    raw_items = parse_json_array(content)

    by_domain: dict[str, DomainReview] = {}
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        review = _apply_score_gate(DomainReview.from_dict(item), threshold)
        by_domain[review.domain] = review

    reviews: list[DomainReview] = []
    for domain in domains:
        key = domain.lower()
        if key in by_domain:
            reviews.append(by_domain[key])
        else:
            reviews.append(
                DomainReview(
                    domain=key,
                    pass_=False,
                    tier="reject",
                    pronunciation="",
                    syllables=0,
                    source_words=[],
                    meaning_zh="",
                    readability=0,
                    pronounceability=0,
                    memorability=0,
                    uniqueness=0,
                    reject_reason="LLM 未返回该域名评审",
                )
            )

    passed = sum(1 for r in reviews if r.pass_)
    print(f"[LLM-2] 自检完成：通过 {passed} / {len(reviews)}", flush=True)
    return reviews


def passed_domains(reviews: list[DomainReview]) -> list[str]:
    return [r.domain for r in reviews if r.pass_]
