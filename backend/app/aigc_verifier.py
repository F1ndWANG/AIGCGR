from __future__ import annotations

import re
from typing import Any

from .models import ProductItem, RealnessCheck, RecommendationItem


FORBIDDEN_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("purchase_link", re.compile(r"https?://|www\.|购买链接|下单链接|直达链接|点击购买", re.IGNORECASE)),
    ("inventory_claim", re.compile(r"库存|现货|有货|available\s+now|in\s+stock", re.IGNORECASE)),
    ("discount_claim", re.compile(r"折扣|优惠券|满减|限时|全网最低|包邮|特价|discount|coupon", re.IGNORECASE)),
    ("sku_claim", re.compile(r"\bSKU[-_\w]*|商品编号|货号", re.IGNORECASE)),
    ("realtime_price_claim", re.compile(r"实时价格|当前售价|今日价格|price\s+now", re.IGNORECASE)),
    ("real_menu_claim", re.compile(r"真实菜单|店内菜单|招牌菜真实供应|menu\s+available", re.IGNORECASE)),
]


def verify_product_item(product: ProductItem) -> RealnessCheck:
    text = " ".join(
        [
            product.name,
            product.category or "",
            product.reason or "",
            product.purchase_hint or "",
            " ".join(product.tags),
        ]
    )
    return verify_generated_content(
        text=text,
        source=product.source,
        data_type="aigc-product-need" if product.source == "aigc" else "sample-data",
        provider=product.provider,
    )


def verify_recommendation_item(item: RecommendationItem) -> RealnessCheck:
    meta = item.meta or {}
    text = " ".join(
        [
            item.name,
            item.type,
            " ".join(item.tags),
            " ".join(item.reasons),
            " ".join(item.suggested_items),
        ]
    )
    return verify_generated_content(
        text=text,
        source=str(meta.get("source") or meta.get("provider") or ""),
        data_type=str(meta.get("data_type") or ""),
        provider=str(meta.get("provider") or meta.get("source") or ""),
    )


def apply_realness_checks(items: list[RecommendationItem], *, strict_real_data: bool = False) -> list[RecommendationItem]:
    checked: list[RecommendationItem] = []
    for item in items:
        realness = verify_recommendation_item(item)
        item.realness = realness
        item.score_breakdown.realness = realness.realness_score
        item.meta["realness_score"] = realness.realness_score
        item.meta["hallucination_risk"] = realness.hallucination_risk
        item.trace.evidence.append(f"realness={realness.realness_score}")
        if realness.risk_flags:
            item.trace.penalties.extend([f"realness:{flag}" for flag in realness.risk_flags[:3]])
        if strict_real_data and not realness.passed:
            continue
        checked.append(item)
    return sorted(checked, key=lambda candidate: (candidate.score, candidate.realness.realness_score), reverse=True)


def verify_generated_content(text: str, source: str, data_type: str = "", provider: str = "") -> RealnessCheck:
    forbidden = _forbidden_claims(text)
    label, base_score, base_risk, data_sources, evidence = _source_baseline(source=source, data_type=data_type, provider=provider)
    risk_flags: list[str] = []

    if forbidden:
        risk_flags.append("forbidden_claim_detected")
        base_score = min(base_score, 0.28)
        base_risk = max(base_risk, 0.82)

    if label == "aigc_product_need" and not _has_generated_need_boundary(text):
        risk_flags.append("aigc_boundary_weak")
        base_score = min(base_score, 0.55)
        base_risk = max(base_risk, 0.38)

    if label == "unknown":
        risk_flags.append("source_uncertain")

    return RealnessCheck(
        label=label,
        realness_score=round(base_score, 3),
        hallucination_risk=round(base_risk, 3),
        passed=not forbidden,
        data_sources=data_sources,
        risk_flags=risk_flags,
        forbidden_claims=forbidden,
        evidence=evidence,
    )


def _source_baseline(source: str, data_type: str, provider: str) -> tuple[str, float, float, list[str], list[str]]:
    source_text = " ".join([source, data_type, provider]).lower()
    if "real-poi" in source_text or "amap" in source_text:
        return "provider_grounded", 0.94, 0.06, ["amap.provider"], ["provider_backed=true"]
    if "aigc-product-need" in source_text or source == "aigc":
        return "aigc_product_need", 0.66, 0.26, ["aigc.generated_need"], ["aigc_boundary=product_need_not_sku"]
    if "sample" in source_text or "local-json" in source_text:
        return "development_sample", 0.34, 0.48, ["local.sample_data"], ["sample_data=true"]
    return "unknown", 0.45, 0.55, ["unknown"], ["provider_backed=false"]


def _forbidden_claims(text: str) -> list[str]:
    matched: list[str] = []
    for name, pattern in FORBIDDEN_PATTERNS:
        if pattern.search(text):
            matched.append(name)
    return matched


def _has_generated_need_boundary(text: str) -> bool:
    boundary_terms = ("不代表真实", "购买前", "自行确认", "需求", "品类", "not real", "verify")
    return any(term.lower() in text.lower() for term in boundary_terms)
