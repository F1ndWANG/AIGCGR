# 动态 API 实现规划

LifeRec 当前已经从静态 Demo 升级为真实 Provider 优先的动态生活推荐系统。配置 `AMAP_API_KEY` 后，餐厅、景点、逆地理编码、天气和步行路线都来自高德 Web 服务 API；配置 `LLM_API_KEY` 后，AIGC 策略摘要和商品需求清单来自 OpenAI-compatible LLM。

## 目标链路

```text
浏览器当前位置 / 用户指定城市
  ↓
高德地点、天气、路线 Provider
  ↓
用户近期饮食、偏好、预算、半径
  ↓
动态候选生成与排序
  ↓
AIGC 生成解释和行动计划
```

## 已实现

- `RecommendationRequest` 支持 `latitude`、`longitude`、`radius_km`、预算、口味、忌口、近期饮食标签和旅行偏好。
- 餐厅推荐：有经纬度时优先调用高德周边搜索。
- 旅行推荐：有经纬度时优先调用高德周边景点；有城市时调用高德关键词搜索。
- 天气上下文：推荐接口会通过高德逆地理编码和天气 API 获取当前天气，并写入 `context` 和行动计划。
- 路线信息：真实 POI 推荐会为前几条结果补充高德步行路线距离和预计耗时。
- 商品推荐：不接淘宝、京东、拼多多，默认使用 AIGC 生成商品需求清单，不声称实时 SKU、库存或购买链接。
- 严格真实数据模式：`STRICT_REAL_DATA=true` 时不使用本地 JSON 补餐厅、景点或商品结果。
- 反馈闭环：SQLite 保存用户对推荐结果的真实反馈，并影响后续排序。
- Provider 缓存：高德地点、天气和路线响应写入 SQLite 缓存，缓存 key 不包含 API Key。

## 已实现 API

| API | 数据来源 | 用途 |
|---|---|---|
| `POST /api/recommend` | 高德 + LLM + 用户输入 | 统一生活推荐入口 |
| `POST /api/context/nearby` | 高德周边搜索 | 附近餐厅、景点、服务 |
| `POST /api/context/places/search` | 高德关键词搜索 | 按城市或关键词查地点 |
| `GET /api/context/geocode/reverse` | 高德逆地理编码 | 经纬度转城市、区县、地址 |
| `GET /api/context/weather` | 高德天气 | 当前天气上下文 |
| `POST /api/context/route/walking` | 高德步行路径规划 | 两点间步行距离、耗时和步骤 |
| `POST /api/context/products/search` | AIGC 商品生成 | 商品类型、预算参考、购买提示 |
| `POST /api/aigc/brief` | OpenAI-compatible LLM | 推荐策略摘要 |
| `GET /api/providers/capabilities` | 配置状态 | 查看真实 Provider 是否启用 |
| `POST /api/feedback` | SQLite 运行时数据 | 保存用户反馈 |
| `GET /api/feedback/summary` | SQLite 运行时数据 | 查看反馈画像 |

## 环境变量

```text
AMAP_API_KEY=你的高德Web服务Key
LLM_API_KEY=你的DeepSeek或OpenAI-compatible Key
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-flash
PRODUCT_PROVIDER=aigc
STRICT_REAL_DATA=true
PROVIDER_CACHE_TTL_SECONDS=300
```

## 数据真实性规则

- `source=amap` 表示地点、天气或路线来自高德真实 API。
- `source=aigc` 表示内容由 LLM 生成，只能作为建议或需求清单。
- `source=sample-data` 仅允许开发兜底；严格模式下不应出现。
- 高德 POI 不提供完整菜单，因此菜品建议是健康选择原则，不代表餐厅真实菜单。
- AIGC 不得虚构实时价格、库存、折扣或购买链接。

## 下一步实施顺序

1. 增加“换一个”接口：基于当前 request_id 排除已有推荐并重新生成。
2. 增加 PostgreSQL 适配：替换 SQLite，支持多人部署。
3. 增加更多路线 Provider：驾车、公交、骑行。
4. 增加推荐评估脚本：检查预算、距离、健康约束和数据来源。
