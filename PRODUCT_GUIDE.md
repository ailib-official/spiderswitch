# Spiderswitch 产品使用指南

> **面向产品用户** - 在产品环境中使用 spiderswitch，无需本地安装

---

## 什么是 Spiderswitch？

**spiderswitch** 是一个 AI 模型切换工具，让您可以在不同的 AI 模型之间轻松切换（如从 GPT-4 切换到 Claude，或从 Claude 切换到 DeepSeek）。

它通过 **MCP (Model Context Protocol)** 协议工作，在产品或服务内部运行，您可以直接使用。

---

## 产品环境 vs 本地环境

| 场景 | 特点 | 适用人群 |
|------|------|----------|
| **产品环境** | 无需安装，服务已内置 | 最终用户、非技术用户 |
| **本地环境** | 需要安装配置本地环境 | 开发者、技术用户 |

**本指南面向产品环境用户**。

---

## 产品中的基础概念

### 1. 产品已内置的配置

在产品环境中，以下内容已经为您准备好了：

- ✅ **运行环境**: spiderswitch 服务器已部署
- ✅ **模型列表**: ai-protocol 中的最新模型清单
- ✅ **网络访问**: AI 服务连接已配置
- ✅ **API Keys 集成**: 通过产品账户系统管理

### 2. 您需要准备的

唯一需要的是：

- ⚠️ **有效的 API Keys**: 通过产品的账户管理界面配置

---

## 快速开始

### 步骤 1: 配置 API Keys

在产品的设置或账户管理页面中，找到 "Model Provider" 或 "AI 服务" 配置项：

| 服务 | 配置项说明 |
|------|-----------|
| OpenAI (GPT-4, GPT-4o) | 添加您的 OpenAI API Key |
| Anthropic (Claude) | 添加您的 Anthropic API Key |
| Google (Gemini) | 添加您的 Google API Key |
| DeepSeek | 添加您的 DeepSeek API Key |

**配置方法**：
1. 登录产品网站
2. 进入「设置」→「模型提供商」或类似页面
3. 选择您想使用的 AI 服务
4. 输入 API Key 并保存

### 步骤 2: 在产品中使用

配置完成后，您可以在产品的以下功能中使用：

#### 场景 1: 选择 AI 模型

在产品的对话或创作界面中，找到「模型选择」或「AI 设置」：

```
可用模型：
✓ GPT-4o (OpenAI) - 已配置 API Key
✓ Claude 3.5 Sonnet (Anthropic) - 已配置 API Key
✓ DeepSeek Chat (DeepSeek) - 已配置 API Key
✗ Gemini Pro (Google) - 未配置 API Key
```

只需点击选择您想要的模型，产品会自动切换。

#### 场景 2: 根据任务需求切换模型

不同任务适合不同的模型：

| 任务类型 | 推荐模型 | 原因 |
|---------|---------|------|
| 文本生成 | GPT-4o / Claude 3.5 Sonnet | 通用能力强 |
| 代码生成 | GPT-4o / Claude Sonnet | 编程能力强 |
| 多模态（图文） | GPT-4o / Claude 3.5 Sonnet | 支持视觉输入 |
| 成本敏感 | DeepSeek Chat | 性价比高 |
| 隐私敏感 | DeepSeek | 国内服务 |

---

## 需要理解的关键概念

### API Key 状态

模型列表会显示每个模型的 API Key 配置状态：

- ✅ **已配置**: 可以立即使用
- ❌ **未配置**: 需要先在产品设置中添加 API Key

**示例**：
```json
{
  "id": "openai/gpt-4o",
  "provider": "openai",
  "api_key_status": {
    "has_api_key": true,
    "configured_env_vars": ["OPENAI_API_KEY"]
  }
}
```

### 模型能力

每个模型都有不同的能力标记：

| 能力 | 说明 |
|------|------|
| streaming | 支持流式输出（实时显示） |
| tools | 支持工具调用（函数调用、代码执行） |
| vision | 支持视觉输入（图片识别） |
| embeddings | 支持向量嵌入（语义搜索） |
| audio | 支持语音输入/输出 |

---

## 常见问题

### Q: 为什么有些模型显示"未配置 API Key"？

**原因**: 产品中还没有配置该模型的 API Key。

**解决方法**:
1. 进入产品设置的「AI 服务」或「模型提供商」页面
2. 添加对应服务的 API Key
3. 保存后刷新页面或重新加载模型列表

### Q: 如何获取 API Key？

| 服务 | 获取地址 |
|------|---------|
| OpenAI | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |
| Anthropic | [console.anthropic.com/](https://console.anthropic.com/) |
| Google | [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) |
| DeepSeek | [platform.deepseek.com/api_keys](https://platform.deepseek.com/api_keys) |

**注意**: 
- API Key 通常是敏感信息，请勿分享给他人
- 建议定期更换 API Key 以保证安全

### Q: 切换模型失败，提示"Missing API Key"？

**原因**: 您选择的模型的 API Key 未在产品中配置。

**解决方法**:
1. 检查您选择的模型对应的 AI 服务（如 OpenAI、Claude）
2. 在产品设置中添加该服务的 API Key
3. 重新尝试切换模型

### Q: 模型列表和文档上说的数量不一样？

**原因**: 
- 文档上的模型数量是 ai-protocol 中的所有可用模型
- 产品中只显示您有 API Key 配置的模型（默认情况）

如果您想看到所有模型，可以在产品设置中启用「显示所有模型」（如果产品提供此选项）。

### Q: 如何知道哪些模型支持我的需求？

**方法**:
1. 查看模型的「能力」标记
2. 根据任务需求选择：
   - 需要实时输出: 选择带 `streaming` 的模型
   - 需要支持工具: 选择带 `tools` 的模型
   - 需要图片识别: 选择带 `vision` 的模型
3. 或参考产品中的「模型推荐」指南（如果提供）

### Q: 是否可以在一个对话中使用多个模型？

**答案**: 这取决于产品的功能设计。

- **逐次切换**: 某些产品允许在对话中多次切换模型，每次切换后使用新模型
- **整段切换**: 某些产品需要在对话开始前选择一个模型，整个对话使用该模型

请参考产品中的具体功能说明。

---

## 产品集成说明（面向开发/运维）

如果您的产品需要集成 spiderswitch：

### 技术架构

```
┌─────────────────────────────────────────┐
│           产品前端界面                  │
│  (Model Selection, Chat Interface)      │
└───────────────────┬─────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│         产品后端服务                      │
│  (Business Logic, Session Mgmt)         │
└───────────────────┬─────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│       Spiderswitch MCP 服务器           │
│  (Model Switching, API Routing)         │
└───────────────────┬─────────────────────┘
                    │
                    ▼
        ┌─────────┼─────────┐
        ▼         ▼         ▼
    OpenAI    Anthropic   DeepSeek
```

### 配置清单

产品集成需要提供以下配置：

| 配置项 | 说明 | 示例 |
|--------|------|------|
| Spiderswitch 服务地址 | MCP 服务器 URL | `mcp://spiderswitch.product.com` |
| AI Protocol 版本 | 使用的协议版本 | `v1` |
| 默认模型 | 新用户的默认模型 | `openai/gpt-4o` |
| API Key 存储策略 | 密钥存储方式 | 产品账户数据库、KMS 等 |
| 权限控制 | 用户可访问的模型列表 | 基于订阅等级 |

### API 集成示例

产品后端调用 spiderswitch 工具：

```python
# 伪代码：产品后端集成示例
async def get_available_models(user_id):
    """获取用户可用的模型列表"""
    # 1. 获取用户 API Keys
    api_keys = await get_user_api_keys(user_id)
    
    # 2. 调用 list_models 工具，传入 API Keys
    result = await call_spiderswitch_tool(
        "list_models",
        {
            "require_api_key": True  # 只返回有 API Key 的模型
        }
    )
    models = result["data"]["models"]
    
    # 3. 对比用户配置和可用模型
    available = filter_by_user_subscription(models, user_id)
    
    return available
```

---

## 安全与隐私

### API Key 管理

- **产品端存储**: 产品通过安全的方式存储您的 API Key（加密、密钥管理系统）
- **隐私保护**: API Key 仅在 spiderswitch 服务器到 AI 服务提供商之间传输
- **可撤销**: 您可以随时在产品设置中删除或更换 API Key

### 数据处理

- spiderswitch 不存储任何对话内容
- 所有 API 调用直接由 spiderswitch 发送到对应的 AI 服务
- 产品仅显示模型状态和配置信息

---

## 相关链接

- **ai-protocol 官方文档**: [ai-protocol 文档](https://github.com/ailib-official/ai-protocol)
- **产品支持**: 查看产品的「帮助」或「支持」页面
- **问题反馈**: 通过产品内的反馈功能提交

---

## 许可证

Spiderswitch 项目采用 MIT 或 Apache-2.0 双重许可，您可以选择其中之一。

---

**spiderswitch** — 让模型切换变得简单，在产品中开箱即用 🤖🔀
