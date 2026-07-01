# spiderswitch 用户指南

> 面向本地用户的安装、配置与日常操作文档。

---

## spiderswitch 是什么？

`spiderswitch` 是一个 MCP 服务器，用于在 ai-lib 生态中动态切换模型与 provider。

它适用于支持 MCP 的客户端，例如 Cursor、Claude Desktop、OpenCode。

---

## 前置条件

| 项目 | 要求 |
|------|------|
| Python | 3.10+ |
| API Key | 至少一个 provider 的密钥 |
| MCP 客户端 | Cursor / Claude Desktop / OpenCode |
| ai-protocol | 推荐配置本地路径（`AI_PROTOCOL_PATH`） |

---

## 安装

### 方式 A：一键安装（推荐）

```bash
bash scripts/install_one_click.sh
```

安装后执行：

```bash
spiderswitch setup --client cursor    # 推荐：协议 + 配置 + 索引构建 + doctor
spiderswitch doctor --json
spiderswitch init --client cursor --output ~/.cursor/mcp.spiderswitch.json --force
```

### 方式 B：开发者安装

```bash
git clone https://github.com/ailib-official/spiderswitch.git
cd spiderswitch
pip install -e .
```

### 方式 C：离线安装（内网/隔离环境）

可从本地 wheel 或本地源码目录安装：

```bash
bash scripts/install_offline.sh /path/to/spiderswitch-<version>-py3-none-any.whl
# 或
bash scripts/install_offline.sh /path/to/spiderswitch-source
```

---

## 配置 API Key

启动 MCP 客户端前，至少配置一个 provider 的密钥。

| Provider | 环境变量 |
|----------|----------|
| OpenAI | `OPENAI_API_KEY` |
| Anthropic | `ANTHROPIC_API_KEY` |
| Google | `GOOGLE_API_KEY` 或 `GEMINI_API_KEY` |
| DeepSeek | `DEEPSEEK_API_KEY` |
| Cohere | `COHERE_API_KEY` |
| Mistral | `MISTRAL_API_KEY` |

示例：

```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
```

安全建议：

- 生产环境优先使用环境变量，不建议在工具参数中传 `api_key`。
- 不要硬编码或提交密钥。
- 建议定期轮换密钥。

---

## MCP 客户端配置

### 使用 `spiderswitch init` 快速生成配置

```bash
spiderswitch init --client cursor --output ~/.cursor/mcp.spiderswitch.json --force
```

支持的 `--client`：

- `cursor`
- `claude`
- `opencode`

### 手工配置示例

#### Cursor / Claude Desktop 格式

```json
{
  "mcpServers": {
    "spiderswitch": {
      "command": "spiderswitch",
      "args": ["serve"],
      "env": {
        "AI_PROTOCOL_PATH": "/path/to/ai-protocol",
        "OPENAI_API_KEY": "sk-..."
      }
    }
  }
}
```

#### OpenCode 格式

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "spiderswitch": {
      "type": "local",
      "command": ["spiderswitch", "serve"],
      "enabled": true,
      "environment": {
        "AI_PROTOCOL_PATH": "/path/to/ai-protocol",
        "OPENAI_API_KEY": "sk-..."
      }
    }
  }
}
```

---

## 能力索引（0.7.0+）

能力索引**离线预构建**，MCP 启动时**直接加载 JSON**，不会每次重新解析 ai-protocol YAML。

```bash
spiderswitch index build              # 写入 ~/.spiderswitch/index/capability-index.json
spiderswitch index                    # 只读加载摘要（JSON）

# ai-protocol 更新后定期重建（可用 cron）：
0 3 * * * spiderswitch index build
```

`spiderswitch setup` 会自动执行 `index build`。若索引不存在，`query_index` 等工具不可用（除非设置 `SPIDERSWITCH_INDEX_REBUILD_ON_START=1`）。

---

## CLI 命令

### `spiderswitch serve`

启动 MCP stdio 服务。

### `spiderswitch setup`

一键自部署：ai-protocol + MCP 配置 + **索引构建** + doctor。

### `spiderswitch index build`

从 ai-protocol 预构建并持久化能力索引。

### `spiderswitch index`

加载已持久化的索引并输出 JSON 摘要（快速，不重建）。

### `spiderswitch init`

生成 MCP 配置模板。

常用参数：

- `--client {cursor|claude|opencode}`
- `--output <path>`
- `--ai-protocol-path <path>`
- `--force`

### `spiderswitch doctor`

执行健康检查（Python 版本、协议路径、**能力索引**、密钥、代理 scheme、可选 runtime probe）。

常用参数：

- `--json` 输出结构化结果
- `--no-runtime-probe` 跳过模型探测以加快检查

### `spiderswitch info` / `spiderswitch version`

部署元数据或版本号（`version --json` 支持 JSON）。

### `spiderswitch protocol setup|verify`

管理 ai-protocol manifests。

---

## MCP 工具说明（8 个）

### `list_models`

列出 ai-protocol manifests 中可用模型。

参数：

- `filter_provider`（可选）
- `filter_capability`（可选）
- `require_api_key`（可选）
- `runtime_id`（可选）

### `switch_model`

切换当前模型。

参数：

- `model`（必填，`provider/model` 格式）
- `api_key`（可选，生产不推荐）
- `base_url`（可选）
- `runtime_id`（可选）

### `get_status`

查询当前状态与 runtime profile。

参数：

- `runtime_id`（可选）

### `exit_switcher`

重置运行时/会话状态。

参数：

- `runtime_id`（可选）
- `scope`（`all` 或 `runtime`，可选）

### `recommend_model`

按本地 BYOK 策略推荐模型（不调用上游 API）。

### `auto_switch`

推荐并切换（一步完成）。

### `query_index`

按能力、facet、标签、tier 或主观评分查询预构建索引。

### `record_experience`

对模型打分（质量/速度/价值 1–5），影响后续排序。

---

## 运行时环境变量

- `AI_PROTOCOL_PATH` / `AI_PROTOCOL_DIR`：本地 ai-protocol 根路径
- `SPIDERSWITCH_SYNC_ON_INIT=1`：在初始化阶段启用 dist 同步（默认关闭）
- `SPIDERSWITCH_SYNC_DIST=0`：在显式触发同步时禁用 dist 同步
- `AI_PROTOCOL_DIST_BASE_URL`：覆盖 raw dist 源地址
- `AI_PROTOCOL_DIST_API_BASE_URL`：覆盖 GitHub API 列表源地址
- `SPIDERSWITCH_LIST_CACHE_TTL_SEC`：`list_models` 缓存 TTL（默认 `5`）
- `SPIDERSWITCH_STATUS_CACHE_TTL_SEC`：`get_status` 缓存 TTL（默认 `2`）
- `SPIDERSWITCH_INDEX_PATH`：能力索引文件路径（默认 `~/.spiderswitch/index/capability-index.json`）
- `SPIDERSWITCH_INDEX_MAX_AGE_SEC`：索引超过 TTL 时告警（秒）
- `SPIDERSWITCH_INDEX_REBUILD_ON_START=1`：索引缺失时启动时从 YAML 重建（较慢兜底）

---

## 常见问题排查

### 缺少 API Key 报错

- 确认客户端进程环境里有对应 provider 的密钥变量。
- 修改环境变量后重启 MCP 客户端。
- 重新执行 `spiderswitch doctor --json` 检查。

### 代理相关失败

- 不支持的代理 scheme（例如 `socks4://`）会被拒绝。
- 请使用 `http://`、`https://` 或 `socks5://`。

### 模型列表为空

- 检查 `AI_PROTOCOL_PATH` 是否指向有效的 `ai-protocol` 仓库。
- 确认该路径下存在 `v1/models/*.yaml`。

### 能力索引缺失

- 执行 `spiderswitch index build`（或在 protocol 就绪后运行 `spiderswitch setup`）。
- 查看 `spiderswitch doctor --json` 中的 `capability_index` 检查项。

---

## 推荐验证流程

1. `spiderswitch protocol verify`
2. `spiderswitch index build`
3. `spiderswitch doctor --json`
4. 启动/重启 MCP 客户端
5. 调用 `list_models` 或 `query_index`
6. 调用 `auto_switch` 或 `switch_model`
7. 调用 `get_status`
8. 调用 `exit_switcher`（可选清理）

---

## 相关文档

- `README.md`：项目概览
- `README_CN.md`：中文快速开始
- `docs/AGENT_DEPLOY_GUIDE.md`：Agent 自部署指南
- `CHANGELOG.md`：版本历史
- `USAGE_EXAMPLES.md`：调用示例

---

`spiderswitch` 的目标是让模型路由过程更可控、可观测、可验证。
