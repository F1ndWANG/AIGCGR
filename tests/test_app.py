from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.aigc import _message_text, _parse_product_json
from app import storage
from app.main import app


def test_health_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert "storage" in payload


def test_user_context_endpoint_aggregates_runtime_data(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(storage, "RUNTIME_DIR", tmp_path)
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "liferec-test.sqlite3")

    with TestClient(app) as client:
        meal_response = client.post(
            "/api/user/meals",
            json={
                "user_id": "u-context",
                "meal_name": "炸鸡",
                "tags": ["高油", "蔬菜少"],
            },
        )
        feedback_response = client.post(
            "/api/feedback",
            json={
                "user_id": "u-context",
                "item_id": "poi-1",
                "item_name": "测试餐厅",
                "item_type": "restaurant",
                "action": "like",
                "tags": ["清淡"],
                "source": "amap",
            },
        )
        context_response = client.get("/api/user/context?user_id=u-context&limit=10")

    assert meal_response.status_code == 200
    assert feedback_response.status_code == 200
    assert context_response.status_code == 200
    payload = context_response.json()
    assert payload["recent_meal_tags"] == ["高油", "蔬菜少"]
    assert payload["meals"][0]["meal_name"] == "炸鸡"
    assert payload["feedback"]["positive"]["items"]["测试餐厅"] == 1
    assert payload["storage"]["meal_events"] == 1
    assert payload["context_sources"]["meals"] == "runtime.sqlite.meal_events"


def test_aigc_product_parser_accepts_reasoning_content_and_embedded_json() -> None:
    text = _message_text(
        {
            "content": "",
            "reasoning_content": '说明文字后输出 [{"name":"无糖酸奶","category":"健康食材","price":42,"tags":["低糖"],"reason":"减少糖摄入","purchase_hint":"看配料表"}]',
        }
    )
    products = _parse_product_json(text)

    assert products[0]["name"] == "无糖酸奶"


def test_aigc_product_parser_keeps_complete_items_from_truncated_array() -> None:
    products = _parse_product_json(
        """
        [
          {"name":"即食鸡胸肉","category":"健康食材","price":59,"tags":["高蛋白"],"reason":"补充蛋白","purchase_hint":"看钠含量"},
          {"name":"无糖酸奶","category":"健康食材","price":42,"tags":["低糖"],"reason":"减少糖摄入","purchase_hint":"看配料表"},
          {"name":"未完成"
        """
    )

    assert [item["name"] for item in products] == ["即食鸡胸肉", "无糖酸奶"]
