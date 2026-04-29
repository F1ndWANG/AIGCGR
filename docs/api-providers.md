# LifeRec API 清单与获取方式

LifeRec 当前以真实动态数据为主：高德提供地点、天气、路线；OpenAI-compatible LLM 提供 AIGC 策略和商品需求生成。本地 JSON 只作为开发兜底，设置 `STRICT_REAL_DATA=true` 后不会用于补推荐结果。

## 1. 项目内部 API

启动后端：

```powershell
cd backend
uvicorn app.main:app --reload --port 8000
```

| API | 数据来源 | 用途 |
|---|---|---|
| `GET /api/health` | 内部 | 后端健康检查 |
| `GET /api/dataset/summary` | 本地文件统计 | 查看开发样例数据规模 |
| `GET /api/providers/capabilities` | 配置状态 | 查看高德、LLM、严格真实数据模式 |
| `POST /api/recommend` | 高德 + LLM + 用户输入 | 统一生活推荐入口 |
| `POST /api/context/nearby` | 高德周边搜索 | 查询附近餐厅、景点、服务 |
| `POST /api/context/places/search` | 高德关键词搜索 | 按城市/关键词查询地点 |
| `GET /api/context/geocode/reverse` | 高德逆地理编码 | 经纬度转地址和 adcode |
| `GET /api/context/weather` | 高德天气 | 查询实时天气 |
| `POST /api/context/route/walking` | 高德步行路线 | 查询步行距离、耗时和步骤 |
| `POST /api/context/products/search` | AIGC | 生成商品需求清单 |
| `POST /api/aigc/brief` | LLM | 生成推荐策略摘要 |
| `POST /api/feedback` | SQLite 运行时数据 | 保存用户反馈 |
| `GET /api/feedback/summary` | SQLite 运行时数据 | 查看反馈画像 |

## 2. 高德开放平台 API

### 项目使用能力

| 能力 | 高德接口 | 用途 |
|---|---|---|
| 周边搜索 | Place Around | 附近餐厅、附近景点 |
| 关键词搜索 | Place Text | 按城市搜索景点、餐厅 |
| 逆地理编码 | Regeo | 经纬度转城市、区县、adcode |
| 天气查询 | WeatherInfo | 饮食、旅行、出行上下文 |
| 步行路线 | Direction Walking | 推荐卡片里的真实步行距离和耗时 |

### 获取方式

1. 打开 https://lbs.amap.com/
2. 注册或登录开发者账号。
3. 创建应用。
4. 创建 `Web服务` Key。
5. 写入 `.env`：

```text
AMAP_API_KEY=你的高德Web服务Key
```

## 3. LLM API

### 项目使用能力

| 能力 | 用途 |
|---|---|
| 推荐策略摘要 | `/api/aigc/brief` 和 `/api/recommend` |
| 商品需求清单 | `/api/context/products/search` |
| 生活方案解释 | 推荐结果中的 AIGC 摘要 |

### 配置

```text
LLM_API_KEY=你的LLMKey
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-flash
PRODUCT_PROVIDER=aigc
```

`LLM_BASE_URL` 支持 DeepSeek、OpenAI 或其他 OpenAI-compatible 服务。

## 4. 浏览器定位 API

前端通过 `navigator.geolocation.getCurrentPosition()` 获取用户授权位置，然后把经纬度传给后端。该能力不需要申请 Key，但需要用户授权，线上部署通常需要 HTTPS。

对应文件：

- `frontend/app.js`
- `frontend/index.html`

## 5. 商品能力说明

项目当前不接入淘宝、京东、拼多多。原因是这些平台的开放能力、审核和合规要求不稳定，且当前开源 MVP 的目标是验证 AIGC + 生成式推荐的生活决策链路。

当前商品输出是：

- 应该购买的商品类型。
- 预算参考。
- 选择标准。
- 使用场景。
- 购买前检查项。

当前商品输出不是：

- 真实 SKU。
- 实时库存。
- 实时优惠。
- 真实购买链接。

## 6. 严格真实数据模式

推荐在 `.env` 开启：

```text
STRICT_REAL_DATA=true
PROVIDER_CACHE_TTL_SECONDS=300
```

开启后：

- 餐厅和景点没有高德结果时返回空推荐，不使用本地样例补结果。
- 商品没有 LLM 结果时返回空推荐，不使用本地商品样例补结果。
- AIGC 调用失败时说明失败，不用模板伪装真实 LLM 输出。

关闭后：

- 本地 JSON 可作为开发兜底，便于无 Key 演示完整链路。

## 7. 用户反馈 API

反馈数据来自用户真实行为，默认写入 `runtime/liferec.sqlite3`。它只影响排序，不会生成虚假地点、天气、路线或商品。

支持动作：

- `like`：喜欢。
- `dislike`：不喜欢。
- `save`：收藏。
- `plan`：加入计划。
- `skip`：跳过。

## 8. 数据来源边界

- `source=amap`：真实高德数据。
- `source=aigc`：LLM 生成建议，不是外部实时事实。
- `source=sample-data`：本地开发样例，不应作为生产真实数据。
- 高德 POI 不提供完整菜单，因此菜品建议是健康选择原则，不代表餐厅真实菜单。
- Provider 缓存不保存 API Key；缓存内容只用于减少重复请求。

## 9. 参考文档

- 高德 Web 服务 API：https://lbs.amap.com/api/webservice/summary
- 高德地点搜索：https://lbs.amap.com/api/webservice/guide/api/search
- 高德天气查询：https://lbs.amap.com/api/webservice/guide/api/weatherinfo
- 高德路径规划：https://lbs.amap.com/api/webservice/guide/api/direction
- MDN Geolocation：https://developer.mozilla.org/en-US/docs/Web/API/Geolocation/getCurrentPosition
