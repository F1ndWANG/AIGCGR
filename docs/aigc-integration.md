# AIGC 模块设计

LifeRec 的 AIGC 不是单纯聊天，而是服务于推荐链路中的三个环节。

## 1. 意图理解

输入用户自然语言：

```text
我今天不想吃饭，最近吃得有点油腻，学校附近有什么健康一点的？
```

输出结构化意图：

```json
{
  "scenario": "restaurant",
  "constraints": ["健康", "低油", "附近"],
  "budget": null,
  "location_required": true
}
```

当前版本使用规则识别，后续接入 LLM。

## 2. 推荐解释

模型根据候选对象、用户画像、健康状态和约束生成解释。

要求：

- 不虚构不存在的数据。
- 解释必须引用已有标签、价格、距离或菜品。
- 健康建议只能作为一般生活方式建议。

## 3. 生活方案生成

AIGC 把推荐结果组织成行动计划：

- 今日饮食方案。
- 餐厅和菜品选择。
- 购物清单。
- 旅行行程。
- 后续追问。

## 当前实现

- `backend/app/aigc.py`：AIGC 摘要生成入口。
- `backend/app/prompts/life_brief.md`：真实 LLM 接入时使用的 Prompt 预留位。
- `POST /api/aigc/brief`：AIGC 摘要 API。

当前没有配置 LLM API Key 时，系统使用模板生成策略摘要；配置后可以替换为 OpenAI-compatible Provider。

## 真实 LLM 接入建议

推荐输出 JSON，避免自由文本难以解析：

```json
{
  "summary": "用户希望在附近找到更健康的晚餐。",
  "strategy": "优先低油、高蛋白、蔬菜充足的餐厅。",
  "plan": ["推荐轻食或粥类", "避开重辣重油", "保留外卖选项"],
  "risks": ["不替代医疗建议"]
}
```

