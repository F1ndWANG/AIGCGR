# 测试与质量检查

## 安装测试依赖

```powershell
python -m pip install -r backend/requirements-dev.txt
```

## 运行测试

```powershell
python -m pytest
```

## 编译检查

```powershell
python -m compileall backend
```

## 公开密钥扫描

```powershell
.\scripts\check_public_safety.ps1
```

扫描范围会排除：

- `.env`
- `runtime/`
- `__pycache__/`
- `.git/`

## 推荐评估

如果你已经保存了一次请求 JSON 和响应 JSON，可以运行：

```powershell
python scripts\evaluate_recommendations.py --request request.json --response response.json
```

评估规则包括：

- 推荐结果不能重复。
- “换一批”排除列表中的 item 不能再次出现。
- 推荐请求未传近期饮食标签时，应能读取运行时饮食记录。
- 候选距离不能超过请求半径。
- 候选价格不应明显超过预算。
- 严格真实数据模式下不能返回 `sample-data`。
- 近期高油时不应优先返回 `油炸`、`重油` 标签。

## CI

GitHub Actions 工作流位于：

```text
.github/workflows/ci.yml
```

每次 push 或 pull request 会执行：

- 安装依赖。
- 编译后端。
- 运行 pytest。
