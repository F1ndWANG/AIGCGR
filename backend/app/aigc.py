from __future__ import annotations

import json
import re

import httpx

from .config import settings


def build_life_brief(message: str, scenario: str, health_tags: list[str]) -> tuple[str, str]:
    """Generate a life recommendation brief through an LLM or deterministic fallback."""
    prompt_slot = "prompts/life_brief.md"
    if settings.llm_api_key:
        return _call_openai_compatible_llm(message, scenario, health_tags), prompt_slot

    if settings.strict_real_data:
        return (
            "AIGC Provider 未配置，严格真实数据模式下不会使用本地模板生成策略。",
            prompt_slot,
        )

    if scenario == "travel":
        return (
            "AIGC 生成策略：先压缩行程强度，再围绕预算、距离和兴趣生成两段式旅行计划。",
            prompt_slot,
        )
    if scenario == "shopping":
        return (
            "AIGC 生成策略：把生活目标转成可购买清单，并解释每个商品如何降低执行成本。",
            prompt_slot,
        )
    health = "、".join(health_tags) if health_tags else "近期状态均衡"
    return (
        f"AIGC 生成策略：结合“{message}”和健康标签“{health}”，生成饮食方向、餐厅选择和菜品理由。",
        prompt_slot,
    )


def _call_openai_compatible_llm(message: str, scenario: str, health_tags: list[str]) -> str:
    base_url = (settings.llm_base_url or "https://api.deepseek.com").rstrip("/")
    endpoint = f"{base_url}/chat/completions"
    payload = {
        "model": settings.llm_model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是 LifeRec 的 AIGC 生活推荐策略生成器。"
                    "请基于用户需求、场景和健康标签生成简洁、可执行的推荐策略。"
                    "不要虚构具体餐厅、价格或地点；不要提供医疗诊断。"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "message": message,
                        "scenario": scenario,
                        "health_tags": health_tags,
                    },
                    ensure_ascii=False,
                ),
            },
        ],
        "temperature": 0.3,
        "max_tokens": 220,
    }

    try:
        with httpx.Client(timeout=20) as client:
            response = client.post(
                endpoint,
                headers={
                    "Authorization": f"Bearer {settings.llm_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()
            return content or _fallback_brief(message, scenario, health_tags)
    except Exception as exc:
        if settings.strict_real_data:
            return f"LLM 调用失败：{type(exc).__name__}。严格真实数据模式下未使用本地模板。"
        return f"{_fallback_brief(message, scenario, health_tags)}（LLM 调用失败，已回退到本地模板：{type(exc).__name__}）"


def _fallback_brief(message: str, scenario: str, health_tags: list[str]) -> str:
    health = "、".join(health_tags) if health_tags else "近期状态均衡"
    if scenario == "travel":
        return "AIGC 生成策略：按预算、距离、天气和行程强度组织旅行推荐。"
    if scenario == "shopping":
        return "AIGC 生成策略：把生活目标转成商品清单，并解释每个商品的使用场景。"
    return f"AIGC 生成策略：结合“{message}”和健康标签“{health}”，生成饮食方向、餐厅选择和菜品理由。"


def generate_product_ideas(keyword: str, scenario: str, budget: float | None, tags: list[str], limit: int) -> list[dict[str, object]]:
    if settings.llm_api_key:
        ideas = _call_product_idea_llm(keyword, scenario, budget, tags, limit)
        if ideas:
            return ideas[:limit]
    if settings.strict_real_data:
        return []
    return _fallback_product_ideas(keyword, scenario, budget, tags, limit)


def _call_product_idea_llm(keyword: str, scenario: str, budget: float | None, tags: list[str], limit: int) -> list[dict[str, object]]:
    base_url = (settings.llm_base_url or "https://api.deepseek.com").rstrip("/")
    endpoint = f"{base_url}/chat/completions"
    payload = {
        "model": settings.llm_model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是 LifeRec 的 AIGC 商品需求生成器。"
                    "请生成用户应该购买的商品类型，不要虚构具体电商链接、库存或实时价格。"
                    "只输出 JSON 数组，每项包含 name, category, price, tags, reason, purchase_hint。"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "keyword": keyword,
                        "scenario": scenario,
                        "budget": budget,
                        "tags": tags,
                        "limit": limit,
                    },
                    ensure_ascii=False,
                ),
            },
        ],
        "temperature": 0.35,
        "max_tokens": 700,
    }

    try:
        with httpx.Client(timeout=25) as client:
            response = client.post(
                endpoint,
                headers={
                    "Authorization": f"Bearer {settings.llm_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            return _parse_product_json(content)
    except Exception:
        return []


def _parse_product_json(content: str) -> list[dict[str, object]]:
    text = content.strip()
    match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if match:
        text = match.group(1).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def _fallback_product_ideas(keyword: str, scenario: str, budget: float | None, tags: list[str], limit: int) -> list[dict[str, object]]:
    base_tags = tags or [keyword]
    if "旅行" in keyword or scenario == "travel":
        ideas = [
            ("短途旅行收纳包", "旅行装备", 69, ["旅行", "收纳"], "让两天行程更容易整理随身物品。", "选择轻量、防水、分区清晰的款式。"),
            ("便携雨伞", "出行装备", 39, ["天气", "旅行"], "适合不确定天气下的短途出行。", "优先选择轻便和抗风结构。"),
            ("充电宝", "数码配件", 99, ["旅行", "通勤"], "保证导航、拍照和联系不断电。", "注意容量、重量和是否支持快充。"),
        ]
    else:
        ideas = [
            ("即食鸡胸肉组合", "健康食材", 59, ["高蛋白", "低油", *base_tags], "补充蛋白质，降低临时点重油外卖的概率。", "选择配料表简单、钠含量较低的款式。"),
            ("无糖酸奶", "健康食材", 42, ["低糖", "早餐", *base_tags], "适合作为早餐或加餐，减少高糖饮品摄入。", "优先看蛋白质含量和是否无添加糖。"),
            ("燕麦片", "主食", 36, ["粗粮", "饱腹", *base_tags], "适合做稳定早餐，提升饱腹感。", "选择原味燕麦，避免高糖混合款。"),
            ("分隔餐盒", "生活工具", 49, ["备餐", "规律饮食"], "帮助提前规划餐食，降低随意进食。", "选择密封性好、可微波加热的材质。"),
            ("小型空气炸锅", "厨房电器", 239, ["少油", "厨房"], "用更少油完成简单烹饪。", "注意容量、清洗难度和厨房空间。"),
        ]
    if budget:
        ideas = [item for item in ideas if item[2] <= budget or item[2] <= budget * 1.2]
    return [
        {
            "name": name,
            "category": category,
            "price": price,
            "tags": item_tags,
            "reason": reason,
            "purchase_hint": hint,
        }
        for name, category, price, item_tags, reason, hint in ideas[:limit]
    ]
