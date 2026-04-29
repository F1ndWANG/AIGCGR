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

`runtime/liferec.sqlite3` 保存推荐历史、用户反馈和 Provider 响应缓存。该数据来自用户真实操作或真实 API 响应，不属于静态样例数据，默认不提交到 Git。
