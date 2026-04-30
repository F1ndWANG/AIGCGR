# LifeRec 项目总览

## 1. 项目定位

LifeRec 是一个面向日常生活场景的 AI 推荐系统。它把用户输入、动态位置、真实生活服务 API、推荐排序和 AIGC 解释结合起来，为饮食、餐厅、购物和旅行生成可执行方案。

当前核心场景：

- 健康饮食建议。
- 附近餐厅推荐。
- AIGC 商品需求清单。
- 本地和城市旅行规划。

## 2. 当前架构

```text
Frontend
  ↓
FastAPI
  ↓
Intent Parser
  ↓
Runtime User Context
  ↓
Provider Layer: Amap + LLM
  ↓
Recommendation Ranker
  ↓
AIGC Explainer
  ↓
Recommendation Response
```

## 3. Provider 策略

| 能力 | 当前方案 | 严格模式下 fallback |
|---|---|---|
| 地点 | 高德地图 Web 服务 API | 无结果则返回空 |
| 逆地理编码 | 高德逆地理编码 API | 无结果则标记 unavailable |
| 天气 | 高德天气 API + SQLite 缓存 | 无结果则不生成天气建议 |
| 路线 | 高德步行路径规划 API + SQLite 缓存 | 无结果则不生成路线字段 |
| AIGC | DeepSeek/OpenAI-compatible API | 失败时说明失败 |
| 商品 | AIGC 商品需求生成器 | 无结果则返回空 |

## 4. 已实现功能

### 后端 API

- `GET /api/health`
- `GET /api/providers/capabilities`
- `POST /api/recommend`
- `POST /api/recommend/refresh`
- `POST /api/context/nearby`
- `POST /api/context/places/search`
- `GET /api/context/geocode/reverse`
- `GET /api/context/weather`
- `POST /api/context/route/walking`
- `POST /api/context/products/search`
- `POST /api/aigc/brief`
- `POST /api/feedback`
- `GET /api/feedback/summary`
- `GET /api/user/context`
- `POST /api/user/meals`
- `GET /api/user/meals`

### 推荐核心

- 规则式意图识别。
- 用户本次输入的口味、忌口、近期饮食标签和旅行偏好。
- 用户运行时饮食记录会自动沉淀为近期饮食标签。
- 高德真实 POI 候选生成。
- 高德天气进入推荐上下文和行动计划。
- 高德步行路线进入推荐卡片。
- 健康、预算、距离、偏好、上下文综合排序。
- AIGC 策略摘要和商品需求生成。
- `STRICT_REAL_DATA` 严格真实数据模式。
- SQLite 运行时推荐历史、用户反馈和饮食记录。
- SQLite Provider 响应缓存，降低外部 API 重复调用。
- 用户反馈会影响后续推荐排序。
- `request_id` 驱动的“换一批”替代推荐。
- 推荐评估脚本可检查预算、距离、数据来源、排除项和健康冲突。

### 前端

- 生活需求输入。
- 场景切换。
- 快捷 Prompt。
- 浏览器当前位置按钮。
- 本次请求的饮食、口味、忌口和旅行偏好输入。
- 快速记录一餐，并回填近期饮食标签。
- 用户记忆摘要：饮食记录、正反馈、负反馈和近期标签。
- Provider 能力状态展示。
- 推荐卡片、健康上下文、AIGC 摘要和行动计划展示。

## 5. 数据文件

| 文件 | 说明 |
|---|---|
| `data/users.json` | 开发样例用户画像 |
| `data/restaurants.json` | 开发样例餐厅 |
| `data/dishes.json` | 开发样例菜品 |
| `data/products.json` | 开发样例商品 fallback |
| `data/destinations.json` | 开发样例旅行目的地 |

这些文件只用于本地开发和无 Key 演示。开启 `STRICT_REAL_DATA=true` 后，推荐主链路不会用它们补餐厅、景点或商品结果。

## 6. 关键代码文件

| 文件 | 说明 |
|---|---|
| `backend/app/main.py` | FastAPI 路由入口 |
| `backend/app/models.py` | 请求和响应模型 |
| `backend/app/recommender.py` | 推荐核心逻辑 |
| `backend/app/providers.py` | 高德地点、天气、路线 Provider |
| `backend/app/product_providers.py` | AIGC 商品生成与本地开发 fallback |
| `backend/app/aigc.py` | DeepSeek/OpenAI-compatible 调用 |
| `backend/app/config.py` | `.env` 配置读取 |
| `backend/app/storage.py` | SQLite 推荐历史、反馈、饮食记录和缓存存储 |
| `backend/app/cache.py` | Provider 响应缓存 |
| `frontend/app.js` | 前端交互逻辑 |

## 7. 运行方式

后端：

```powershell
cd backend
uvicorn app.main:app --reload --port 8000
```

前端：

```powershell
cd frontend
python -m http.server 5173
```

访问：

```text
http://127.0.0.1:5173
```

## 8. 当前边界

- 高德 POI 提供餐厅和地点基础信息，但不提供完整菜单。
- 菜品建议是健康选择原则，不代表某餐厅真实菜单。
- AIGC 商品模块不提供真实 SKU、库存、折扣或购买链接。
- 当前使用 SQLite 保存运行时推荐历史、饮食记录和反馈；生产环境可替换为 PostgreSQL。

## 9. 下一步建议

1. 增加 PostgreSQL 适配：替换 SQLite，支持多人部署。
2. 扩展路线能力：驾车、公交、骑行。
3. 增加更多用户数据导入：运动、睡眠、日历和长期偏好。
