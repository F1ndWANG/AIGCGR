# 用户反馈闭环

LifeRec 当前已经加入运行时反馈闭环。该能力不依赖静态样例数据，而是记录用户对真实推荐结果的行为，用于后续推荐重排。

## 1. 数据存储

默认使用 SQLite：

```text
runtime/liferec.sqlite3
```

`runtime/` 已加入 `.gitignore`，不会提交到 GitHub。

当前保存三类用户相关事件：

- 推荐事件：`request_id`、用户、场景、上下文、推荐结果。
- 反馈事件：用户对某个推荐项的 `like`、`dislike`、`save`、`plan`、`skip`。
- 饮食事件：用户记录的餐食名称、标签、备注和时间。

## 2. API

### `POST /api/feedback`

保存用户反馈。

```json
{
  "user_id": "u001",
  "request_id": "推荐接口返回的 request_id",
  "item_id": "B0IA3YONKY",
  "item_name": "黄焖鸡米饭(方山熙园店)",
  "item_type": "restaurant",
  "action": "like",
  "tags": ["餐饮服务", "快餐厅"],
  "source": "amap"
}
```

### `GET /api/feedback/summary`

查看用户反馈摘要。

```text
GET /api/feedback/summary?user_id=u001
```

### `POST /api/recommend/refresh`

基于某次推荐的 `request_id` 重新生成替代推荐。系统会读取原始请求，自动排除上一批已返回的推荐项。

```json
{
  "user_id": "u001",
  "request_id": "推荐接口返回的 request_id"
}
```

### `POST /api/user/meals`

保存用户饮食记录。推荐接口在没有显式传入 `recent_meal_tags` 时，会读取这些真实记录。

```json
{
  "user_id": "u001",
  "meal_name": "炸鸡和奶茶",
  "tags": ["高油", "高糖", "蔬菜少"]
}
```

### `GET /api/user/context`

聚合用户上下文。前端和后续 Agent 可以用它一次性读取饮食记录、近期饮食标签、反馈画像、存储状态和上下文来源。

```text
GET /api/user/context?user_id=u001&limit=20
```

## 3. 如何影响推荐

推荐接口会读取该用户的历史反馈：

- `like`、`save`、`plan` 会提升相同 item 或相似 tag 的排序。
- `dislike`、`skip` 会降低相同 item 或相似 tag 的排序。
- 被反馈影响的推荐项会在 `meta.feedback_adjustment` 中显示分数调整。
- “换一批”会排除同一个 `request_id` 下已经展示过的推荐项。
- 饮食记录会转化为近期饮食标签，用于识别高油、高盐、蔬菜少等健康约束。

## 4. 数据真实性边界

- 反馈数据是真实用户行为数据。
- 反馈不会把本地样例伪装成真实外部数据。
- 严格真实数据模式下，外部候选仍来自高德或 AIGC；反馈只影响排序，不生成虚假地点或商品。
