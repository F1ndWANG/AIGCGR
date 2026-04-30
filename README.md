# LifeRec

LifeRec 是一个开源的 AI 生活推荐系统原型，目标是把“我今天该吃什么、买什么、去哪儿、怎么安排”这类自然语言需求，转化为可执行的个性化生活方案。

项目结合 AIGC、生成式推荐、动态位置、真实生活服务 API、用户反馈和运行时生活记录，覆盖健康饮食、附近餐厅、AIGC 商品需求清单和旅行规划等场景。

> 当前定位：`v0.2` 可运行 MVP。它不是静态 Demo，而是已经具备真实 Provider、运行时用户数据、反馈重排、换一批推荐和评估脚本的完整实验项目。

## 项目亮点

- 真实动态推荐：餐厅、景点、天气、步行路线优先来自高德 Web 服务 API。
- AIGC 商品生成：不依赖淘宝、京东、拼多多，生成商品需求、预算参考和购买前检查项。
- 用户生活记忆：SQLite 保存饮食记录、推荐历史、用户反馈和 Provider 缓存。
- 健康约束推断：根据近期饮食标签识别高油、高盐、蔬菜少、蛋白不足等状态。
- 反馈学习：喜欢、不喜欢、加入计划等行为会影响后续排序。
- 换一批推荐：基于 `request_id` 排除上一批结果，重新生成替代方案。
- 真实数据边界：严格模式下不使用本地样例补餐厅、景点或商品结果。
- 工程化基础：FastAPI、原生 Web 前端、Docker、pytest、GitHub Actions、公开密钥扫描。

## 工作流

```text
自然语言需求
  -> 意图识别
  -> 用户上下文：位置、饮食记录、反馈画像、偏好
  -> Provider：高德 POI / 天气 / 路线 + OpenAI-compatible LLM
  -> 候选生成与排序
  -> AIGC 解释
  -> 推荐卡片、行动计划、后续反馈
```

## 当前能力

| 场景 | 已实现能力 | 数据来源 |
|---|---|---|
| 健康饮食 | 根据近期饮食、忌口、预算和口味生成餐饮建议 | 用户输入 + SQLite 饮食记录 |
| 附近餐厅 | 基于当前位置或城市推荐附近真实 POI | 高德地点搜索 |
| 菜品建议 | 给出健康选择原则和点餐方向 | 规则 + AIGC 解释 |
| 生活购物 | 生成商品类型、预算参考、购买标准 | LLM / AIGC |
| 旅行规划 | 推荐目的地、景点和轻量行程 | 高德 POI + 规则排序 |
| 天气路线 | 推荐结果加入天气、步行距离和耗时 | 高德天气 + 高德路线 |
| 用户反馈 | 保存喜欢、不喜欢、加入计划并影响重排 | SQLite |
| 用户上下文 | 聚合饮食记录、反馈画像、存储状态 | `/api/user/context` |
| 推荐评估 | 检查重复、预算、距离、真实数据、健康冲突 | 本地评估脚本 |

## 技术栈

| 层级 | 技术 |
|---|---|
| 后端 | Python, FastAPI, Pydantic, httpx |
| 推荐核心 | 规则召回、动态距离、健康约束、反馈重排 |
| AIGC | OpenAI-compatible LLM，默认模型 `deepseek-v4-flash` |
| 地图服务 | 高德 Web 服务 API |
| 前端 | 原生 HTML/CSS/JavaScript |
| 存储 | SQLite，默认位于 `runtime/liferec.sqlite3` |
| 工程化 | Docker, pytest, GitHub Actions, PowerShell scripts |

## 快速开始

### 1. 配置环境变量

```powershell
Copy-Item .env.example .env
```

推荐配置：

```env
AMAP_API_KEY=你的高德Web服务Key
LLM_API_KEY=你的DeepSeek或OpenAI-compatible Key
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-flash
PRODUCT_PROVIDER=aigc
STRICT_REAL_DATA=true
PROVIDER_CACHE_TTL_SECONDS=300
```

`.env` 已被 `.gitignore` 忽略，不会提交到 GitHub。

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

## 示例请求

饮食餐厅：

```text
我今天不想吃饭，最近吃得有点油腻，学校附近有什么健康一点的？
```

AIGC 商品：

```text
我想开始健康饮食，帮我推荐一份购物清单。
```

旅行规划：

```text
我周末从南京出发玩两天，预算 1000，不想太累。
```

## 主要 API

| API | 用途 |
|---|---|
| `GET /api/health` | 后端健康检查和存储状态 |
| `GET /api/providers/capabilities` | 查看高德、AIGC、商品、缓存等 Provider 状态 |
| `POST /api/recommend` | 统一生活推荐入口 |
| `POST /api/recommend/refresh` | 基于 `request_id` 排除上一批结果并换一批 |
| `GET /api/user/context` | 聚合用户饮食记录、反馈画像和上下文来源 |
| `POST /api/user/meals` | 保存用户真实饮食记录 |
| `GET /api/user/meals` | 查看用户近期饮食记录和标签 |
| `POST /api/feedback` | 保存用户对推荐项的真实反馈 |
| `GET /api/feedback/summary` | 查看用户反馈画像摘要 |
| `POST /api/context/nearby` | 查询附近地点，高德优先 |
| `POST /api/context/places/search` | 按城市或关键词搜索地点，高德优先 |
| `GET /api/context/geocode/reverse` | 经纬度转地址和 adcode |
| `GET /api/context/weather` | 查询实时天气 |
| `POST /api/context/route/walking` | 查询步行路线 |
| `POST /api/context/products/search` | AIGC 商品需求清单生成 |
| `POST /api/aigc/brief` | AIGC 推荐策略摘要 |

## 真实数据策略

LifeRec 明确区分真实外部数据、用户运行时数据、AIGC 生成内容和本地开发样例。

| 类型 | 来源 | 说明 |
|---|---|---|
| 地点、天气、路线 | 高德 Web 服务 API | 配置 `AMAP_API_KEY` 后启用 |
| 商品建议 | AIGC | 不声称真实 SKU、库存、折扣或购买链接 |
| 饮食记录 | 用户主动输入 | 写入 SQLite，只用于健康约束和排序 |
| 用户反馈 | 用户点击行为 | 写入 SQLite，只影响后续排序 |
| 本地 JSON | `data/` | 仅开发 fallback，严格模式不补推荐结果 |

开启严格真实数据模式：

```env
STRICT_REAL_DATA=true
```

在该模式下，如果高德或 LLM 没有返回可用结果，系统会返回空结果或说明不可用，不会用本地样例伪装成真实推荐。

## 项目结构

```text
LifeRec
├── backend/              FastAPI 服务、Provider、推荐核心、评估逻辑
├── data/                 本地开发样例数据，严格模式下不补真实结果
├── docs/                 架构、API、真实数据、部署、测试和路线图文档
├── frontend/             Web MVP
├── scripts/              开发启动、评估和安全检查脚本
├── tests/                pytest 测试
├── AIGC+GR.md            AIGC 与生成式推荐分析文档
└── README.md
```

## 测试与质量

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

当前评估覆盖：

- 推荐结果不能重复。
- 换一批排除项不能再次返回。
- 候选距离不能超过请求半径。
- 候选价格不应明显超过预算。
- 严格真实数据模式不能返回 `sample-data`。
- 近期高油时不应优先返回油炸、重油标签。

## 文档

| 文档 | 内容 |
|---|---|
| [项目总览](docs/project-summary.md) | 当前架构、功能和边界 |
| [架构设计](docs/architecture.md) | 系统模块和数据流 |
| [动态 API 规划](docs/dynamic-api-plan.md) | 动态推荐和 Provider 方案 |
| [API 清单与获取方式](docs/api-providers.md) | 所需 API 和申请方式 |
| [API 设置指南](docs/api-setup-guide.md) | `.env` 配置和验证方法 |
| [AIGC 模块设计](docs/aigc-integration.md) | LLM 调用和 Prompt 边界 |
| [真实数据策略](docs/real-data-policy.md) | 数据真实性和 fallback 规则 |
| [反馈闭环](docs/feedback-loop.md) | 用户反馈、饮食记录和重排 |
| [部署与运行](docs/deployment.md) | 本地和 Docker 运行 |
| [测试与质量检查](docs/testing.md) | 自动化测试和评估 |
| [Roadmap](docs/roadmap.md) | 后续方向 |

## Roadmap

- 接入更多路线能力：驾车、公交、骑行。
- 增加长期偏好画像和用户配置管理。
- 引入向量检索与语义召回。
- 支持用户导入商品链接、菜单、运动、睡眠和日历数据。
- 增加多 Agent 任务规划：餐厅、路线、购物、旅行分工协作。
- 从 SQLite 迁移到 PostgreSQL，支持多人部署。

## 安全说明

- 不要提交 `.env` 或任何 API Key。
- 所有第三方 API 调用应走后端，不要把 Key 写入前端。
- AIGC 商品建议不是实时交易信息。
- 高德 POI 不提供完整菜单，菜品建议是健康选择原则，不代表餐厅真实菜单。
- LifeRec 只提供一般生活方式建议，不提供医疗诊断、治疗建议或处方建议。
