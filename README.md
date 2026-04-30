# LifeRec

LifeRec 是一个开源的 AI 生活推荐系统原型，结合 AIGC、用户画像、动态位置、规则排序和生成式推荐思想，为饮食、餐厅、购物和旅行场景生成个性化生活方案。

当前版本是 `v0.2` MVP，重点跑通完整链路：

```text
自然语言需求 -> 意图识别 -> 用户画像/生活状态 -> 动态上下文 -> 候选生成 -> 推荐排序 -> AIGC 解释 -> 行动方案
```

## 核心能力

- 饮食状态分析：根据近期饮食记录识别高油、高盐、蔬菜不足、蛋白不足等状态。
- 真实饮食记录：用户可通过 API 或前端记录一餐，后续推荐自动读取运行时历史。
- 健康饮食推荐：结合口味、预算、忌口和近期饮食状态，生成今日饮食建议。
- 餐厅与菜品推荐：根据当前位置、预算和健康目标推荐附近餐厅与具体菜品。
- AIGC 商品生成：不依赖电商平台 API，直接生成商品需求清单、预算参考和购买提示。
- 旅行规划推荐：根据出发地、预算、时间和偏好推荐目的地与行程。
- 解释型推荐：每个推荐结果输出匹配标签、推荐理由和行动计划。
- 反馈学习：用户可以对推荐结果点赞、不喜欢或加入计划，后续推荐会参考真实反馈重排。
- 换一批推荐：基于当前 `request_id` 排除上一批结果并生成替代推荐。

## Provider 策略

- 地点服务：采用高德地图 Web 服务 API，本地 JSON 仅作开发 fallback。
- 商品服务：采用 AIGC 生成商品需求清单，本地 `data/products.json` 仅作开发 fallback。
- AIGC：采用 OpenAI-compatible LLM 接口，当前默认模型为 `deepseek-v4-flash`。
- 天气与路线：采用高德天气 API 和高德步行路径规划 API。
- 真实数据模式：`STRICT_REAL_DATA=true` 时不使用本地餐厅、景点、商品样例补结果。
- Provider 缓存：高德响应写入本地 SQLite 缓存，缓存 key 不保存 API Key。
- 推荐评估：提供规则化评估脚本，检查预算、距离、真实数据来源和换一批排除约束。

## 技术栈

- 后端：Python, FastAPI, Pydantic, httpx
- 推荐核心：用户画像 + 规则排序 + 动态距离 + AIGC 解释
- 前端：原生 HTML/CSS/JavaScript
- 数据：高德真实 POI/天气/路线 + LLM 生成内容；本地 JSON 仅作开发兜底
- 存储：SQLite 运行时数据库保存推荐历史、用户反馈、饮食记录和 Provider 缓存，默认位于 `runtime/`
- 工程化：Docker, pytest, GitHub Actions, PowerShell 启动脚本

## 快速开始

### 1. 配置环境变量

复制模板：

```powershell
Copy-Item .env.example .env
```

最小配置：

```env
AMAP_API_KEY=你的高德Web服务Key
LLM_API_KEY=你的DeepSeekKey
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-flash
PRODUCT_PROVIDER=aigc
STRICT_REAL_DATA=true
PROVIDER_CACHE_TTL_SECONDS=300
```

`.env` 已被 `.gitignore` 忽略，不会提交到 Git。

### 2. 启动后端

```powershell
.\scripts\dev_backend.ps1
```

后端地址：

```text
http://127.0.0.1:8000
```

API 文档：

```text
http://127.0.0.1:8000/docs
```

### 3. 启动前端

```powershell
.\scripts\dev_frontend.ps1
```

前端地址：

```text
http://127.0.0.1:5173
```

### 4. Docker 启动

```powershell
docker compose up --build
```

### 5. 测试与安全检查

```powershell
python -m pip install -r backend/requirements-dev.txt
python -m pytest
python -m compileall backend
.\scripts\check_public_safety.ps1
```

推荐评估脚本：

```powershell
python scripts\evaluate_recommendations.py --request request.json --response response.json
```

## 示例输入

```text
我今天不想吃饭，最近吃得有点油腻，学校附近有什么健康一点的？
```

```text
我想开始健康饮食，帮我推荐一份购物清单。
```

```text
我周末从南京出发玩两天，预算 1000，不想太累。
```

## 主要 API

| API | 用途 |
|---|---|
| `GET /api/health` | 后端健康检查 |
| `GET /api/providers/capabilities` | 查看高德、AIGC、商品生成等 Provider 状态 |
| `POST /api/recommend` | 统一生活推荐入口 |
| `POST /api/recommend/refresh` | 基于 `request_id` 排除上一批结果并换一批 |
| `POST /api/context/nearby` | 附近地点查询，高德优先 |
| `POST /api/context/places/search` | 城市或关键词地点搜索，高德优先 |
| `GET /api/context/geocode/reverse` | 高德逆地理编码 |
| `GET /api/context/weather` | 高德实时天气 |
| `POST /api/context/route/walking` | 高德步行路径规划 |
| `POST /api/context/products/search` | AIGC 商品需求清单生成 |
| `POST /api/aigc/brief` | AIGC 推荐策略摘要 |
| `POST /api/feedback` | 保存用户对推荐项的真实反馈 |
| `GET /api/feedback/summary` | 查看用户反馈画像摘要 |
| `POST /api/user/meals` | 保存用户真实饮食记录 |
| `GET /api/user/meals` | 查看用户近期饮食记录和标签 |

## 项目结构

```text
LifeRec
├── backend/              FastAPI 服务与推荐核心
├── data/                 示例餐厅、菜品、商品、景点和用户数据
├── docs/                 架构、API、数据、安全和实施文档
├── frontend/             Web MVP
├── AIGC+GR.md            AIGC 与生成式推荐分析文档
└── README.md
```

## 文档入口

- [项目总览](docs/project-summary.md)
- [架构设计](docs/architecture.md)
- [实施计划](docs/implementation-plan.md)
- [动态 API 实现规划](docs/dynamic-api-plan.md)
- [API 清单与获取方式](docs/api-providers.md)
- [API 设置指南](docs/api-setup-guide.md)
- [AIGC 模块设计](docs/aigc-integration.md)
- [真实数据策略](docs/real-data-policy.md)
- [反馈闭环](docs/feedback-loop.md)
- [部署与运行](docs/deployment.md)
- [测试与质量检查](docs/testing.md)
- [Roadmap](docs/roadmap.md)
- [数据说明](docs/data-schema.md)
- [隐私与安全策略](docs/privacy-and-safety.md)

## 当前状态

已完成：

- 本地示例数据和开源项目骨架。
- 饮食、餐厅、购物、旅行推荐闭环。
- 高德地点、逆地理编码、天气和步行路线 Provider。
- 浏览器当前位置动态推荐。
- DeepSeek/OpenAI-compatible AIGC 调用。
- AIGC 商品生成，不依赖淘宝、京东、拼多多。
- `STRICT_REAL_DATA` 严格真实数据模式。
- SQLite 反馈闭环，支持喜欢、不喜欢、加入计划影响后续排序。
- SQLite 真实饮食记录，推荐接口在未传 `recent_meal_tags` 时自动读取。
- `request_id` 驱动的“换一批”替代推荐。
- SQLite Provider 缓存，降低高德重复调用。
- Docker、CI、pytest、公开密钥扫描脚本。
- 推荐评估脚本，覆盖预算、距离、数据来源、排除项和健康冲突。

待扩展：

- 驾车、公交、骑行等更多路线规划。
- 向量检索与语义召回。
- 用户手动商品链接或商品 Feed 导入。

## 安全说明

LifeRec 当前只提供一般生活方式建议，不提供医疗诊断、治疗建议或处方建议。用户存在持续身体不适、慢性病、过敏风险或特殊人群情况时，应咨询专业医生或营养师。
