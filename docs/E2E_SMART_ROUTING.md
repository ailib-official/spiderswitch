# SpiderSwitch Smart Routing — E2E 测试指南

## 前置条件

```bash
cd /home/alex/spiderswitch
pip install -e ".[dev]"   # 或 pip install -e .

export AI_PROTOCOL_PATH=/home/alex/ai-protocol
export OPENAI_API_KEY=sk-...      # 至少一个
export DEEPSEEK_API_KEY=sk-...     # 可选，用于 cheap 路由对比
```

## 一键 E2E

```bash
bash scripts/e2e_smart_routing.sh
```

含 live 模型切换（会初始化 AiClient）：

```bash
export SPIDERSWITCH_E2E_LIVE=1
bash scripts/e2e_smart_routing.sh
```

## 打包

```bash
bash scripts/package_release.sh
# → dist/spiderswitch-pro-0.5.0.zip
# → dist/spiderswitch-0.5.0-*.whl
```

## Cursor 手动 E2E

1. 安装 Pro 包：
   ```bash
   SPIDERSWITCH_INSTALL_SOURCE=/home/alex/spiderswitch \
     bash packaging/spiderswitch-pro/install.sh
   ```

2. 将生成的 `~/.cursor/mcp.spiderswitch.json` 合并进 Cursor MCP 设置

3. 重启 Cursor，在 Agent 对话中验证：
   - 「用 recommend_model 推荐一个写代码最划算的模型」
   - 「用 auto_switch 切换到 quality tier 的模型」

4. 预期：返回 `model_id`、`tier`、`reasons`；`auto_switch` 后 `get_status` 显示已切换

## 审查摘要（v0.5.0 smart routing）

| 项 | 状态 |
|----|------|
| BYOK only，无 upstream 预充值 | ✅ |
| 策略本地，不调用 LLM | ✅ |
| 6 个 MCP 工具注册 | ✅ |
| 单元测试 policy engine | ✅ 5 passed |
| MCP 回归 list_tools | ✅ |
| E2E recommend（需 API key env） | ✅ |
| E2E live auto_switch | 需 `SPIDERSWITCH_E2E_LIVE=1` |

## 已知限制

- `auto_switch` 依赖 `recommend` + `switch_model` 链式调用；live 模式会创建 AiClient
- Pro YAML 策略文件为文档/未来扩展，v0.5.0 引擎使用内置 `smart-v1` 规则
- `vision` 任务要求 manifest 中 `vision` capability
