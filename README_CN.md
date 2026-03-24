# spiderswitch（ai-lib生态系统MCP模型切换器）

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT%20OR%20Apache--2.0-green.svg)](LICENSE)

MCP（Model Context Protocol）服务器，使Agent能够从[ai-lib生态系统](https://github.com/ailib-official/ai-lib-python)动态切换AI模型。

## 功能特性

- **协议驱动**：所有模型配置从ai-protocol manifests加载（ARCH-001）
- **多Provider支持**：支持OpenAI、Anthropic、Google、DeepSeek等
- **运行时无关**：使用ai-lib-python SDK进行统一的模型交互
- **MCP兼容**：通过stdio传输实现标准MCP工具
- **能力发现**：查询可用模型及其能力
- **本地就绪提示**：`list_models` 返回每个 provider 的 API key 存在状态与代理就绪状态
- **明确退出路径**：`exit_switcher` 可重置运行时与状态，便于回退
- **自动协议路径**：自动探测本地 `ai-protocol` 并为当前进程设置 `AI_PROTOCOL_PATH`
- **官方 Dist 同步**：启动时尽力同步官方 `dist/v1/*.json` 到本地 `ai-protocol/dist/v1`

## 快速开始

### 安装

```bash
# 克隆仓库
git clone https://github.com/ailib-official/spiderswitch.git
cd spiderswitch

# 安装依赖
pip install -e .
```

### 环境配置

设置你的API密钥：

```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GOOGLE_API_KEY="..."
```

推荐 provider 与环境变量映射：

| Provider | 环境变量 |
|----------|----------|
| openai | `OPENAI_API_KEY` |
| anthropic | `ANTHROPIC_API_KEY` |
| google | `GOOGLE_API_KEY` 或 `GEMINI_API_KEY` |
| deepseek | `DEEPSEEK_API_KEY` |
| cohere | `COHERE_API_KEY` |
| mistral | `MISTRAL_API_KEY` |

安全建议：
- 生产环境优先使用环境变量，不要在工具参数中显式传 `api_key`。
- 服务端日志会做敏感字段脱敏，但客户端调用轨迹中仍可能暴露明文参数。

可选运行时环境变量：
- `SPIDERSWITCH_SYNC_ON_INIT=1`：开启运行时初始化阶段的 `dist` 同步（默认关闭）。
- `SPIDERSWITCH_SYNC_DIST=0`：在显式触发同步时关闭 `dist` 同步。
- `AI_PROTOCOL_DIST_BASE_URL`：覆盖官方 raw dist 源地址。
- `AI_PROTOCOL_DIST_API_BASE_URL`：覆盖 models/providers dist json 的 GitHub API 列表源地址。
- `SPIDERSWITCH_LIST_CACHE_TTL_SEC`：`list_models` 缓存 TTL（默认 `5` 秒）。
- `SPIDERSWITCH_STATUS_CACHE_TTL_SEC`：`get_status` 缓存 TTL（默认 `2` 秒）。

### 一键安装（插件市场形态）

```bash
bash scripts/install_one_click.sh
```

安装后可执行：

```bash
spiderswitch init --client cursor --output ~/.cursor/mcp.spiderswitch.json --force
spiderswitch doctor --json
```

### 离线安装（内网/隔离环境）

可从本地 wheel 或本地源码目录安装：

```bash
bash scripts/install_offline.sh /path/to/spiderswitch-0.4.0-py3-none-any.whl
# 或
bash scripts/install_offline.sh /path/to/spiderswitch-source
```

### 配置

添加到你的MCP客户端配置：

#### OpenCode 配置

配置文件路径：`~/.config/opencode/opencode.json`

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "spiderswitch": {
      "type": "local",
      "command": ["python3", "-m", "spiderswitch.server"],
      "enabled": true,
      "environment": {
        "AI_PROTOCOL_PATH": "/path/to/ai-protocol",
        "OPENAI_API_KEY": "sk-your-key",
        "ANTHROPIC_API_KEY": "sk-ant-your-key",
        "DEEPSEEK_API_KEY": "sk-your-key"
      }
    }
  }
}
```

#### Claude Desktop / Cursor 配置

配置文件路径：`~/.config/claude-desktop/config.json` 或 `~/.cursor/mcp.json`

```json
{
  "mcpServers": {
    "spiderswitch": {
      "command": "python3",
      "args": ["-m", "spiderswitch.server"],
      "env": {
        "AI_PROTOCOL_PATH": "/path/to/ai-protocol"
      }
    }
  }
}
```

### 验证配置（OpenCode）

```bash
# 查看已加载的MCP服务器
opencode mcp list

# 预期输出：
# ✓ spiderswitch connected
#   python3 -m spiderswitch.server
```
### 使用方法

在Agent中调用MCP工具：

```python
# 列出可用模型
models = await mcp_client.call_tool("list_models", {})

# 切换到Claude 3.5 Sonnet
await mcp_client.call_tool(
    "switch_model",
    {"model": "anthropic/claude-3-5-sonnet"}
)

# 检查当前状态
status = await mcp_client.call_tool("get_status", {})
```

## 可用的MCP工具

### 1. switch_model

切换到不同的AI模型/provider。

**参数：**
- `model`（字符串，必填）：模型标识符（如 `openai/gpt-4o`、`anthropic/claude-3-5-sonnet`）
- `api_key`（字符串，可选）：显式API密钥（覆盖环境变量；生产环境不推荐）
- `base_url`（字符串，可选）：用于测试/mock的自定义基础URL

**返回：**
```json
{
  "status": "success",
  "data": {
    "id": "anthropic/claude-3-5-sonnet",
    "provider": "anthropic",
    "capabilities": ["streaming", "tools", "vision"],
    "proxy_status": {
      "provider": "anthropic",
      "proxy_required_guess": false,
      "proxy_configured": false,
      "configured_proxy_env_vars": [],
      "hint": null
    },
    "warnings": []
  },
  "message": "Successfully switched to anthropic/claude-3-5-sonnet"
}
```

### 2. list_models

列出所有已注册provider的可用模型。

**参数：**
- `filter_provider`（字符串，可选）：按provider ID过滤
- `filter_capability`（字符串，可选）：按能力过滤（`streaming`、`tools`、`vision`、`embeddings`、`audio`）

**返回：**
```json
{
  "status": "success",
  "data": {
    "count": 2,
    "models": [
      {
        "id": "openai/gpt-4o",
        "provider": "openai",
        "capabilities": ["streaming", "tools", "vision"],
        "api_key_status": {
          "provider": "openai",
          "has_api_key": true,
          "expected_env_vars": ["OPENAI_API_KEY"],
          "configured_env_vars": ["OPENAI_API_KEY"]
        },
        "proxy_status": {
          "provider": "openai",
          "proxy_required_guess": true,
          "proxy_configured": false,
          "configured_proxy_env_vars": [],
          "hint": "This provider may require proxy access in your network region. Set HTTPS_PROXY/HTTP_PROXY in the MCP server process environment if needed."
        }
      },
      {
        "id": "anthropic/claude-3-5-sonnet",
        "provider": "anthropic",
        "capabilities": ["streaming", "tools", "vision"]
      }
    ],
    "filtered": {
      "require_api_key": false,
      "provider": null,
      "capability": null
    }
  }
}
```

### 3. get_status

获取当前模型状态和配置。

**返回：**
```json
{
  "status": "success",
  "data": {
    "provider": "anthropic",
    "model": "claude-3-5-sonnet",
    "capabilities": ["streaming", "tools", "vision"],
    "is_configured": true,
    "connection_epoch": 3,
    "last_switched_at": "2026-03-02T09:00:00+00:00"
  }
}
```

### 4. exit_switcher

显式重置 spiderswitch 运行时客户端与状态。

**返回：**
```json
{
  "status": "success",
  "data": {
    "exited": true,
    "status": {
      "provider": null,
      "model": null,
      "is_configured": false
    }
  }
}
```

## API Key 指南与排障

当 `switch_model` 因密钥缺失失败时，返回里会包含：
- `provider`：缺失密钥的 provider
- `expected_env_vars`：支持的环境变量名称
- `hint`：可直接执行的修复提示

建议排障流程：
1. 在 MCP 服务器进程环境中配置对应 API key。
2. 如客户端不支持热更新环境变量，重启 MCP 服务进程。
3. 重新调用 `switch_model`。
4. 调用 `get_status` 确认状态。

## 与 Agent 连接管理的协调方式

本服务在内部管理模型客户端生命周期。为了避免与 agent 自身连接管理冲突，建议：
- 把 MCP switcher 作为模型切换控制平面；
- agent 侧监听 `get_status.connection_epoch`；
- 仅当 `connection_epoch` 增加时，重建 agent 侧缓存会话。

这样可以避免模型切换后继续复用旧连接，降低状态漂移风险。

## 架构

```
spiderswitch/
├── src/
│   ├── server.py           # MCP服务器主入口
│   ├── tools/              # MCP工具实现
│   │   ├── switch.py       # switch_model工具
│   │   ├── list.py         # list_models工具
│   │   ├── status.py       # get_status工具
│   │   └── reset.py        # exit_switcher工具
│   ├── runtime/            # 运行时抽象层
│   │   ├── base.py         # 基础运行时接口
│   │   ├── python_runtime.py  # ai-lib-python实现
│   │   └── loader.py       # ProtocolLoader封装
│   └── state.py            # 状态管理
├── tests/                  # 测试套件
└── pyproject.toml          # 项目配置
```

## 开发

### 运行测试

```bash
# 安装测试依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 运行测试并生成覆盖率报告
pytest --cov=src/spiderswitch
```

### 使用Mock服务器测试

使用[ai-protocol-mock](https://github.com/ailib-official/ai-protocol-mock)：

```bash
# 启动mock服务器
docker-compose up -d ai-protocol-mock

# 使用mock运行
MOCK_HTTP_URL=http://localhost:4010 python -m spiderswitch.server
```

### 代码风格

```bash
# 格式化代码
ruff format src tests

# 代码检查
ruff check src tests

# 类型检查
mypy src
```

## 协议驱动设计（ARCH-001）

本服务器遵循ai-lib设计原则：

> **一切逻辑皆算子，一切配置皆协议**

所有provider配置从ai-protocol manifests加载。没有provider特定的硬编码逻辑。添加新provider只需在ai-protocol中添加manifest文件。

## 相关项目

- [ai-protocol](https://github.com/ailib-official/ai-protocol) - 协议规范
- [ai-lib-python](https://github.com/ailib-official/ai-lib-python) - Python运行时SDK
- [ai-lib-rust](https://github.com/ailib-official/ai-lib-rust) - Rust运行时SDK
- [ai-lib-ts](https://github.com/ailib-official/ai-lib-ts) - TypeScript运行时SDK

## 许可证

本项目采用以下任一许可证：
- Apache License, Version 2.0 ([LICENSE-APACHE](LICENSE-APACHE) 或 http://www.apache.org/licenses/LICENSE-2.0)
- MIT License ([LICENSE-MIT](LICENSE-MIT) 或 http://opensource.org/licenses/MIT)

可选其一。

## 贡献

欢迎贡献！请确保：
1. 代码遵循PEP 8并通过`ruff check`
2. 类型提示通过`mypy --strict`
3. 包含新功能的测试
4. 更新文档

---

**spiderswitch** - Where MCP meets ai-lib. 🤖🔀
