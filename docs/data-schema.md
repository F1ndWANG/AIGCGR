# 数据说明

当前示例数据全部位于 `data/` 目录，均为虚构数据，只用于开发 fallback、测试和无 Key 演示。开启 `STRICT_REAL_DATA=true` 后，推荐主链路不会用这些文件补餐厅、景点或商品结果。

## 用户数据

`users.json` 包含：

- 基础位置和预算。
- 口味偏好。
- 忌口和过敏。
- 健康目标。
- 近期饮食记录。
- 旅行偏好。

## 餐厅与菜品

`restaurants.json` 通过 `dish_ids` 关联 `dishes.json`。

推荐排序会同时考虑餐厅标签和菜品标签。

## 商品数据

`products.json` 用于生活购物导购，当前覆盖健康饮食和短途旅行场景。

## 旅行数据

`destinations.json` 用于目的地推荐和行程生成。

## 运行时数据

`runtime/liferec.sqlite3` 保存推荐历史、用户反馈、用户饮食记录、生活状态记录、长期用户偏好和 Provider 响应缓存。该数据来自用户真实操作或真实 API 响应，不属于静态样例数据，默认不提交到 Git。

主要运行时表：

- `recommendation_events`：保存 `request_id`、原始推荐请求、上下文和已展示结果，用于“换一批”、推荐历史、评估和后续 Agent 接力。
- `feedback_events`：保存用户对推荐项的喜欢、不喜欢、加入计划等行为，用于后续重排。
- `meal_events`：保存用户手动记录的餐食名称、饮食标签、备注和时间，用于推断近期健康约束。
- `wellness_events`：保存用户手动记录的睡眠、运动、压力和生活状态标签，用于一般生活推荐约束。
- `user_preferences`：保存默认地点、默认预算、口味、忌口、过敏、健康目标和旅行偏好，用于补全后续推荐上下文。
- `plan_items`：保存用户从推荐卡片加入的行动计划项，支持 `scheduled_for` 执行时间和 active、done、canceled 状态；前端可直接设置时间、标记完成或取消。
- `api_cache`：保存高德等 Provider 响应缓存，缓存 key 会去除 API Key。

饮食记录示例：

```json
{
  "user_id": "u001",
  "meal_name": "炸鸡和奶茶",
  "tags": ["高油", "高糖", "蔬菜少"],
  "note": "晚餐"
}
```

当推荐请求没有显式传入 `recent_meal_tags` 时，后端会自动读取 `meal_events` 中该用户最近的饮食标签；如果请求中传入了标签，则以本次请求为准。

生活状态记录示例：

```json
{
  "user_id": "u001",
  "tags": ["睡眠不足", "压力高"],
  "sleep_hours": 5.5,
  "exercise_minutes": 10,
  "stress_level": 4,
  "mood": "疲惫",
  "note": "期末周"
}
```

相关接口：

```text
POST /api/user/wellness
GET /api/user/wellness
GET /api/user/context
GET /api/user/export
GET /api/user/recommendations
GET /api/user/daily-brief
```

当推荐请求没有显式传入 `recent_wellness_tags` 时，后端会自动读取 `wellness_events` 中该用户最近的生活状态标签，例如睡眠不足、运动不足、压力高。该能力只用于一般生活方式建议，不提供医疗诊断。

长期偏好示例：

```json
{
  "user_id": "u001",
  "default_location": "南京江宁",
  "default_budget": 50,
  "taste": ["清淡", "高蛋白"],
  "avoid": ["油炸"],
  "allergies": ["花生"],
  "health_goals": ["减脂"],
  "travel_style": ["轻松", "自然"]
}
```

相关接口：

```text
GET /api/user/preferences
PUT /api/user/preferences
GET /api/user/context
```

当推荐请求没有显式传入地点、预算、口味、忌口、过敏、健康目标或旅行偏好时，后端会自动读取 `user_preferences` 中该用户保存的长期画像。

计划项示例：

```json
{
  "user_id": "u001",
  "request_id": "recommendation-request-id",
  "item_id": "B0IA3YONKY",
  "item_name": "黄焖鸡米饭(方山熙园店)",
  "item_type": "restaurant",
  "title": "今晚去黄焖鸡米饭(方山熙园店)",
  "tags": ["餐饮服务", "快餐厅"],
  "source": "amap",
  "note": "来自真实高德地点数据"
}
```

相关接口：

```text
POST /api/user/plans
GET /api/user/plans
GET /api/user/plans/export
GET /api/user/plans/export.ics
PATCH /api/user/plans/{plan_id}
```

计划状态：

- `active`：当前待执行计划。
- `done`：已完成。
- `canceled`：已取消。

`GET /api/user/context` 默认只返回 active 计划，用于前端侧栏展示当前待执行事项；历史计划可通过 `GET /api/user/plans?status=done` 或 `status=canceled` 查询。

`PATCH /api/user/plans/{plan_id}` 支持局部更新，常用字段：

- `status`：`active`、`done` 或 `canceled`。
- `scheduled_for`：ISO 8601 时间字符串；传 `null` 可清空计划时间。
- `title` / `note`：用于后续 Agent 或前端扩展的标题和备注。

计划导出接口会返回：

- `summary`：active、done、canceled 和 total 数量。
- `active`：当前待执行计划。
- `done`：已完成计划。
- `canceled`：已取消计划。

`GET /api/user/plans/export.ics` 会把计划导出为 iCalendar 文件。计划项如果有 `scheduled_for`，ICS 会使用该时间；如果没有，系统会自动按导出时间顺延生成 1 小时事件，确保日历软件可导入。

## 推荐历史

`recommendation_events` 会在每次生成推荐时保存真实请求、上下文和已展示结果。前端通过 `GET /api/user/context` 读取最近 5 条历史摘要，也可以通过 `GET /api/user/recommendations?user_id=u001&limit=20` 单独查询。

返回摘要包含：

- `request_id`：可用于“换一批”排除上一批候选。
- `scenario` / `message` / `created_at`：用户当时的推荐场景、原始需求和生成时间。
- `context`：当时的地点、半径、天气、真实数据策略等上下文。
- `top_items`：从真实推荐结果中提取的 Top 候选摘要，不从静态样例补齐。

## 推荐证据链

`RecommendationItem.trace` 用于解释推荐排序过程，是后续 Life State Vector、Execution Score、Realness Guard 的基础字段。

字段包括：

- `ranker`：当前使用的排序器版本，例如 `life_rec_weighted_v0`。
- `score_formula`：当前多目标评分公式。
- `data_sources`：推荐实际依赖的数据源，例如 `amap.poi`、`amap.walking_route`、`aigc.product_need`、`runtime.feedback`。
- `evidence`：评分证据，包括 preference、health、budget、distance、context 等分项。
- `penalties`：扣分项，例如 `budget_fit_low`、`distance_cost_high`、`not_real_provider_data`。
- `confidence`：基于分项得分、真实 Provider 数据和扣分项计算的 0-1 置信度。

## 可执行性评分

`RecommendationItem.execution` 用于衡量推荐现在是否容易执行。该字段由 `ExecutionCostScorer` 动态计算，不依赖静态样例标签。

核心字段：

- `executable_score`：0-1 可执行分数，越高越容易立刻执行。
- `execution_cost`：0-1 执行成本，越高表示负担越大。
- `distance_cost`：距离或步行距离成本。
- `budget_cost`：价格、预算或预算参考成本。
- `time_cost`：路线耗时或执行耗时成本。
- `weather_cost`：雨、雪、雾、霾、极端温度等天气阻力。
- `complexity_cost`：决策复杂度，例如建议项过多或旅行安排复杂。
- `data_risk`：数据可信度风险，例如真实高德 POI、AIGC 商品需求或本地样例数据。
- `blockers`：主要阻碍项，例如 `distance_high`、`budget_exceeded`、`route_time_unknown`。
- `evidence`：执行评分证据，例如 `distance_km=0.8`、`price_ratio=0.75`。

推荐主链路会将原始相关性分数与 `executable_score` 融合重排。评估脚本也会统计 `average_executable_score`，并对低可执行性候选输出 `low_executable_score` warning。

## 计划感知排序

`RecommendationItem.plan_signal` 用于描述推荐结果与用户已有计划之间的关系。该字段由 `PlanAwareRanker` 基于 `plan_items` 动态生成。

核心规则：

- active 计划：相同 `item_id` 或 `item_name` 会被视为重复推荐并降权。
- active 标签重叠：与当前待执行计划高度相似时软降权。
- done 计划：完成过的计划标签会提供正向加权，代表用户真实执行偏好。
- canceled 计划：取消过的计划标签会提供负向加权。
- scheduled active：已设置未来执行时间且相似的计划会触发 `schedule_conflict`。

核心字段：

- `adjustment`：计划感知排序对最终分数的加减值。
- `duplicate_active`：是否与 active 计划重复。
- `schedule_conflict`：是否与已排期 active 计划冲突。
- `completed_tag_boost`：done 计划标签带来的加权。
- `canceled_tag_penalty`：canceled 计划标签带来的惩罚。
- `active_overlap`：与 active 计划的标签重叠度。
- `blockers`：计划阻碍项，例如 `active_plan_duplicate`。
- `evidence`：计划排序证据，例如 `done_tag_boost=0.5`。

当计划状态通过 `PATCH /api/user/plans/{plan_id}` 更新为 `done` 或 `canceled` 时，后端会同步写入 `feedback_events`，把计划执行结果沉淀为更强的用户反馈。

## AIGC 真实性防护

`RecommendationItem.realness` 和 `ProductItem.realness` 用于显式区分真实 Provider 数据、AIGC 需求生成和本地样例数据。该字段由 `AIGCVerifier` 生成。

核心字段：

- `label`：数据边界标签，例如 `provider_grounded`、`aigc_product_need`、`development_sample`。
- `realness_score`：0-1 真实性分数，越高表示越可由 Provider 或明确边界支撑。
- `hallucination_risk`：0-1 幻觉风险，越高越需要降级或拦截。
- `passed`：是否通过禁止声明检查。
- `data_sources`：真实性判断依据，例如 `amap.provider` 或 `aigc.generated_need`。
- `risk_flags`：风险项，例如 `forbidden_claim_detected`、`aigc_boundary_weak`。
- `forbidden_claims`：命中的禁止声明类型。
- `evidence`：真实性证据。

AIGC 或非 Provider 输出不得声称：

- 真实电商购买链接。
- SKU、货号或商品编号。
- 库存、现货、有货。
- 折扣、优惠券、限时、包邮、全网最低。
- 实时价格或当前售价。
- 真实餐厅菜单或真实供应菜品。

`AigcProductProvider` 会对每个生成商品做校验；严格真实数据模式下，命中禁止声明的 AIGC 商品会被过滤。评估脚本会统计 `average_realness_score`，并对禁止声明输出 `aigc_forbidden_claim`。

## 今日 AIGC 简报

`GET /api/user/daily-brief` 会聚合该用户的饮食记录、生活状态、长期偏好、反馈、active 计划和推荐历史，生成今日生活简报。

返回内容包括：

- `summary`：一句总体判断。
- `priorities`：今日优先考虑的生活约束。
- `risk_flags`：需要注意的上下文风险，例如数据不足或近期高负担信号。
- `next_actions`：下一步可执行动作。
- `context_sources`：简报实际读取的数据来源。

如果配置了 `LLM_API_KEY`，简报由 DeepSeek/OpenAI-compatible 模型生成；如果没有配置且未启用严格真实数据模式，系统会只基于真实运行时上下文生成确定性摘要，不补外部地点、商品或价格。

## 用户记忆导出

`GET /api/user/export` 会导出指定用户的完整运行时记忆，便于调试、备份、迁移和后续 Agent 接力。

导出内容包括：

- `meals`：真实饮食记录。
- `wellness`：生活状态记录。
- `feedback`：用户反馈画像和事件。
- `preferences`：长期偏好。
- `plans`：active、done、canceled 计划分组和统计。
- `recommendations`：推荐历史摘要和 Top 候选。
- `context_sources`：每类数据实际读取的 SQLite 表。

导出结果不会包含 `.env`、API Key、Provider 原始缓存密钥或本地运行日志。
## Life State Vector

`GET /api/user/life-state` 会即时读取运行时 SQLite 数据，并通过 `LifeStateEncoder` 输出动态用户状态，不额外写入静态快照。

输入信号包括 `meal_events`、`wellness_events`、`user_preferences`、`feedback_events`、`plan_items` 和 `recommendation_events`。

核心输出字段：

- `short_term_tags`：近期饮食和生活状态标签。
- `long_term_tags`：长期画像标签。
- `constraints`：忌口、过敏和短期风险信号。
- `source_counts`：每类运行时数据的数量。
- `vector`：归一化后的 meal、wellness、preference、feedback、plan、history、schedule 信号。
- `context_completeness`：当前上下文覆盖度。
- `confidence`：基于上下文覆盖度和计划时间信号计算的状态置信度。
- `warnings`：缺失数据提示，例如 `missing_meal_history` 或 `missing_feedback`。

`RecommendationResponse`、`UserContextResponse`、`DailyBriefResponse` 和 `UserMemoryExportResponse` 都会携带 `life_state`，便于前端、评估脚本和后续 Agent 共用同一套状态表示。
