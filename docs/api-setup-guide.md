# LifeRec API 设置指南

本文档说明如何配置 LifeRec 的真实数据 Provider。当前项目主路径只需要两个外部能力：高德 Web 服务 API 和 OpenAI-compatible LLM API。

## 1. 配置文件

复制模板：

```powershell
Copy-Item .env.example .env
```

`.env` 已被 `.gitignore` 忽略，不会提交到 GitHub。

推荐配置：

```text
AMAP_API_KEY=你的高德Web服务Key
LLM_API_KEY=你的DeepSeek或OpenAI-compatible Key
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-flash
PRODUCT_PROVIDER=aigc
STRICT_REAL_DATA=true
PROVIDER_CACHE_TTL_SECONDS=300
```

`STRICT_REAL_DATA=true` 表示不使用本地餐厅、景点、商品样例补结果。适合你当前“所有数据都是真实的，不是静态的”的要求。

## 2. 高德开放平台 API

### 用途

- 附近餐厅搜索。
- 附近景点搜索。
- 城市和关键词地点搜索。
- 经纬度转地址。
- 实时天气。
- 步行路线规划。

### 获取步骤

1. 打开高德开放平台：https://lbs.amap.com/
2. 注册或登录开发者账号。
3. 进入控制台并创建应用。
4. 在应用中创建 Key。
5. Key 类型选择 `Web服务`。
6. 将 Key 写入 `.env`：

```text
AMAP_API_KEY=你的高德Web服务Key
```

### 验证

启动后端：

```powershell
cd backend
uvicorn app.main:app --reload --port 8000
```

查看 Provider：

```text
http://127.0.0.1:8000/api/providers/capabilities
```

应看到：

```json
{
  "places": { "active": true },
  "weather": { "active": true },
  "routes": { "active": true }
}
```

测试附近餐厅：

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/context/nearby" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"latitude":31.936,"longitude":118.904,"keyword":"餐厅","radius_km":3}'
```

测试天气：

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/context/weather?latitude=31.936&longitude=118.904"
```

测试步行路线：

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/context/route/walking" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"origin_latitude":31.936,"origin_longitude":118.904,"destination_latitude":31.939,"destination_longitude":118.906}'
```

## 3. LLM API

### 用途

- 推荐策略摘要。
- 商品需求清单生成。
- 推荐理由和行动计划生成。

### DeepSeek 配置

```text
LLM_API_KEY=你的DeepSeekKey
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-flash
```

### OpenAI-compatible 配置

```text
LLM_API_KEY=你的模型平台Key
LLM_BASE_URL=https://你的模型平台/v1
LLM_MODEL=对应模型名称
```

测试 AIGC：

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/aigc/brief" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"message":"我想吃健康一点的晚餐","scenario":"restaurant","health_tags":["高油","蔬菜少"]}'
```

## 4. 商品 Provider

当前不接淘宝、京东、拼多多。商品能力采用 AIGC 生成“商品需求清单”，返回商品类型、预算参考、选择标准和购买提示。

关键边界：

- 不声称是真实 SKU。
- 不声称实时价格或库存。
- 不生成未经验证的购买链接。
- 如果需要真实商品交易，后续应接入用户自有商品 Feed 或合规电商开放平台。

测试：

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/context/products/search" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"keyword":"健康饮食","budget":200,"tags":["低油","高蛋白"],"limit":5}'
```

## 5. 前端定位权限

前端“使用当前位置”按钮依赖浏览器定位能力。

- 用户必须授权。
- `localhost` 可以使用定位。
- 线上部署通常需要 HTTPS。
- 获取到的位置只传给后端，用于高德地点、天气和路线推荐。

## 6. 反馈存储

用户反馈和推荐历史默认保存在：

```text
runtime/liferec.sqlite3
```

该目录已被 `.gitignore` 忽略。反馈数据用于后续推荐重排，不会上传到第三方 Provider。

Provider 响应缓存也保存在同一个 SQLite 文件中。缓存 key 会剔除 API Key，只按请求 Provider、URL 和非密钥参数生成。

## 7. 安全注意事项

- 不要提交 `.env`。
- 不要把 API Key 写到前端代码。
- 真实部署时，所有第三方 API 调用都应走后端。
- 如果 API Key 已在聊天、截图或公开仓库中暴露，应立即轮换。
- 健康建议不能写成诊断或治疗结论。
