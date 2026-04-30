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

`runtime/liferec.sqlite3` 保存推荐历史、用户反馈、用户饮食记录和 Provider 响应缓存。该数据来自用户真实操作或真实 API 响应，不属于静态样例数据，默认不提交到 Git。

主要运行时表：

- `recommendation_events`：保存 `request_id`、原始推荐请求、上下文和已展示结果，用于“换一批”和评估。
- `feedback_events`：保存用户对推荐项的喜欢、不喜欢、加入计划等行为，用于后续重排。
- `meal_events`：保存用户手动记录的餐食名称、饮食标签、备注和时间，用于推断近期健康约束。
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
