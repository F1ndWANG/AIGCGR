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

## CI

GitHub Actions 工作流位于：

```text
.github/workflows/ci.yml
```

每次 push 或 pull request 会执行：

- 安装依赖。
- 编译后端。
- 运行 pytest。
