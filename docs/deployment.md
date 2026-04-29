# 部署与运行

## 本地运行

后端：

```powershell
.\scripts\dev_backend.ps1
```

前端：

```powershell
.\scripts\dev_frontend.ps1
```

访问：

```text
http://127.0.0.1:5173
```

## Docker 运行

准备 `.env`：

```powershell
Copy-Item .env.example .env
```

启动：

```powershell
docker compose up --build
```

后端：

```text
http://127.0.0.1:8000
```

## 环境变量

| 变量 | 说明 |
|---|---|
| `AMAP_API_KEY` | 高德 Web 服务 Key |
| `LLM_API_KEY` | DeepSeek 或 OpenAI-compatible Key |
| `LLM_BASE_URL` | LLM API Base URL |
| `LLM_MODEL` | 模型名称，默认 `deepseek-v4-flash` |
| `PRODUCT_PROVIDER` | 商品 Provider，默认 `aigc` |
| `STRICT_REAL_DATA` | 是否禁用本地样例 fallback |
| `PROVIDER_CACHE_TTL_SECONDS` | 高德等 Provider 响应缓存秒数 |

## 运行时数据

运行时数据位于：

```text
runtime/liferec.sqlite3
```

保存内容：

- 推荐历史。
- 用户反馈。
- Provider 响应缓存。

`runtime/` 不提交到 GitHub。
