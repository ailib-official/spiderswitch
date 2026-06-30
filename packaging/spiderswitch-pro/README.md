# SpiderSwitch Pro Pack

Gumroad / 手动交付包。100% BYOK，无平台 API 预充值。

## 内容

- `cursor-mcp/` — Cursor MCP 配置模板
- `routing/` — 成本优先 / 质量优先策略 YAML
- `install.sh` — 一键安装

## 安装

```bash
unzip spiderswitch-pro-*.zip
cd spiderswitch-pro
chmod +x install.sh
SPIDERSWITCH_INSTALL_SOURCE=/path/to/spiderswitch ./install.sh
```

## E2E 验证

安装后：

```bash
export OPENAI_API_KEY=sk-...
export DEEPSEEK_API_KEY=sk-...
spiderswitch doctor --json
```

在 Cursor Agent 中调用 MCP 工具 `recommend_model` 或 `auto_switch`。
