# 多语言改造实施方案

## 概述

本文件的业务职责，是为当前 `embedease-ai` 项目提供一套可执行的中英文多语言改造方案，覆盖前端界面、嵌入式聊天、后端错误响应、SSE/WebSocket 事件、Quick Setup、Agent 模板与默认提示词，避免项目继续以“中文硬编码”为中心扩展。

当前业务目标：

- 支持 `zh-CN` 和 `en-US`
- 语言归属以终端用户优先
- 管理台采用 URL locale 路由
- Embed/匿名访客采用自动检测 + 本地记忆
- 前后端都基于统一 locale 协议工作

统一回退顺序：

1. 显式切换的 locale
2. 登录用户 `preferred_locale`
3. 匿名会话 `conversation.locale`
4. 浏览器 `Accept-Language`
5. 工作区 `default_locale`
6. 系统默认 `zh-CN`

## 架构原则

### 1. 统一语言域模型

所有层都只使用标准 locale，不再在业务逻辑里直接用“中文 / 英文”这种自由字符串。

- `Locale = "zh-CN" | "en-US"`
- `default_locale`：工作区默认语言
- `enabled_locales`：工作区启用语言列表
- `preferred_locale`：用户偏好语言
- `resolved_locale`：当前请求最终生效语言
- `conversation.locale`：会话级语言记忆

约束规则：

- 业务状态码、事件类型、错误码保持英文机器码稳定，不翻译
- 所有用户可见文本由 `i18n key + params + locale` 生成
- 禁止在组件、服务、工具层继续直接返回中文展示文案
- 知识库原文、商品原始数据保留原值，不做离线双份翻译

### 2. 前端架构

管理台与普通页面：

- 使用 Next App Router 的 locale 路由段承载语言，例如 `/zh-CN/...`、`/en-US/...`
- `middleware` 负责首访 locale 解析、回退和重写
- `layout`、`metadata`、页面标题、描述、按钮、空状态统一从消息表读取
- 前端配置映射不再返回中文标签，而是返回稳定 key

Embed 与匿名访客：

- `EmbedWidget` 增加 `locale?: Locale | "auto"`
- `auto` 模式下根据浏览器语言解析 locale，并写入本地存储
- HTTP、SSE、WebSocket 全链路显式透传 locale
- Embed 自带语言包，不依赖宿主站点语言环境

推荐前端 i18n 目录：

- `frontend/lib/i18n/config.ts`
- `frontend/lib/i18n/types.ts`
- `frontend/lib/i18n/client.ts`
- `frontend/lib/i18n/server.ts`
- `frontend/lib/i18n/keys.ts`
- `frontend/lib/i18n/messages/zh-CN.ts`
- `frontend/lib/i18n/messages/en-US.ts`

### 3. 后端架构

后端增加请求级 `LocaleContext`，作为 API、SSE、WebSocket、错误处理、模板拼装的统一语言来源。

核心规则：

- middleware / dependency 解析 `resolved_locale`
- 请求级状态保存在 `request.state.locale`
- 所有响应设置 `Content-Language`
- WebSocket 握手接受 locale 参数或 header，并绑定到连接上下文

本地化处理分三层：

- 错误与校验：`code + i18n_key + i18n_params + message`
- 系统事件：事件 `type` 保持稳定，`payload` 中用户可见字段按 locale 输出
- 模板与提示词：按 locale bundle 管理

推荐后端 i18n 目录：

- `backend/app/core/i18n.py`
- `backend/app/core/locale.py`
- `backend/app/locales/zh-CN.py`
- `backend/app/locales/en-US.py`

### 4. 数据与模板存储

需要持久化的业务字段：

- workspace/system config：`default_locale`、`enabled_locales`
- user：`preferred_locale`
- conversation：`locale`
- agent greeting / prompt / quick setup template：按 locale bundle 存储

统一模板结构建议：

```json
{
  "zh-CN": {
    "title": "欢迎光临",
    "body": "您好，我可以帮助您推荐商品。"
  },
  "en-US": {
    "title": "Welcome",
    "body": "Hi, I can help you discover the right products."
  }
}
```

兼容规则：

- 老数据默认视为 `zh-CN`
- 缺失目标语言时回退到 `zh-CN`

### 5. AI 与 Prompt 策略

多语言不能只停留在 UI 层，Agent 输出语言必须被 locale 约束。

要求：

- 默认 Agent prompt、Greeting、Supervisor prompt、Complaint prompt 全部支持 locale 版本
- Prompt 装配时注入 `response_locale`
- 若用户当前轮显式换语言，则该轮回复语言优先跟随用户输入
- 工具层返回结构化数据和稳定错误码，减少中文硬编码影响 LLM 输出

## 需要新增的文件

### 前端新增

- `frontend/middleware.ts`
- `frontend/lib/i18n/config.ts`
- `frontend/lib/i18n/types.ts`
- `frontend/lib/i18n/client.ts`
- `frontend/lib/i18n/server.ts`
- `frontend/lib/i18n/keys.ts`
- `frontend/lib/i18n/messages/zh-CN.ts`
- `frontend/lib/i18n/messages/en-US.ts`

### 后端新增

- `backend/app/core/i18n.py`
- `backend/app/core/locale.py`
- `backend/app/locales/zh-CN.py`
- `backend/app/locales/en-US.py`

### 测试新增

- `backend/tests/i18n/test_locale_resolution.py`
- `backend/tests/i18n/test_error_localization.py`
- `backend/tests/i18n/test_chat_event_localization.py`

## 需要修改的前端文件

### 入口与路由

- `frontend/app/layout.tsx`
- `frontend/app/page.tsx`
- `frontend/app/api/v1/chat/route.ts`

### API 与 locale 透传

- `frontend/lib/api/client.ts`
- `frontend/lib/api/chat.ts`
- `frontend/lib/api/quick-setup.ts`
- `frontend/lib/api/system-config.ts`
- `frontend/lib/api/conversations.ts`
- `frontend/lib/websocket/WebSocketManager.ts`

### Embed 与聊天 UI

- `frontend/embed/EmbedWidget.tsx`
- `frontend/embed/useWebSocket.ts`
- `frontend/components/features/embed/FloatingChatWidget.tsx`
- `frontend/components/features/embed/EmbedChatContent.tsx`

### 配置与标签映射

- `frontend/lib/config/complaint-ticket-flow.ts`
- `frontend/lib/config/navigation.ts`
- `frontend/lib/config/agent-tabs.ts`
- `frontend/lib/config/labels/agent-types.ts`
- `frontend/lib/config/labels/tool-categories.ts`
- `frontend/lib/config/labels/tools.ts`
- `frontend/lib/config/labels/middleware.ts`
- `frontend/lib/config/labels/knowledge-types.ts`
- `frontend/lib/config/labels/policies.ts`
- `frontend/lib/config/labels/prompt-layers.ts`
- `frontend/lib/config/labels/config-sources.ts`
- `frontend/lib/config/labels/routing.ts`
- `frontend/lib/config/labels/tool-policies.ts`

### 管理台与 Quick Setup

- `frontend/app/admin/quick-setup/page.tsx`
- `frontend/app/admin/quick-setup/steps/system-step.tsx`
- `frontend/app/admin/quick-setup/steps/greeting-step.tsx`
- `frontend/app/admin/quick-setup/steps/summary-step.tsx`
- `frontend/app/support/page.tsx`
- `frontend/app/support/[conversationId]/page.tsx`

### 类型与状态

- `frontend/types/quick-setup.ts`
- `frontend/types/chat.ts`
- `frontend/types/websocket.ts`
- `frontend/types/conversation.ts`
- `frontend/stores/user-store.ts`
- `frontend/stores/conversation-store.ts`
- `frontend/stores/chat-store.ts`
- `frontend/stores/support-store.ts`
- `frontend/stores/support-workbench-store.ts`

## 需要修改的后端文件

### locale 基础层与错误处理

- `backend/app/main.py`
- `backend/app/core/dependencies.py`
- `backend/app/core/errors.py`

### HTTP、SSE、WebSocket

- `backend/app/routers/chat.py`
- `backend/app/routers/conversations.py`
- `backend/app/routers/ws.py`
- `backend/app/schemas/websocket.py`
- `backend/app/services/websocket/manager.py`

### Quick Setup 与系统配置

- `backend/app/routers/quick_setup.py`
- `backend/app/schemas/quick_setup.py`
- `backend/app/schemas/system_config.py`
- `backend/app/schemas/conversation.py`
- `backend/app/services/quick_setup/configurators.py`
- `backend/app/services/quick_setup/state_manager.py`
- `backend/app/services/system_config.py`
- `backend/app/services/conversation.py`

### Prompt 与模板

- `backend/app/prompts/defaults/agent.py`
- `backend/app/prompts/registry.py`
- `backend/app/services/agent/bootstrap.py`
- `backend/app/services/agent/core/config.py`

### 模型与持久化

- `backend/app/models/user.py`
- `backend/app/models/conversation.py`
- `backend/app/models/agent.py`
- `backend/app/core/database.py`

### 业务服务与工具层

- `backend/app/services/support/handoff.py`
- `backend/app/services/support/state_service.py`
- `backend/app/services/complaint/orchestrator.py`
- `backend/app/services/complaint/planner_service.py`
- `backend/app/services/complaint/executor_service.py`
- `backend/app/services/complaint/review_service.py`
- `backend/app/services/agent/tools/product/search.py`
- `backend/app/services/agent/tools/product/details.py`
- `backend/app/services/agent/tools/product/featured.py`
- `backend/app/services/agent/tools/product/filter_attribute.py`
- `backend/app/services/agent/tools/product/filter_price.py`
- `backend/app/services/agent/tools/product/by_category.py`
- `backend/app/services/agent/tools/product/category_overview.py`
- `backend/app/services/agent/tools/product/categories.py`
- `backend/app/services/agent/tools/product/purchase.py`
- `backend/app/services/agent/tools/product/similar.py`

## 对每类文件的改动要求

### 前端 i18n 基础层

- 建立 locale 常量、解析器、cookie/localStorage 持久化能力
- 提供统一 `t()` 取词入口
- 所有页面 metadata 与 `<html lang>` 受 locale 控制

### 前端 API 与实时链路

- `apiRequest` 统一注入 `Accept-Language` 与 `X-Locale`
- SSE 请求显式透传 locale
- WebSocket 握手附带 locale
- 前端消费后端稳定 code/type，而不是依赖中文文案判断逻辑

### 前端业务配置

- 所有配置映射从“直接返回中文”改为“返回 i18n key”
- Quick Setup 的 `language` 改为 `default_locale`、`enabled_locales`
- Embed 支持 `locale: "auto"`

### 后端 locale 基础层

- middleware / dependency 统一计算 `resolved_locale`
- 设置 `Content-Language`
- WebSocket 连接元数据保存 locale

### 后端错误与事件

- `AppError` 改为支持 `i18n_key` 与 `i18n_params`
- SSE/WebSocket 的事件 `type` 不变，只翻译用户可见字段
- 商品工具层优先返回稳定错误码与结构化结果

### 模板与持久化

- greeting、prompt、quick setup 模板改成 locale bundle
- 老数据默认兼容为 `zh-CN`
- system config 存储 `default_locale` 与 `enabled_locales`
- user / conversation 逐步持久化 locale 偏好

## 实施顺序

1. 建立前后端 locale 契约与 i18n 基础设施
2. 打通 HTTP、SSE、WebSocket 的 locale 透传链路
3. 改造错误响应、系统事件和前端 API client
4. 改造前端关键页面与配置映射
5. 改造 Quick Setup、Greeting、Prompt 模板存储结构
6. 改造工具层返回结构化错误码
7. 补齐测试与缺词检查

## 测试计划

### 重点测试文件

- `backend/tests/services/test_system_config.py`
- `backend/tests/services/test_conversation.py`
- `backend/tests/services/test_chat_stream_sdk.py`
- `backend/tests/services/test_chat_stream_sdk_complaint.py`
- `backend/tests/services/support/test_state_service.py`
- `backend/tests/services/complaint/test_orchestrator_stream.py`

### 必测场景

- locale 优先级解析正确
- `zh-CN` 与 `en-US` 下错误响应 `code` 相同、`message` 不同
- SSE/WebSocket 事件文案能按 locale 切换
- Quick Setup 能正确读写 `default_locale` 与 `enabled_locales`
- Prompt/Greeting 按 locale 选择正确版本
- 老配置数据在缺少 bundle 时自动回退到 `zh-CN`

## 默认假设

- 首期正式支持 `zh-CN` 和 `en-US`
- 管理台走 URL locale，embed 不强制走 locale 路由
- 机器码、枚举值、事件类型统一保持英文稳定值
- 老数据默认按 `zh-CN` 读取
- 知识库与商品库首期不做离线双语复制，只做原文检索 + 按 locale 输出
