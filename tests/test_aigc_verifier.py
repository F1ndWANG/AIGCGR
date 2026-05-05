from __future__ import annotations

from types import SimpleNamespace

from app.aigc_verifier import verify_generated_content
from app import product_providers
from app.product_providers import AigcProductProvider


def test_verifier_flags_forbidden_aigc_product_claims() -> None:
    result = verify_generated_content(
        text="高蛋白代餐 SKU123，现货库存充足，点击 https://shop.example 下单有折扣。",
        source="aigc",
        data_type="aigc-product-need",
        provider="aigc-generated",
    )

    assert result.passed is False
    assert result.realness_score <= 0.28
    assert result.hallucination_risk >= 0.82
    assert {"purchase_link", "inventory_claim", "discount_claim", "sku_claim"}.issubset(set(result.forbidden_claims))


def test_verifier_marks_amap_poi_as_provider_grounded() -> None:
    result = verify_generated_content(
        text="来自高德地点数据的餐厅，地址由 Provider 返回。",
        source="amap",
        data_type="real-poi",
        provider="amap",
    )

    assert result.passed is True
    assert result.label == "provider_grounded"
    assert result.realness_score > 0.9
    assert result.hallucination_risk < 0.1


def test_aigc_product_provider_filters_forbidden_claims_in_strict_mode(monkeypatch) -> None:
    monkeypatch.setattr(product_providers, "settings", SimpleNamespace(strict_real_data=True, llm_api_key="test"))
    monkeypatch.setattr(
        product_providers,
        "generate_product_ideas",
        lambda **_: [
            {
                "name": "Protein kit SKU-1",
                "category": "food",
                "price": 99,
                "tags": ["protein"],
                "reason": "现货库存充足",
                "purchase_hint": "点击 https://shop.example 下单有折扣",
            }
        ],
    )

    products = AigcProductProvider().search(keyword="protein", budget=100, tags=["protein"], limit=5)

    assert products == []
