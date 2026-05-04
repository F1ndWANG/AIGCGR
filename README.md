# LifeRec: AIGC + 生成式推荐生活推荐系统

LifeRec 是一个开源 AI 生活推荐系统原型，目标是把“我今天该吃什么、买什么、去哪儿、怎么安排”这类自然语言需求，转化为可执行、可解释、可持续学习的个性化生活方案。

项目结合 AIGC、生成式推荐、动态位置、真实生活服务 API、运行时用户记忆、计划反馈学习和真实性防护，覆盖健康饮食、附近餐厅、AIGC 商品需求清单、旅行规划和每日生活简报等场景。

当前定位：`v0.2` 可运行 MVP。它不是静态 Demo，而是具备真实 Provider、SQLite 运行时数据、算法追踪、Life State Vector、可执行性重排、计划感知排序、AIGC 真实性防护和自动化测试的完整实验项目。

## 需求分析

明确用户需求：

- 用户希望用自然语言描述生活需求，例如“不想吃饭”“附近有什么健康餐厅”“帮我做购物清单”“周末去哪玩”。
- 系统需要结合当前位置、预算、饮食记录、生活状态、长期偏好、反馈、计划和真实 Provider 数据生成推荐。
- 推荐结果不能只是聊天文本，还要能转化为行动计划、路线、商品需求、餐厅选择和后续反馈。
- AIGC 可以生成解释和商品需求，但不能虚构真实餐厅、菜单、SKU、库存、折扣、购买链接或实时价格。

可行性研究：

- 地点、天气、路线使用高德 Web 服务 API，保证外部生活服务数据可追溯。
- 商品部分不依赖淘宝、京东、拼多多，采用 AIGC 生成“商品需求清单”，并明确不代表真实交易信息。
- 用户记忆使用 SQLite 保存，适合本地运行、实验迭代和后续迁移到 PostgreSQL。
- 推荐算法采用可逐步扩展的模块化设计，便于后续做论文、实验和开源演进。

需求规格说明：

- 必须支持饮食、餐厅、购物、旅行四类核心场景。
- 必须支持多用户 `user_id` 隔离。
- 必须支持真实运行时记忆：饮食、生活状态、偏好、反馈、计划、推荐历史。
- 必须返回可解释结果：评分、证据链、数据来源、扣分项、执行成本和真实性风险。
- 必须提供测试、安全扫描和 `.env` 密钥隔离。

## 系统设计

概要设计：

```text
Frontend
  -> FastAPI Backend
  -> Intent Parser
  -> Runtime User Context
  -> Life State Vector
  -> Provider Layer: Amap + OpenAI-compatible LLM
  -> Candidate Generation
  -> Multi-objective Ranking
  -> Execution / Plan / Realness Reranking
  -> Recommendation Cards + Plan + Feedback
```

模块划分：

| 模块 | 说明 |
|---|---|
| `backend/app/main.py` | FastAPI 路由入口 |
| `backend/app/recommender.py` | 推荐主链路、意图识别、候选生成和排序 |
| `backend/app/life_state.py` | Life State Vector 用户状态编码 |
| `backend/app/execution.py` | ExecutionCostScorer，可执行性评分 |
| `backend/app/plan_ranker.py` | PlanAwareRanker，计划感知排序 |
| `backend/app/aigc_verifier.py` | AIGCVerifier，真实性与幻觉风险校验 |
| `backend/app/product_providers.py` | AIGC 商品需求生成与本地 fallback |
| `backend/app/providers.py` | 高德地点、天气、路线 Provider |
| `backend/app/storage.py` | SQLite 运行时记忆和缓存 |
| `frontend/` | 原生 HTML/CSS/JavaScript Web MVP |
| `tests/` | pytest 自动化测试 |

详细设计：

- `RecommendationTrace`：记录 ranker、评分公式、数据源、证据、扣分项和置信度。
- `LifeStateSnapshot`：把饮食、生活状态、偏好、反馈、计划、推荐历史编码为动态用户状态。
- `ExecutionScore`：融合距离、预算、路线时间、天气、复杂度和数据风险，计算可执行性。
- `PlanSignal`：用 active/done/canceled 计划做重复抑制、完成偏好增强和取消偏好惩罚。
- `RealnessCheck`：区分 `provider_grounded`、`aigc_product_need`、`development_sample`，检测购买链接、SKU、库存、折扣、实时价格等禁止声明。
- `ScoreBreakdown`：包含 preference、health、budget、distance、context、execution、realness 等分项。

## 编码实现

后端实现：

- 使用 Python + FastAPI + Pydantic 构建 API。
- 使用 SQLite 保存运行时用户数据，默认路径为 `runtime/liferec.sqlite3`。
- 使用高德 Web 服务 API 获取 POI、逆地理编码、天气和步行路线。
- 使用 OpenAI-compatible LLM，默认模型配置为 `deepseek-v4-flash`。
- 使用 AIGC 商品需求生成，不声称真实 SKU、库存、折扣或购买链接。

前端实现：

- 原生 HTML/CSS/JavaScript，无复杂构建链。
- 支持 API Base URL 切换、用户 ID 切换、当前位置获取。
- 支持饮食记录、生活状态记录、长期偏好保存、计划管理、推荐历史、每日简报和用户记忆导出。
- 推荐卡片展示算法追踪、可执行性评分、计划感知信号和真实性风险。

主要 API：

| API | 用途 |
|---|---|
| `GET /api/health` | 健康检查和存储状态 |
| `GET /api/providers/capabilities` | 查看高德、AIGC、商品、缓存 Provider 状态 |
| `POST /api/recommend` | 统一生活推荐入口 |
| `POST /api/recommend/refresh` | 基于 `request_id` 换一批 |
| `GET /api/user/life-state` | 动态生活状态向量 |
| `GET /api/user/context` | 聚合用户上下文 |
| `GET /api/user/export` | 导出完整用户记忆 JSON |
| `GET /api/user/daily-brief` | 生成 AIGC 今日生活简报 |
| `POST /api/user/meals` / `GET /api/user/meals` | 饮食记录写入和查询 |
| `POST /api/user/wellness` / `GET /api/user/wellness` | 生活状态写入和查询 |
| `PUT /api/user/preferences` / `GET /api/user/preferences` | 长期偏好保存和查询 |
| `POST /api/user/plans` / `PATCH /api/user/plans/{plan_id}` | 计划创建和状态更新 |
| `GET /api/user/plans/export` / `GET /api/user/plans/export.ics` | 计划 JSON / ICS 导出 |
| `POST /api/context/nearby` | 附近地点查询 |
| `POST /api/context/places/search` | 城市或关键词地点搜索 |
| `GET /api/context/weather` | 实时天气 |
| `POST /api/context/route/walking` | 步行路线 |
| `POST /api/context/products/search` | AIGC 商品需求清单 |

本地运行：

```powershell
Copy-Item .env.example .env
.\scripts\dev_backend.ps1
.\scripts\dev_frontend.ps1
```

推荐环境变量：

```env
AMAP_API_KEY=你的高德Web服务Key
LLM_API_KEY=你的DeepSeek或OpenAI-compatible Key
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-flash
PRODUCT_PROVIDER=aigc
STRICT_REAL_DATA=true
PROVIDER_CACHE_TTL_SECONDS=300
CORS_ALLOW_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
```

`.env` 已被 `.gitignore` 忽略，不应提交到 GitHub。

## 软件测试

测试目标：

- 发现并修复推荐链路、用户记忆、Provider 边界、AIGC 生成和前端交互中的错误。
- 覆盖单元测试、集成测试、系统级接口测试和安全检查。
- 确保严格真实数据模式下不会把本地样例伪装成真实推荐。

测试命令：

```powershell
python -m pip install -r backend/requirements-dev.txt
python -m pytest
python -m compileall backend
node --check frontend/app.js
.\scripts\check_public_safety.ps1
```

推荐评估脚本：

```powershell
python scripts\evaluate_recommendations.py --request request.json --response response.json
```

当前测试覆盖：

- API 健康检查、CORS、Provider 能力。
- 饮食、生活状态、偏好、反馈、计划、推荐历史和用户记忆导出。
- Life State Vector 动态编码。
- RecommendationTrace 证据链。
- ExecutionCostScorer 可执行性评分。
- PlanAwareRanker 计划感知排序。
- AIGCVerifier 禁止声明检测和严格模式过滤。
- 预算、距离、真实数据、健康冲突、低可执行性和幻觉风险评估。
- 前端 JavaScript 语法检查。
- 公开密钥扫描。

## 运行维护

交付后维护重点：

- 纠错维护：修复 Provider 异常、AIGC 输出越界、推荐排序异常和前端交互问题。
- 适应性维护：支持新的地图服务、LLM Provider、数据库和部署环境。
- 完善性维护：继续扩展算法模块和产品功能。
- 安全维护：持续避免提交 `.env`、API Key、运行时缓存和用户隐私数据。

真实数据边界：

- 地点、天气、路线来自高德 Provider。
- 商品建议是 AIGC 商品需求生成，不是实时交易信息。
- 高德 POI 不提供完整菜单，菜品建议是健康选择原则，不代表餐厅真实菜单。
- LifeRec 只提供一般生活方式建议，不提供医疗诊断、治疗建议或处方建议。

后续路线：

- Phase 6：反馈权重学习，引入时间衰减和用户级标签权重。
- Phase 7：Bandit 探索，平衡稳定偏好和新选项。
- 数据库迁移：从 SQLite 迁移到 PostgreSQL。
- 用户体系：增加认证、权限隔离和多用户部署能力。
- Provider 扩展：增加驾车、公交、骑行、日历、运动、睡眠和菜单数据。

## 文档索引

| 文档 | 内容 |
|---|---|
| [项目总览](docs/project-summary.md) | 当前架构、功能和边界 |
| [架构设计](docs/architecture.md) | 系统模块和数据流 |
| [动态 API 规划](docs/dynamic-api-plan.md) | 动态推荐和 Provider 方案 |
| [API 清单与获取方式](docs/api-providers.md) | 所需 API 和申请方式 |
| [API 设置指南](docs/api-setup-guide.md) | `.env` 配置和验证方法 |
| [AIGC 模块设计](docs/aigc-integration.md) | LLM 调用和 Prompt 边界 |
| [算法创新路线](docs/algorithm-innovation-roadmap.md) | Life State、可执行推荐、计划反馈和真实性防护 |
| [真实数据策略](docs/real-data-policy.md) | 数据真实性和 fallback 规则 |
| [反馈闭环](docs/feedback-loop.md) | 用户反馈、饮食记录和重排 |
| [部署与运行](docs/deployment.md) | 本地和 Docker 运行 |
| [测试与质量检查](docs/testing.md) | 自动化测试和评估 |
| [Roadmap](docs/roadmap.md) | 后续方向 |
