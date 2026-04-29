# 用户反馈闭环

LifeRec 当前已经加入运行时反馈闭环。该能力不依赖静态样例数据，而是记录用户对真实推荐结果的行为，用于后续推荐重排。

## 1. 数据存储

默认使用 SQLite：

```text
runtime/liferec.sqlite3
```

`runtime/` 已加入 `.gitignore`，不会提交到 GitHub。

当前保存两类事件：

- 推荐事件：`request_id`、用户、场景、上下文、推荐结果。
- 反馈事件：用户对某个推荐项的 `like`、`dislike`、`save`、`plan`、`skip`。

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

## 3. 如何影响推荐

推荐接口会读取该用户的历史反馈：

- `like`、`save`、`plan` 会提升相同 item 或相似 tag 的排序。
- `dislike`、`skip` 会降低相同 item 或相似 tag 的排序。
- 被反馈影响的推荐项会在 `meta.feedback_adjustment` 中显示分数调整。

## 4. 数据真实性边界

- 反馈数据是真实用户行为数据。
- 反馈不会把本地样例伪装成真实外部数据。
- 严格真实数据模式下，外部候选仍来自高德或 AIGC；反馈只影响排序，不生成虚假地点或商品。
