# LifeRec 架构设计

LifeRec v0.1 采用“轻量推荐核心 + AIGC 生成解释”的混合架构。

```text
Frontend
  ↓
FastAPI /api/recommend
  ↓
Intent Parser
  ↓
Profile + Context
  ↓
Candidate Generator
  ↓
Rule Ranker
  ↓
Explanation Builder
  ↓
Recommendation Response
```

## 模块说明

- `Intent Parser`：根据用户输入识别场景、地点、预算和约束。
- `Profile + Context`：读取用户画像和近期饮食记录。
- `Candidate Generator`：根据场景生成餐厅、商品或目的地候选。
- `Rule Ranker`：基于偏好、健康、预算、距离和上下文计算综合分。
- `Explanation Builder`：为推荐结果生成可读理由和行动计划。

## 后续扩展

- 接入 LLM Provider，将意图识别和解释生成替换为真实模型调用。
- 接入向量数据库，支持餐厅、商品、景点的语义检索。
- 增加用户反馈表，支持短期偏好更新。
- 增加插件接口，把地图、电商、外卖和天气作为外部能力。

