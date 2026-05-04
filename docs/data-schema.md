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

## 今日 AIGC 简报

`GET /api/user/daily-brief` 会聚合该用户的饮食记录、生活状态、长期偏好、反馈、active 计划和推荐历史，生成今日生活简报。

返回内容包括：

- `summary`：一句总体判断。
- `priorities`：今日优先考虑的生活约束。
- `risk_flags`：需要注意的上下文风险，例如数据不足或近期高负担信号。
- `next_actions`：下一步可执行动作。
- `context_sources`：简报实际读取的数据来源。

如果配置了 `LLM_API_KEY`，简报由 DeepSeek/OpenAI-compatible 模型生成；如果没有配置且未启用严格真实数据模式，系统会只基于真实运行时上下文生成确定性摘要，不补外部地点、商品或价格。
