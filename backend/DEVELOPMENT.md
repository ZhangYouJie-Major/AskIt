# Backend 开发指南

## 包管理器：uv

本项目使用 [uv](https://github.com/astral-sh/uv) 作为 Python 包管理器，它是极快的 Python 包管理器，替代 pip、pip-tools 和 virtualenv。

### 为什么选择 uv？

- **极快**：比 pip 快 10-100 倍
- **可靠**：使用 Rust 实现， deterministic dependency resolution
- **现代**：统一管理依赖和虚拟环境
- **兼容**：完全兼容 PyPI 生态系统

### 安装 uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# 使用 pip
pip install uv
```

### 开发工作流

#### 1. 安装依赖

```bash
# 安装所有依赖（包括开发依赖）
uv sync --dev

# 仅安装生产依赖
uv sync
```

#### 2. 启动开发服务器

```bash
# 方式 1: 使用开发脚本
./scripts/dev.sh dev

# 方式 2: 直接使用 uv
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 3. 运行测试

```bash
# 方式 1: 使用开发脚本
./scripts/dev.sh test

# 方式 2: 直接使用 uv
uv run pytest -v
```

#### 4. 添加新依赖

```bash
# 添加生产依赖
uv add fastapi

# 添加开发依赖
uv add --dev pytest

# 指定版本
uv add "fastapi==0.115.0"
```

#### 5. 代码格式化

```bash
# 方式 1: 使用开发脚本
./scripts/dev.sh format

# 方式 2: 直接使用 uv
uv run ruff check --fix .
uv run ruff format .
```

### 项目结构

```
backend/
├── pyproject.toml      # 项目配置和依赖定义
├── uv.lock             # 锁定的依赖版本（自动生成）
├── .venv/              # 虚拟环境（自动创建）
├── app/                # 应用代码
├── scripts/            # 开发脚本
│   └── dev.sh          # 开发工具脚本
└── requirements.txt    # 旧版依赖文件（已废弃，保留用于兼容）
```

### 常用命令

| 命令 | 说明 |
|------|------|
| `uv sync` | 安装/同步依赖 |
| `uv run <command>` | 在虚拟环境中运行命令 |
| `uv add <package>` | 添加新依赖 |
| `uv remove <package>` | 移除依赖 |
| `uv lock` | 更新锁文件 |
| `uv pip list` | 列出已安装的包 |

### Docker 部署

Dockerfile 已更新为使用 uv：

```bash
# 构建镜像
docker build -t askit-backend .

# 运行容器
docker run -p 8000:8000 askit-backend
```

### 从 pip 迁移

如果你之前使用 pip/requirements.txt，现在可以：

1. `requirements.txt` 已保留用于兼容
2. 新的依赖定义在 `pyproject.toml` 中
3. 使用 `uv sync` 即可自动迁移

### 故障排除

#### 虚拟环境问题

```bash
# 删除并重建虚拟环境
rm -rf .venv
uv sync --dev
```

#### 依赖冲突

```bash
# 查看依赖树
uv pip tree

# 更新所有依赖
uv lock --upgrade
```

### 相关链接

- [uv 官方文档](https://github.com/astral-sh/uv)
- [uv 命令参考](https://docs.astral.sh/uv/)
