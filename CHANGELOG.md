# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- 知识库检索与原文引用跟随当前文档版本，失效及删除修订不再进入检索结果，并兼容模型内容块输出。
- 客诉 Planner、Executor 调用模型前提交当前阶段，避免一个用户等待模型时阻塞其他用户的数据库写入。
- 聊天会话绑定所选 Agent，普通 Agent 使用自身配置执行，客诉 Agent 使用绑定的提示词和知识源；防止跨会话用户或 Agent 混用历史。
- Agent 冷启动去重，工具串行锁和 TODO 广播状态按每轮运行隔离；流式连接结束时停止后台 Agent 并释放运行名额。

### Added

- 知识库文档上传、版本化入库、重建与删除流程，以及带出处的检索和原文引用能力。
- 聊天并发上限 `CHAT_MAX_CONCURRENT_RUNS`（默认 16）；同会话重复请求返回 409，超过并发配置返回 503。
- 多 Agent 并发说明及基于一次性 SQLite 的独立验证脚本。

## [0.1.18] - 2025-02-12

### 核心亮点

本版本完成 **开发工具集成**，为项目添加完整的 Windsurf skills 工具集，包括图片上传、README 图片处理、技能创建和发版流程自动化，提升开发效率和项目维护能力。

### Added

- **Windsurf Skills 工具集**
  - `qiniu-upload` - 七牛云图片上传工具，支持 PicList/PicGo 本地服务
  - `readme-images` - README.md 图片引用处理，支持 GitHub/Gitee 双平台
  - `skill-creator` - 技能创建指南，提供完整的技能开发流程
  - `release` - 发版流程自动化，支持版本管理、CHANGELOG 更新、标签创建

- **开发流程优化**
  - 标准化发版流程，包含版本检查、变更分析、CHANGELOG 更新
  - 自动化标签创建和推送
  - 支持 Gitee 和 GitHub 双平台发布

### Changed

- **项目结构**
  - 添加 `.windsurf/skills/` 目录结构
  - 集成开发工具脚本和文档

---

## [0.1.17] - 2025-02-05

### 核心亮点

本版本完成 **SDK 完整迁移**，将 streaming 组件、chat_models（v0/v1）、Payload TypedDict 全部迁移到 `langgraph-agent-kit` SDK，简化项目结构，增强代码复用性。

### Added

- **langgraph-agent-kit 增强**
  - `chat_models/` - v0/v1 双版本模型基类和 `create_chat_model()` 工厂
  - `SiliconFlowV1ChatModel` / `SiliconFlowReasoningChatModel` - 硅基流动推理模型支持
  - 24 个 Payload TypedDict 定义，支持 IDE 自动补全和类型检查
  - `parse_content_blocks()` / `ParsedContent` - content_blocks 解析工具
  - 类型守卫函数：`is_text_block`, `is_reasoning_block`, `is_tool_call_block` 等

### Changed

- **项目结构简化**：删除 12 个重复文件，统一使用 SDK 版本
- **导入路径更新**：10+ 文件更新为从 SDK 导入
- **BusinessResponseHandler**：继承 SDK 的 `StreamingResponseHandler`，添加商品数据处理
- **README.md 更新**：补充 Chat Models、Content Parser、Payload TypedDict 文档

### Fixed

- 测试文件导入路径修复

---

## [0.1.16] - 2025-01-31

### 核心亮点

本版本聚焦于 **Chat SDK 模块化** 与 **客服工作台优化**，新增完整的前端 Chat SDK 和 React Hooks 绑定，重构客服工作台为现代气泡式布局，优化多项性能和体验细节。

### Added

- **@embedease/chat-sdk**: 前端聊天核心 SDK
  - `ChatClient` - SSE 流式聊天客户端
  - Timeline 模块 - 聊天消息状态管理
  - WebSocket 模块 - 实时双向通信（心跳、重连、离线队列）

- **@embedease/chat-sdk-react**: React Hooks 封装
  - `useChat` - 完整聊天功能 Hook
  - `useTimeline` - 独立 Timeline 状态管理
  - `useWebSocket` - 独立 WebSocket 连接管理

- **langgraph-agent-kit**: LangGraph Agent 流式处理工具包
  - `StreamOrchestrator` - 流式编排器
  - 中间件系统和工具注册表

- **版本管理增强**: `update_version.py` 支持 SDK 包版本同步和一致性检查

- **版本发布工作流**: `.windsurf/workflows/create-tag.md` 完整的 Tag 发布流程

### Changed

- **客服工作台重构**: 左右分栏布局，新增用户分组和会话预览功能，首次加载优化
- **聊天页面优化**: 现代气泡式布局，移除 SSE 支持网关，统一使用 WebSocket
- **推理模型架构**: v1 推理模型注册表，支持提供商级别特殊处理
- **chat_models v1 架构**: 移除多态设计，强制使用 LangChain 标准输出
- **API 端点优化**: 移除不必要的数据库依赖，提升性能
- **嵌入式脚本命名**: 统一为 `embedeaseai-chat`

### Fixed

- 客服状态切换重复提示问题
- 硅基流动推理模型内容显示问题

### Documentation

- 日志配置速查表和界面预览
- chat_models v1/v0 版本切换说明

---

## [0.1.15] - 2026-01-30

### 核心亮点

本版本聚焦于 **中间件能力扩展** 与 **配置统一化**，新增 4 个 LangChain 原生中间件增强 Agent 稳定性，同时重构前端中间件配置体系，实现单一配置源、全局一致展示。

### Added

- **模型重试中间件 (ModelRetry)**: 当 LLM 调用失败时自动重试，支持指数退避策略。可配置最大重试次数、退避因子、初始/最大延迟、抖动开关和失败后行为（继续/报错）。通过 SSE 事件 `model.retry.start` / `model.retry.failed` 实时通知前端重试状态。

- **模型降级中间件 (ModelFallback)**: 主模型调用失败时自动切换到备选模型列表。按配置顺序依次尝试，所有模型失败后返回错误。通过 SSE 事件 `model.fallback` 通知前端降级详情（原模型、降级模型、错误原因）。

- **模型调用限制中间件 (ModelCallLimit)**: 防止 Agent 无限循环调用 LLM。支持线程级和单次运行级调用限制，超限时可选择静默结束或抛出错误。通过 SSE 事件 `model.call_limit.exceeded` 通知超限情况。

- **上下文编辑中间件 (ContextEditing)**: 智能清理历史工具调用结果，管理上下文 token 大小。支持配置触发阈值、保留最近 N 个结果、清理工具输入、排除特定工具等。通过 SSE 事件 `context.edited` 通知清理详情。

- **中间件配置统一化**: 
  - 新增 `MIDDLEWARE_FLAG_KEYS` 常量定义 12 个可配置中间件开关键名
  - 新增 `getAllMiddlewareFlags()` 函数获取完整中间件配置列表
  - 所有前端中间件展示点统一使用配置源，移除硬编码

- **中间件配置跳转**: 所有中间件展示位置（Agent 概览、设置中心、快速设置）均可点击跳转到对应 Agent 的中间件详细配置页面。

### Changed

- **中间件标签体系重构**: 
  - `MIDDLEWARE_LABELS` 扩展至 12 个开关标签（新增 ModelRetry、ModelFallback、ModelCallLimit、ContextEditing）
  - `MIDDLEWARE_PIPELINE_LABELS` 扩展至 16 个管道标签
  - `policies.ts` 移除重复标签定义，改为引用统一的 `getMiddlewareLabel()`

- **中间件展示组件优化**:
  - `MiddlewareFlagsCard` 改为遍历 `MIDDLEWARE_FLAG_KEYS` 显示全部 12 个中间件
  - `settings/page.tsx` 全局中间件默认配置和 Agent 对比表改为动态渲染
  - `quick-setup/knowledge-step.tsx` 移除硬编码标签映射

- **backend-architecture skill 更新**: 中间件执行顺序表更新为 16 个中间件，新增"可配置"列区分系统级和 Agent 级中间件，补充中间件 SSE 事件类型。

---

## [0.1.14] - 2026-01-29

### 核心亮点

本版本聚焦于**用户体验一致性**和**配置透明度**，让管理员更清晰地理解系统配置，同时简化日常操作路径。

### Added

- **Agent 运行态配置预览** (`frontend/app/admin/agents/[agentId]/effective-config/*`, `backend/app/services/agent/effective_config.py`): 新增「运行态预览」Tab，完整展示 Agent 最终生效的配置全貌——系统提示词、技能列表、工具清单、中间件链、知识源和策略配置。包含配置健康度检查和来源追踪，帮助管理员快速定位配置问题。

- **Popover 说明组件体系** (`frontend/components/ui/info-popover.tsx`, `frontend/components/features/config/*`): 新增 `InfoPopover` 通用悬停说明组件，以及 `MiddlewarePopover`（中间件专用）和 `ToolPopover`（工具专用）业务组件。在配置界面中，鼠标悬停即可查看中间件工作原理、触发条件、工具分类说明等详细信息，降低配置学习成本。

- **Agent 详情页共享布局** (`frontend/components/admin/agent-detail-layout.tsx`, `frontend/lib/config/agent-tabs.ts`): 创建统一的 `AgentDetailLayout` 组件和 `getAgentTabs` 配置函数，三个 Agent 配置路由（Agent 中心、单 Agent 模式、编排模式）共享相同的布局逻辑和 Tab 导航，代码量减少 80%。

### Changed

- **命名体系优化**: 删除模糊的"工作空间"概念，采用更直接的命名方式：
  - "单 Agent 工作空间" → **Agent 配置**
  - "编排中心" → **编排配置**
  - "Quick Setup" → **快速配置**
  - "进入工作空间" → **进入配置**

- **导航结构调整**: 快速配置从主菜单移至底部入口区域，与日常高频操作分离，保持主菜单简洁。

- **前端代码模块化** (`frontend/lib/timeline/*`, `frontend/types/*`): 
  - `effective-config/page.tsx` 拆分为 7 个子组件（722 行 → 129 行）
  - `timeline-utils.ts` 模块化重构（1001 行 → 9 行 + 5 个模块）
  - 新增 `types/quick-setup.ts` 和 `types/effective-config.ts` 类型定义

### Fixed

- **快速设置重复按钮** (`frontend/app/admin/quick-setup/steps/summary-step.tsx`): 修复 Summary 步骤显示重复"完成配置"按钮的问题。

---

## [0.1.13] - 2026-01-28

### Added

- **爬虫模块动态启用** (`backend/app/services/crawler/config_service.py`, `backend/app/routers/crawler.py`): 新增 `CrawlerConfigService` 配置服务，支持通过后台管理界面动态启用/禁用爬虫模块，无需修改 .env 配置文件。状态存储在数据库中，优先级高于环境变量。
- **爬虫设置页面** (`frontend/app/admin/settings/crawler/page.tsx`): 新增爬虫模块设置页面，提供启用/禁用开关、配置信息展示、统计概览和快捷操作入口。

### Changed

- **爬虫启动逻辑优化** (`backend/app/main.py`): 应用启动时始终初始化爬虫数据库表结构，根据数据库中的启用状态决定是否执行调度任务，支持后续动态启用。
- **爬虫路由动态检查** (`backend/app/routers/crawler.py`, `backend/app/routers/admin.py`): 所有爬虫 API 端点改为动态检查数据库中的启用状态，新增 `/api/v1/crawler/config`、`/config/enable`、`/config/disable` 配置管理接口。
- **系统状态接口优化** (`backend/app/routers/system.py`): `/api/v1/system/features` 接口改为动态获取爬虫启用状态，前端可实时感知模块状态变化。
- **爬虫管理页面优化** (`frontend/app/admin/crawler/page.tsx`): 未启用时显示友好的引导界面和启用按钮，替代原有的"请修改 .env"提示。
- **FeatureGuard 组件增强** (`frontend/components/features/feature-guard.tsx`): 添加 `loading` 状态支持，避免页面闪动；添加功能设置页面跳转按钮。
- **聊天输入框简化** (`frontend/components/features/chat/ChatRichInput.tsx`): 添加 `showToolbar` 属性，聊天页面隐藏格式工具栏，只保留发送按钮。
- **聊天界面背景统一** (`frontend/components/features/chat/ChatContent.tsx`): 移除输入区域独立背景色，与聊天区域保持一致。
- **推荐问题动态化** (`frontend/components/features/chat/ChatContent.tsx`): 移除前端写死的推荐问题 fallback，完全由后台 Agent 配置管理。
- **模式指示器重构** (`frontend/components/admin/mode-indicator.tsx`): 下拉菜单改为只显示当前状态和配置入口，点击跳转到对应配置页面而不是直接切换；只有在"模式设置"页面才能真正切换模式（带确认弹窗）。
- **路由分离** (`frontend/app/admin/single/page.tsx`, `frontend/app/admin/supervisor/page.tsx`): 单 Agent 和 Supervisor 使用独立路由，`/admin/workspace` 自动重定向到当前模式对应页面。
- **侧边栏菜单重构** (`frontend/components/admin/admin-sidebar.tsx`): 按模式显示不同菜单内容，移除 ModeIndicator 组件，在底部添加模式切换按钮（带确认弹窗）。
- **提示词 Markdown 渲染** (`frontend/app/globals.css`): 添加 `@tailwindcss/typography` 插件，修复提示词内容显示缺少 Markdown 样式的问题。

---

## [0.1.12] - 2026-01-28

### Added

- **前端模式感知架构** (`frontend/stores/mode-store.ts`, `frontend/components/admin/mode-indicator.tsx`): 新增全局模式状态管理 Store，支持单 Agent 与 Supervisor 两种运行模式的切换与持久化。新增模式指示器组件，侧边栏顶部显示当前运行模式。
- **统一工作空间入口** (`frontend/app/admin/workspace/*`): 新增 `/admin/workspace` 工作空间页面，作为模式感知的统一编辑入口。单 Agent 模式显示当前 Agent 快捷配置入口，Supervisor 模式显示编排架构可视化与子 Agent 列表。
- **模式设置页面** (`frontend/app/admin/settings/mode/page.tsx`): 新增专门的模式切换页面，提供详细的模式说明与切换确认流程。
- **仪表盘模式状态卡片** (`frontend/app/admin/page.tsx`): 仪表盘顶部新增运行模式状态卡片，直观显示当前模式并提供快捷入口。
- **前端模式感知架构设计文档** (`docs/architecture/frontend-mode-aware-design.md`): 新增详细的架构设计文档，包含问题分析、设计原则、页面结构、数据流设计与实施路线图。

### Changed

- **侧边栏模式感知** (`frontend/components/admin/admin-sidebar.tsx`): 重构侧边栏支持模式感知，Supervisor 模式下隐藏 Agent 切换器与 Agent 控制台菜单，单 Agent 模式下正常显示。新增工作空间高亮入口。

---

## [0.1.11] - 2026-01-09

### 2026-01-27 (UTC+08:00)

#### Added

- **提示词统一管理架构** (`backend/app/prompts/*`, `backend/app/routers/prompts.py`, `frontend/app/admin/prompts/*`): 新增 `PromptRegistry` 提示词注册表，支持默认值 + 数据库覆盖，提供 CRUD、reset 等完整管理功能。前端新增富文本编辑器组件，支持变量高亮与实时预览。
- **Quick Setup 模式选择** (`frontend/app/admin/quick-setup/*`): 新增 Agent 模式选择功能（Supervisor/Product/FAQ/KB），优化状态卡片展示与连接测试 UX，支持分步骤进度显示。

#### Changed

- **数据库 Provider 模式** (`backend/app/core/db/*`): 统一爬虫/Checkpoint 数据库使用 Provider 模式，新增 `get_session` 别名保持向后兼容。
- **SQLite 防死锁优化** (`backend/app/core/database.py`): 优化 SQLite 连接配置，减少并发场景下的死锁风险。

#### Fixed

- **前端 Hydration 错误** (`frontend/components/*`): 修复多个 SSR hydration 问题，包括 Tiptap 编辑器 `immediatelyRender`、TabsTrigger `asChild`、AlertDialogDescription `p` 嵌套等。
- **提示词 API 路径** (`backend/app/routers/prompts.py`): 修复路由前缀配置问题。
- **Agent 更新接口** (`backend/app/routers/agents.py`): 修复 `knowledge_config` 关联加载问题。

### 2026-01-26 (UTC+08:00)

#### Added

- **Agent 技能系统** (`backend/app/services/skill/*`, `backend/app/routers/skills.py`, `backend/app/models/skill.py`): 实现完整的 Agent 可扩展技能系统，包括 `SkillService`（CRUD、Agent 关联）、`SkillGenerator`（AI 智能生成）、`SkillRegistry`（运行时缓存）、`SkillInjector`（技能注入）。
- **LLM 配置后台管理** (`frontend/app/admin/settings/*`): 新增 LLM/Embedding/Rerank 模型配置管理界面，支持动态切换与测试连接。

#### Fixed

- **集成测试问题** (`backend/tests/*`): 修复 `lru_cache` 缓存、asyncio 事件循环绑定、日志配置等集成测试问题。

### 2026-01-22 (UTC+08:00)

#### Added

- **三套聊天主题 + 深色模式** (`frontend/stores/theme-store.ts`, `frontend/components/features/chat/*`): 新增 Minimal、Ethereal、Industrial 三种聊天界面风格，全面支持深色模式切换。
- **Markdown 统一渲染** (`frontend/components/ui/markdown/*`): 统一 Markdown 输入与渲染组件，支持代码高亮、表格、任务列表等扩展语法。

### 2026-01-20 (UTC+08:00)

#### Added

- **Supervisor 监督者模式** (`backend/app/services/agent/*`): 新增多 Agent 编排能力，支持 Supervisor Agent 协调多个子 Agent 协同工作，实现复杂任务分解与路由。
- **滑动窗口 & 噪音过滤 & 关键信息摘要** (`backend/app/services/agent/middleware/*`): 新增三个中间件：`SlidingWindowMiddleware`（上下文窗口裁剪）、`NoiseFilterMiddleware`（工具输出噪音过滤）、`SummarizationBroadcastMiddleware`（关键信息压缩摘要）。

### 2026-01-12 (UTC+08:00)

#### Changed

- **统一品牌名称** (`README.md`, `frontend/*`, `backend/*`): 将项目品牌从 "EmbedAI Agent" 统一更名为 "EmbedEase AI"，更新所有相关文档与界面文案。

### 2026-01-09 17:40 (UTC+08:00)

#### Added

- **产品落地页** (`frontend/app/landing/*`): 新增产品官网落地页，展示核心功能、使用场景与转化流程，支持 CTA 按钮与演示视频入口。
- **多智能体系统架构** (`backend/app/services/agent/*`, `backend/app/models/agent.py`): 重构 Agent 架构，支持多 Agent 类型（Product/FAQ/KB/Custom），实现模块化设计与配置驱动的 Agent 创建。
- **Quick Setup 一站式引导** (`backend/app/routers/quick_setup.py`, `backend/app/services/quick_setup/*`, `frontend/app/admin/quick-setup/*`): 新增可视化配置向导，支持 3 步完成 Agent 创建（选择类型 → 配置知识源 → 设置开场白），降低非技术用户使用门槛。
- **Agent 开场白系统** (`backend/app/models/agent.py`, `frontend/components/features/chat/*`): 支持多渠道开场白配置（Web/嵌入组件/客服），可设置触发条件、延迟时间、CTA 按钮等。
- **推荐问题系统** (`backend/app/models/agent.py`, `backend/app/routers/agents.py`, `frontend/components/features/chat/*`): 支持为 Agent 配置推荐问题，提供热度统计与智能排序，引导用户快速提问。
- **PostgreSQL 数据库支持** (`backend/app/core/database.py`, `backend/.env.example`): 新增多数据库后端架构，支持 SQLite 和 PostgreSQL 切换，生产环境可使用 PostgreSQL 提升性能。
- **消息撤回与编辑功能** (`backend/app/routers/chat.py`, `backend/app/services/conversation.py`): 支持客服消息撤回、编辑与重新生成，优化客服工作流。
- **图片上传与 OCR 识别** (`backend/app/routers/ocr.py`, `backend/app/routers/upload.py`, `frontend/components/features/chat/*`): 支持多模态对话，用户可上传图片并进行 OCR 文字识别。
- **消息分页查询接口** (`backend/app/routers/conversations.py`): 优化历史消息加载性能，支持分页查询与懒加载。
- **Agent 记忆配置与预览** (`backend/app/routers/agents.py`, `frontend/app/admin/agents/*`): 支持查看用户记忆数据、配置记忆策略、预览提示词效果。
- **聊天主题系统** (`frontend/stores/theme-store.ts`, `frontend/components/features/chat/*`): 新增 Ethereal 与 Industrial 两种聊天界面风格，支持动态切换。
- **健康检查系统** (`backend/app/routers/health.py`, `backend/app/core/health.py`): 新增系统健康检查端点，监控 Qdrant、数据库、LLM API 等依赖状态。
- **管理后台设置中心** (`backend/app/routers/admin.py`, `frontend/app/admin/settings/*`): 提供系统配置概览、中间件默认值查询、原始配置导出等功能。
- **消息响应耗时追踪** (`backend/app/models/message.py`, `backend/app/services/agent/middleware/logging.py`): 记录每条消息的 LLM 响应耗时，支持性能分析。
- **默认 Agent 配置注入** (`backend/app/core/config.py`, `backend/app/services/agent/bootstrap.py`): 支持通过环境变量或配置文件定义默认 Agent，启动时自动初始化。
- **FAQ 高级筛选与统计** (`backend/app/routers/agents.py`, `frontend/app/admin/faq/*`): 新增 FAQ 分类统计、最近更新追踪、智能合并建议等功能。
- **客服工作台热度排序** (`backend/app/services/support/heat_score.py`, `frontend/app/support/*`): 基于等待时长、消息数、用户活跃度等维度计算会话热度，优化客服优先级管理。
- **Agent 激活机制** (`frontend/contexts/agent-context.tsx`, `frontend/components/admin/agent-switcher.tsx`): 支持全局激活 Agent，管理后台可快速切换当前工作的 Agent。
- **悬浮聊天气泡拖拽** (`frontend/components/features/embed/*`): 嵌入式组件支持拖拽与边缘吸附，优化移动端体验。

#### Changed

- **统一 API 路由前缀** (`backend/app/main.py`, `backend/app/routers/*`): 将所有 API 路由统一为 `/api/v1` 前缀，规范化接口版本管理。
- **Docker Compose 配置统一** (`docker-compose.yml`, `docker-compose.prod.yml`): 移除独立生产环境配置文件，统一使用 `docker-compose.yml` 并通过 profile 控制环境。
- **服务容器依赖注入** (`backend/app/core/dependencies.py`, `backend/app/core/container.py`): 新增服务容器统一管理依赖注入，优化 WebSocket 与路由层代码复用。
- **状态管理迁移至 Zustand** (`frontend/stores/*`, `frontend/hooks/*`): 将 Agent 与 Chat 状态管理从 Context 迁移到 Zustand Store，提升性能与可维护性。
- **优化爬虫模块错误处理** (`backend/app/routers/crawler.py`, `backend/app/core/health.py`): 统一服务不可用错误码，优化爬虫健康检查与功能检测。
- **日志系统增强** (`backend/app/core/logging.py`): 默认启用文件日志，新增全局异常钩子与 asyncio 事件循环异常处理器。
- **管理后台导航优化** (`frontend/app/admin/layout.tsx`): 调整侧边栏导航顺序，Agent 中心置顶并添加核心标签，优化用户体验。

#### Fixed

- **筛选器空值处理** (`frontend/app/admin/conversations/page.tsx`, `frontend/app/admin/crawler/sites/page.tsx`): 修复 Radix UI SelectItem 空字符串冲突，统一使用 `"all"` 作为默认值。
- **会话列表类型检查** (`frontend/app/page.tsx`, `frontend/lib/api/conversations.ts`): 新增数组类型检查，防止非数组类型导致的运行时错误。
- **Qdrant 连接失败处理** (`backend/app/core/qdrant.py`): 优化 Qdrant 客户端容错机制，连接失败时不阻塞应用启动。
- **SQLAlchemy 布尔比较** (`backend/app/repositories/message.py`): 使用 `.is_(False)` 和 `is None` 替代 `== False` 和 `== None`，符合最佳实践。

#### Docs

- 新增企业微信推送功能说明，强调嵌入组件转化率提升价值。
- 完善人工客服系统架构图，新增通知配置与在线状态管理流程。
- **Docker 一键部署指南** (`README.md`, `README_DOCKER.md`): 新增详细的 Docker 部署文档，优化快速开始章节结构。
- **README 重构** (`README.md`): 重写用户文档，强调四种 Agent 类型、三种对话模式、一站式引导等核心功能，面向非技术用户优化。

## [0.1.10] - 2026-01-04

### 2026-01-04 16:00 (UTC+08:00)

#### Added

- **工具调用追踪与消息元数据** (`backend/app/services/chat_stream.py`, `backend/app/models/message.py`, `backend/app/services/conversation.py`): 将 LangGraph 工具调用与模型 usage metadata 全量落库，暴露 `tool_calls` 表与 `message.extra_metadata`，方便历史回放、Token 统计与仪表盘分析。
- **消息送达 / 已读与在线状态** (`backend/app/models/message.py`, `backend/app/services/conversation.py`, `backend/app/routers/chat.py`): 记录消息送达、已读时间与当前在线用户/客服 ID，支持客服面板实时掌握多端状态。
- **客服双通道与嵌入式聊天 WebSocket** (`backend/app/services/chat_stream.py`, `backend/app/services/support/*`, `frontend/components/features/embed/*`): 嵌入式组件改为 WebSocket 长连推送，并允许在任意会话中一键切换人工客服；手动/自动交接均通过同一双通道广播。
- **管理后台基础路由** (`backend/app/routers/admin.py`): 提供统一的后台入口，为后续运营面板/统计视图铺路。

#### Changed

- **客服介入通知机制重构** (`backend/app/services/support/handoff.py`, `backend/app/services/websocket/*`): 从 SSE + 客户端轮询改为服务端 WebSocket 广播，移除客服端主动推送，保证所有状态更新按服务器时间线下发。
- **事件类型系统升级** (`backend/app/schemas/events.py`, `backend/app/services/agent/streams/response_handler.py`): 将 Agent 事件按生命周期重新分层，新增工具调用分组（Cluster）以便时间线展示，同时保留 start/end 精准配对。
- **爬虫数据库拆分与 WAL** (`backend/app/core/crawler_database.py`, `backend/app/models/crawler/*.py`): 将爬虫数据迁移至独立 SQLite 文件，默认启用 WAL、分离页面处理事务，避免影响主业务数据库并提升并发能力。
- **日志格式与转义** (`backend/app/core/logging.py`): 优化 loguru formatter，自动转义特殊字符，防止彩色输出被错误解析。

#### Fixed

- **WebSocket 连接稳定性** (`backend/app/services/websocket/manager.py`): 修复并发下的连接泄露与状态同步问题，避免客服端卡死或状态错乱。

#### Docs

- **客服配置指南** (`README.md`, `docs/support.md`): 补充企业微信 / Webhook 通知、人工介入开关与新 WebSocket 事件说明。

## [0.1.9] - 2025-12-24

### 2025-12-24 21:09 (UTC+08:00)

#### Added

- 新增爬虫模块配置与数据模型，支持自动发现商品并导入
- 新增 `scheduler` 模块，提供 TaskRegistry/TaskScheduler/TaskRunner 结构，支持单站点多任务调度
- 新增 `CrawlSiteTask` 及 `/scheduler/*` API，文档化扩展方式（`backend/app/scheduler/README.md`）
- 支持通过 `CRAWLER_SITES_JSON` 在配置文件中定义站点，应用启动时自动导入并注册定时任务
- 新增 `normalize_domain` / `generate_site_id` 工具与站点初始化器，保证不同子域名可作为独立站点
- `/crawler/sites` API 增加域名查重、ID 自动生成及系统站点删除保护
- **Agent 工具稳健性配置** (`backend/.env.example`, `backend/app/core/config.py`): 新增工具重试与调用次数限制配置（`AGENT_TOOL_RETRY_*`, `AGENT_TOOL_LIMIT_*`），并补全 TODO 规划开关及自定义提示/描述字段。
- **中间件扩展** (`backend/app/services/agent/agent.py`, `backend/app/services/agent/middleware/todo_broadcast.py`): 条件注入 `ToolRetryMiddleware`、`ToolCallLimitMiddleware`、`TodoListMiddleware`，并新增 `TodoBroadcastMiddleware` 在 todos 变更时向前端推送 SSE。
- **SSE 事件类型** (`backend/app/schemas/events.py`): 新增 `assistant.todos` 事件与 TODO payload 定义。
- **前端待办渲染** (`frontend/hooks/use-timeline-reducer.ts`, `frontend/types/chat.ts`, `frontend/components/features/chat/TimelineTodosItem.tsx`, `frontend/components/prompt-kit/todo-list.tsx`, `frontend/components/features/chat/ChatContent.tsx`, `frontend/components/features/chat/timeline/index.ts`): 时间线 reducer 支持 `assistant.todos`，新增 TodoList 组件与时间线项渲染，展示待办清单及状态。

#### Changed

- **TODO 历史保留** (`frontend/hooks/use-timeline-reducer.ts`): `assistant.todos` 事件不再查找并更新现有 item，而是每次推送都插入新的 TodoList，保留大模型在同一轮对话中的多次规划记录。

### 2025-12-24 18:05 (UTC+08:00)

#### Added

- **分类导航工具集** (`backend/app/services/agent/tools/list_all_categories.py`, `get_category_overview.py`, `list_products_by_category.py`): 新增「列出所有分类」「获取分类概览」「按分类列出商品」三款工具，支持查询类目规模、价格区间、热门关键词与代表商品，回答"有哪些分类 / 某分类有啥"的问题更加精准。
- **语义推荐工具集** (`find_similar_products.py`, `list_featured_products.py`, `list_products_by_attribute.py`): 新增「查找相似商品」「列出精选商品」「按属性关键词筛选商品」三款工具，结合向量检索与价格/标签/描述信息，为用户提供替代商品、主题推荐与特性过滤能力。
- **探索与链接工具** (`suggest_related_categories.py`, `get_product_purchase_links.py`): 新增「推荐相关分类」「获取商品购买链接」两款工具，可在无匹配结果时扩展联想、并直接返回可跳转的商品 URL。
- **Agent 工具注册** (`backend/app/services/agent/tools/__init__.py`, `backend/app/services/agent/agent.py`): 将上述 8 个工具全部注册进 Agent，配合既有搜索/对比/引导能力，共 13 个职能单一的工具可被模型自由组合，形成"分类概览 → 商品筛选 → 相似/精选推荐 → 购买链接"完整链路。

#### Changed

- **工具参数单一性校验** (`search_products.py`, `list_products_by_category.py`, `get_category_overview.py`, `find_similar_products.py`, `list_products_by_attribute.py`, `suggest_related_categories.py`): 在 6 个工具中增加运行时参数校验，检测逗号、顿号、换行等分隔符，防止模型一次性传入多个品类/分类/关键词导致检索失败。当检测到多值参数时，工具立即返回结构化错误提示，引导模型拆分为多次调用，确保每次工具调用保持单一职责，提升检索准确率。

## [0.1.8] - 2025-12-23

### 2025-12-23 17:33 (UTC+08:00)

#### Added

- **推理模型多态基座** (`backend/app/core/chat_models/base.py`, `backend/app/core/chat_models/__init__.py`): 新增 `ReasoningChunk` 数据结构与 `BaseReasoningChatModel.extract_reasoning()` 统一入口，Agent 通过多态接口即可获取推理增量，彻底移除对 `additional_kwargs["reasoning_content"]` 的依赖。
- **SiliconFlow 推理实现文档化** (`backend/app/core/chat_models/providers/reasoning_content.py`, `backend/app/core/chat_models/README.md`): 以 `SiliconFlowReasoningChatModel` 封装 `reasoning_content` 字段的提取流程，并补充多态架构设计/扩展指南，方便后续按平台扩展。
- **推理模型注册表** (`backend/app/core/chat_models/registry.py`): 引入 `REASONING_MODEL_REGISTRY`，集中声明 provider → 模型实现的映射，新增平台只需注册即可被自动选择。
- **右下角浮窗聊天组件** (`frontend/components/features/embed/FloatingChatWidget.tsx`, `frontend/components/features/embed/EmbedChatContent.tsx`, `frontend/app/layout.tsx`): 在开发体验页默认渲染可折叠的浮动聊天窗口，支持单会话清空按钮和最小化，方便快速演示。
- **嵌入式脚本打包管线** (`frontend/embed/entry.tsx`, `frontend/embed/EmbedWidget.tsx`, `frontend/embed/embed.css`, `frontend/embed/vite.config.ts`, `frontend/embed/demo.html`): 新增纯 JS Widget 入口与 UI，实现 `window.EmbedeaseAIChat.init()` API，并通过 Vite 打包为单文件 `embedeaseai-chat.js`，可直接在第三方站点以 `<script>` 内嵌。
- **构建脚本与依赖** (`frontend/package.json`): 添加 `pnpm build:embed` 命令及 `vite`、`@vitejs/plugin-react`、`terser` 依赖，确保嵌入脚本能够独立打包。
- **README 演示入口** (`README.md`): 在文档顶部加入 `docs/agent0.mp4` 演示视频按钮，访客打开仓库即可直接观看。
- **记忆专用模型配置** (`backend/app/core/config.py`, `backend/.env.example`, `backend/app/core/llm.py`, `backend/app/services/memory/fact_memory.py`, `backend/app/services/memory/graph_memory.py`): 引入 `MEMORY_MODEL/MEMORY_PROVIDER/MEMORY_API_KEY/MEMORY_BASE_URL` 配置与 `get_memory_model()`，记忆抽取可选用独立模型，避免与主聊天模型抢配额。

#### Changed

- **Agent 推理事件发送** (`backend/app/services/agent/agent.py`): SSE 推理增量改为调用 `model.extract_reasoning()`，兼容不同 provider 的推理字段并保留逐字符播报统计。
- **版本号** (`backend/pyproject.toml`, `backend/uv.lock`, `frontend/package.json`): bump 至 0.1.8，确保前后端版本保持一致。

#### Removed

- **OpenAI 推理实现与旧单测** (`backend/app/core/chat_models/providers/openai.py`, `backend/tests/test_reasoning_content_injection.py`): 删除旧的 OpenAI 专用逻辑与对应单测，为多态实现压缩冗余代码。

## [0.1.7] - 2025-12-22

### 2025-12-23 10:16 (UTC+08:00)

#### Added

- **上下文压缩配置与事件** (`backend/.env.example`, `backend/app/core/config.py`, `backend/app/schemas/events.py`): 默认开启 `SummarizationMiddleware`，新增触发阈值/保留条数/裁剪 token 配置，并定义 `context.summarized` SSE 事件 payload（包含压缩前后消息与 token 数）。
- **SummarizationBroadcastMiddleware** (`backend/app/services/agent/middleware/summarization_broadcast.py`): 封装 LangChain `SummarizationMiddleware`，捕获压缩结果并向前端推送 SSE，复用当前 token 计数器估算压缩收益。
- **前端上下文压缩可视化** (`frontend/types/chat.ts`, `frontend/hooks/use-timeline-reducer.ts`, `frontend/components/features/chat/timeline/TimelineContextSummarizedItem.tsx`, `frontend/components/features/chat/ChatContent.tsx`, `frontend/components/features/chat/timeline/index.ts`): 新增 `context.summarized` 事件类型、时间线 item 以及 UI 卡片，展示压缩前后消息/Token 变化。
- **Agent 工具稳健性配置** (`backend/.env.example`, `backend/app/core/config.py`): 新增工具重试与调用次数限制配置（`AGENT_TOOL_RETRY_*`, `AGENT_TOOL_LIMIT_*`），并补全 TODO 规划开关及自定义提示/描述字段。
- **中间件扩展** (`backend/app/services/agent/agent.py`, `backend/app/services/agent/middleware/todo_broadcast.py`): 条件注入 `ToolRetryMiddleware`、`ToolCallLimitMiddleware`、`TodoListMiddleware`，并新增 `TodoBroadcastMiddleware` 在 todos 变更时向前端推送 SSE。
- **SSE 事件类型** (`backend/app/schemas/events.py`): 新增 `assistant.todos` 事件与 TODO payload 定义。
- **前端待办渲染** (`frontend/hooks/use-timeline-reducer.ts`, `frontend/types/chat.ts`, `frontend/components/features/chat/TimelineTodosItem.tsx`, `frontend/components/prompt-kit/todo-list.tsx`, `frontend/components/features/chat/ChatContent.tsx`, `frontend/components/features/chat/timeline/index.ts`): 时间线 reducer 支持 `assistant.todos`，新增 TodoList 组件与时间线项渲染，展示待办清单及状态。

#### Changed

- **Agent 中间件声明式构建** (`backend/app/services/agent/agent.py`): 以 `MiddlewareSpec` 数据类集中声明中间件顺序/启用条件/工厂函数，并在注释表格中列出执行顺序，替代原先分散的 `insert/append` 逻辑。
- **System Prompt 升级** (`backend/app/services/agent/agent.py`): 三种模式的 system prompt 精简为核心原则 + 输出格式，不再列举具体工具或流程。
- **工具文档统一** (`backend/app/services/agent/tools/*.py`): `compare_products`、`get_product_details`、`filter_by_price`、`guide_user` docstring 统一使用“商品搜索能力/价格筛选能力”描述，示例与 Note 不再出现英文工具名。
- **Strict 模式执行逻辑** (`backend/app/services/agent/middleware/strict_mode.py`): 依据 ToolPolicy 判断最小工具调用次数、允许直接回答与回退提示，替代 prompt 层强制逻辑。
- **依赖版本** (`backend/pyproject.toml`, `backend/uv.lock`, `frontend/package.json`): bump 至 0.1.8 并同步锁定文件。

#### Removed

- **意图识别层** (`backend/app/services/agent/middleware/intent_recognition.py`, `backend/app/services/agent/intent_analyzer.py`, `backend/app/schemas/intent.py`): 删除规则/LLM 双重意图识别及工具过滤逻辑，改由策略层与模型自主判断。

### 2025-12-22 17:06 (UTC+08:00)

#### Added

- **Agent 工具稳健性配置** (`backend/.env.example`, `backend/app/core/config.py`): 新增工具重试与调用次数限制配置（`AGENT_TOOL_RETRY_*`, `AGENT_TOOL_LIMIT_*`），并补全 TODO 规划开关及自定义提示/描述字段。
- **中间件扩展** (`backend/app/services/agent/agent.py`, `backend/app/services/agent/middleware/todo_broadcast.py`): 条件注入 `ToolRetryMiddleware`、`ToolCallLimitMiddleware`、`TodoListMiddleware`，并新增 `TodoBroadcastMiddleware` 在 todos 变更时向前端推送 SSE。
- **SSE 事件类型** (`backend/app/schemas/events.py`): 新增 `assistant.todos` 事件与 TODO payload 定义。
- **前端待办渲染** (`frontend/hooks/use-timeline-reducer.ts`, `frontend/types/chat.ts`, `frontend/components/features/chat/TimelineTodosItem.tsx`, `frontend/components/prompt-kit/todo-list.tsx`, `frontend/components/features/chat/ChatContent.tsx`, `frontend/components/features/chat/timeline/index.ts`): 时间线 reducer 支持 `assistant.todos`，新增 TodoList 组件与时间线项渲染，展示待办清单及状态。

### Overview

- System prompt 与工具说明全面改为“能力描述”，彻底移除英文工具名曝光，配合策略层实现纯中文提示体验。
- strict/natural/free 模式的约束由 `ToolPolicy` 与中间件驱动，提示词仅描述角色原则。

### Added

- **ToolPolicy 配置层** (`backend/app/services/agent/policy.py`): 定义 natural/free/strict 策略（最小工具调用、允许直接回答、回退提示等），供 StrictModeMiddleware 使用。
- **Agent 工具执行配置** (`backend/app/core/config.py`, `backend/.env.example`): 新增 `AGENT_SERIALIZE_TOOLS` 配置项，支持控制工具调用是否串行执行（避免并发问题）。
- **串行工具执行中间件** (`backend/app/services/agent/middleware/sequential_tools.py`): 新增 `SequentialToolExecutionMiddleware`，当模型返回多个工具调用时强制按顺序执行。
- **中间件集成** (`backend/app/services/agent/agent.py`): 根据配置条件性地添加串行工具执行中间件到Agent流程。

### Changed

- **System Prompt 升级** (`backend/app/services/agent/agent.py`): 三种模式的 system prompt 精简为核心原则 + 输出格式，不再列举具体工具或流程。
- **工具文档统一** (`backend/app/services/agent/tools/*.py`): `compare_products`、`get_product_details`、`filter_by_price`、`guide_user` docstring 统一使用“商品搜索能力/价格筛选能力”描述，示例与 Note 不再出现英文工具名。
- **Strict 模式执行逻辑** (`backend/app/services/agent/middleware/strict_mode.py`): 依据 ToolPolicy 判断最小工具调用次数、允许直接回答与回退提示，替代 prompt 层强制逻辑。
- **依赖版本** (`backend/pyproject.toml`, `backend/uv.lock`, `frontend/package.json`): bump 至 0.1.7 并同步锁定文件。

### Removed

- **意图识别层** (`backend/app/services/agent/middleware/intent_recognition.py`, `backend/app/services/agent/intent_analyzer.py`, `backend/app/schemas/intent.py`): 删除规则/LLM 双重意图识别及工具过滤逻辑，改由策略层与模型自主判断。

## [0.1.6] - 2025-12-19

### Overview

本版本聚焦于「记忆系统 MVP」，完善了三类记忆能力及其编排能力：

1. **LangGraph Store（长期画像）**：用于跨会话维度存储用户偏好、预算范围、任务进度等结构化信息，为 Agent 提供稳定的上下文基线。
2. **Fact Memory（事实型记忆）**：自动从对话中提取事实，去重后写入 SQLite（元数据）与独立 Qdrant 集合 `memory_facts`（向量），支持回放与高相似度召回。
3. **Graph Memory（图谱记忆）**：以 JSONL 形式记录实体-关系-观察，适合描述“用户与商品/计划/家庭成员之间”的结构化链接。
4. **Memory Orchestration Middleware**：在请求开始阶段注入画像 + 事实 + 图谱，在请求结束后异步写入记忆，实现闭环流水线。

### Added

- **记忆向量存储模块**：新增 `vector_store.py`，负责初始化/缓存 Qdrant 客户端，自动创建独立集合 `memory_facts`，并对嵌入模型进行统一管理。
- **记忆配置扩展**：`.env.example` 与 `Settings` 增加 `MEMORY_FACT_COLLECTION`、`MEMORY_FACT_SIMILARITY_THRESHOLD` 等参数，允许针对不同环境调整集合名称与过滤阈值。
- **文档补全**：`backend/app/services/memory/README.md` 新增“多层混合记忆 + 中间件编排”说明，详细描述 LangGraph Store、Fact Memory（SQLite + Qdrant）、Graph Memory、Orchestration 中间件的职责与交互流程。
- **记忆抽取 SSE 事件** (`backend/app/schemas/events.py`, `backend/app/services/memory/middleware/orchestration.py`)：新增 `memory.extraction.start/complete` 事件类型及 payload，在记忆抽取开始/完成时向前端推送进度与统计信息，便于实时展示记忆写入状态。
- **用户画像服务** (`backend/app/services/memory/profile_service.py`)：
  - 新增 `ProfileService` 统一管理画像的读写与更新，支持从事实/图谱自动提取结构化画像信息。
  - 规则引擎支持自动提取：预算区间（`budget_min/max`）、品类偏好（`favorite_categories`）、品牌偏好（`custom_data.brand_preferences`）、语气偏好（`tone_preference`）、任务进度（`task_progress`）。
  - 新增 `ProfileUpdateSource` 枚举区分更新来源（fact/graph/user_input/system），支持来源优先级冲突解决。
- **画像更新 SSE 事件** (`backend/app/schemas/events.py`)：新增 `memory.profile.updated` 事件类型及 `MemoryProfileUpdatedPayload`，在画像更新时向前端推送更新字段列表和来源。
- **用户画像 API** (`backend/app/routers/users.py`)：
  - `GET /api/v1/users/{user_id}/profile`: 获取用户画像
  - `POST /api/v1/users/{user_id}/profile`: 更新用户画像（用户显式设置）
  - `DELETE /api/v1/users/{user_id}/profile`: 删除用户画像

### Changed

- **事实型长期记忆**：
  - `FactMemoryService` 写入阶段同时更新 SQLite（元数据 + 历史记录）与 Qdrant 向量；检索阶段改为调用 Qdrant `similarity_search_with_score`，并在失败时自动回退至关键词搜索。
  - `update_fact` / `delete_fact` 同步维护 Qdrant 向量数据，确保与 SQLite 状态一致。
  - `Fact` 数据模型移除本地 `embedding` 字段，由 Qdrant 负责托管向量，避免重复存储与手工余弦计算。
- **记忆检索阈值语义** (`backend/app/core/config.py`, `backend/app/services/memory/fact_memory.py`)：将 `MEMORY_FACT_SIMILARITY_THRESHOLD` 明确为“距离阈值（越小越相似）”，检索逻辑改为过滤距离大于阈值的结果，与 Qdrant 的 Distance 语义保持一致。
- **记忆编排中间件** (`backend/app/services/memory/middleware/orchestration.py`)：
  - 新增 `MemoryWriteResult` 结构，统一记录事实/实体/关系/画像写入统计及错误信息。
  - 将记忆写入流程从 `awrap_model_call` 挪至 `aafter_agent` 钩子，仅在整轮 Agent 结束后执行一次，避免多次重复写入并保证抽取使用独立 LLM 调用。
  - 增加 SSE 通知包装器，在记忆抽取开始与完成时通过 `StreamEventType` 向前端发送实时状态（含耗时与写入数量），支持同步/异步两种执行模式。
  - `_process_memory_write` 在事实/图谱抽取后自动调用 `ProfileService` 更新用户画像，并通过 SSE 推送 `memory.profile.updated` 事件。
- **事实记忆服务** (`backend/app/services/memory/fact_memory.py`)：新增 `get_recent_facts()` 方法，支持获取用户最近添加的事实用于画像更新。
- **记忆编排说明**：README 中的数据流图、工作流示例更新为“注入记忆 → Agent 推理 → 异步写入 SQLite + Qdrant”的完整闭环，并补充回退机制、并发安全策略。

## [0.1.5] - 2025-12-19

### 2025-12-19 11:45 (UTC+08:00)

- **系统提示词结合库状态（商品库画像注入）** (`backend/scripts/import_products.py`, `backend/app/services/catalog_profile.py`, `backend/app/services/agent/agent.py`):
  - 导入时对商品数据做源头标准化，并生成商品库画像（Top 类目/价位范围）与短提示词（<=100 字）
  - 新增 `app_metadata` KV 表用于持久化存储 `catalog_profile.stats` / `catalog_profile.prompt_short` / `catalog_profile.fingerprint`
  - Agent 初始化时读取画像提示词并拼接到 system prompt（带 TTL 缓存），fingerprint 变化时清空所有 mode 的 agent 缓存触发重建
  - 新增配置项：`CATALOG_PROFILE_ENABLED` / `CATALOG_PROFILE_TTL_SECONDS` / `CATALOG_PROFILE_TOP_CATEGORIES`（并补充 `.env.example`）
  - 新增单测：`tests/test_catalog_profile.py`

### 2025-12-19 10:50 (UTC+08:00)

#### ⏱️ 时间线渲染重构 (Timeline-based Chat Rendering)

实现 **Cursor/Windsurf 风格的时序时间线渲染**，SSE 事件按到达顺序逐条显示，同一个 span 的 start/end 更新同一张卡片。

##### 🔧 后端改动 (Backend Changes)

- **事件 payload 增强** (`backend/app/schemas/events.py`):
  - `ToolStartPayload` / `ToolEndPayload` 新增 `tool_call_id` 字段，支持前端配对 start/end 事件
  - `ToolEndPayload` 新增 `status` 字段（`success` / `error` / `empty`）

- **工具 tool_call_id 注入** (`backend/app/services/agent/tools/*.py`):
  - 5 个工具（`search_products` / `get_product_details` / `filter_by_price` / `compare_products` / `guide_user`）均生成并传递 `tool_call_id`



##### ✨ 前端改动 (Frontend Changes)

- **Timeline Reducer** (`frontend/hooks/use-timeline-reducer.ts`):
  - 新增纯函数 reducer，处理 7 种 `TimelineItem` 类型
  - 支持按 `id` 快速定位更新（O(1)）
  - 推理/正文增量自动归属当前运行的 LLM 调用

- **Timeline 组件** (`frontend/components/features/chat/timeline/`):
  - `TimelineLlmCallItem`: 模型调用状态卡片（思考中/完成/失败）
  - `TimelineToolCallItem`: 工具执行状态卡片
  - `TimelineReasoningItem`: 推理内容（流式，可折叠）
  - `TimelineContentItem`: 正文内容（流式）
  - `TimelineProductsItem`: 商品卡片网格
  - `TimelineUserMessageItem`: 用户消息气泡
  - `TimelineErrorItem`: 错误提示条

- **新版 Hook 与组件** (`frontend/hooks/use-chat-v2.ts`, `frontend/components/features/chat/ChatContentV2.tsx`):
  - 使用 reducer 管理 timeline 状态
  - 渲染 timeline items 而非消息列表

##### 📡 时间线 Item 类型 (TimelineItem Types)

| 类型 | 说明 |
|------|------|
| `user.message` | 用户消息气泡 |
| `llm.call` | 模型调用状态卡片（start 插入、end 更新） |
| `assistant.reasoning` | 推理内容（流式，归属当前 LLM call） |
| `assistant.content` | 正文内容（流式） |
| `tool.call` | 工具执行状态卡片（start 插入、end 更新） |
| `assistant.products` | 商品卡片网格 |
| `error` | 错误条 |

##### 🎯 事件流示例 (Event Flow Example)

```
09:10:01 llm.call.start      → 插入「模型思考中」卡片
09:10:02 reasoning.delta     → 在卡片下方显示推理内容
09:10:10 llm.call.end        → 更新卡片为「思考完成 · 9000ms」
09:10:11 tool.start          → 插入「商品搜索中」卡片
09:10:12 tool.end            → 更新卡片为「搜索完成 · 5项 · 1234ms」
09:10:13 llm.call.start      → 插入新的「模型思考中」卡片
...
```

---

## [0.1.4] - 2025-12-17

### 2025-12-18 16:59 (UTC+08:00)

#### 🧭 新增聊天模式 natural/free/strict (Chat Modes)

- **配置驱动默认模式** (`backend/app/core/config.py`, `backend/.env.example`):
  - 新增 `CHAT_MODE` 配置项（`natural` / `free` / `strict`），用于控制默认聊天模式
  - `.env.example` 增加 `CHAT_MODE=natural` 示例与说明

- **请求级别覆盖默认模式** (`backend/app/schemas/chat.py`):
  - `ChatRequest` 新增 `mode` 字段（可选），支持按请求切换模式
  - 增加 `effective_mode`：请求优先，否则回退到 `settings.CHAT_MODE`

- **模式透传到运行时上下文** (`backend/app/services/streaming/context.py`, `backend/app/services/chat_stream.py`, `backend/app/routers/chat.py`):
  - `ChatContext` 新增 `mode` 字段，使 middleware/tools 可读取当前模式
  - `ChatStreamOrchestrator` 接收 `mode` 并注入到 `ChatContext`

- **Agent 按模式选择 Prompt/Middleware** (`backend/app/services/agent/agent.py`):
  - 新增三份 system prompt：`NATURAL_SYSTEM_PROMPT` / `FREE_SYSTEM_PROMPT` / `STRICT_SYSTEM_PROMPT`
  - Agent 实例按 mode 缓存（同一进程内不同模式互不影响）
  - `free` 模式禁用意图识别工具过滤（避免强制引导回商品话题）

- **strict 模式强约束与受控失败** (`backend/app/services/agent/middleware/strict_mode.py`, `backend/app/services/chat_stream.py`):
  - 新增 `StrictModeMiddleware`：strict 模式下若模型未发起工具调用则替换为“受控失败”提示
  - Orchestrator 增加 strict 兜底：若全程未出现 `tool.end`，落库前用受控失败消息替换内容（最终保险）

### 2025-12-18 16:22 (UTC+08:00)

#### 🐛 修复 products 污染导致空卡片 (Fix Empty ProductCard Rendering)

- **后端 products 解析修复** (`backend/app/services/agent/agent.py`):
  - ToolMessage 解析 products 时使用临时变量，避免 normalize 失败时污染 `products_data`
  - 防止 `assistant.final` 携带非商品对象（如 `{"products": [], "message": ...}`）导致前端渲染空 `ProductCard` / `product.id` 缺失日志

### 2025-12-18 15:43 (UTC+08:00)

#### 🎨 前端 SSE 展示重构 (Frontend SSE Display Refactor)

- **消息结构升级** (`frontend/hooks/use-chat.ts`):
  - `timeline` 简化为仅保留消息项（不再插入工具/LLM 卡片）
  - 将 `llm`（思考中/完成/耗时/错误）、`toolsSummary`（工具执行摘要）、`trace`（运行轨迹）写入到 `ChatMessage`
  - `llm.call.start` 到达时自动插入空的 reasoning segment，确保推理折叠标题立即出现并承载状态

- **UI 展示重构** (`frontend/components/features/chat/ChatContent.tsx`):
  - 推理折叠标题右侧常驻：运行轨迹入口 + LLM 状态 + 工具摘要
  - 运行轨迹使用 `Steps` 面板展示（LLM / Tool / Products / Error 全部可追溯）
  - 移除正文区域 “思考中...” 占位，避免主消息流被过程事件打断

### 2025-12-18 12:35 (UTC+08:00)

#### 🧠 推理内容与流式兼容 (Reasoning & Streaming Compatibility)

##### ✨ 核心改进 (Core Improvements)

- **推理内容统一归一化**: 同时兼容 LangChain OpenAI 的两条 streaming 路径（Chat Completions vs Responses API），统一将推理内容写入 `AIMessageChunk.additional_kwargs["reasoning_content"]`
- **向后兼容增强**: 兼容 LangChain v0 compat 格式（`additional_kwargs["reasoning"]` 为 dict），自动提取并转换为 `reasoning_content` 字符串

##### 🔧 技术实现 (Technical Changes)

- **推理内容归一化中枢** (`backend/app/core/chat_models/base.py`):
  - 覆盖 `_convert_chunk_to_generation_chunk`：对 Chat Completions streaming 的 raw dict chunk 注入 `reasoning_content`
  - 覆盖 `_stream_responses` / `_astream_responses`：对 Responses API streaming 的产物做后处理注入，避免路径 B 绕过注入点
  - 提供可选覆盖钩子 `_extract_reasoning_content`：允许平台特定提取逻辑扩展，但默认同时支持 `reasoning` / `reasoning_content`
  - 补充特别详细的数据结构说明：解释两条路径的原始/中间/最终结构与前因后果，降低维护成本

- **去冗余且保留兼容** (`backend/app/core/chat_models/providers/*.py`):
  - `OpenAIReasoningChatModel` 与 `ReasoningContentChatModel` 保留类名与导入路径，但提取逻辑统一委托给基类默认实现，减少重复代码

##### 🧩 SSE 事件职责拆分与清晰化 (SSE Middleware Responsibility)

- **职责拆分**: `LoggingMiddleware` 仅负责 logger 记录，不再发送 `llm.call.start/end` SSE 事件；对应 SSE 事件由 `SSEMiddleware` 统一负责
- **文件命名澄清**: 将 LLM 调用级别 SSE 中间件实现明确为 `llm_call_sse.py`，并更新引用与文档（删除旧 `sse_events.py`）

##### ✅ 测试 (Tests)

- 新增并恢复单测：
  - `tests/test_reasoning_content_injection.py`: 覆盖 Chat Completions（`reasoning`/`reasoning_content`）、Responses content blocks、v0 compat dict 解析与不覆写行为
  - `tests/test_llm_call_sse_middleware.py`: 覆盖 SSEMiddleware 成功/异常路径的 start/end 事件
  - 更新 `tests/test_llm_logging_middleware.py`: 断言 LoggingMiddleware 不 emit SSE 事件

### 2025-12-17 18:00 (UTC+08:00)

#### 🔧 日志与序列化优化 (Logging & Serialization Improvements)

##### ✨ 核心改进 (Core Improvements)

- **ChatContext 重构**: 将 `ChatContext` 从 `@dataclass` 重构为 Pydantic `BaseModel`，解决 Pydantic 序列化警告
- **日志记录增强**: 优化工具调用日志记录，确保 `tool_calls.items` 完整显示，避免深层嵌套被截断
- **工具函数签名优化**: 使用 `Annotated` 类型注解改进工具函数参数，提升代码清晰度和类型安全

##### 🔧 技术实现 (Technical Changes)

- **ChatContext 重构** (`backend/app/services/streaming/context.py`):
  - 从 `@dataclass(frozen=True, slots=True)` 改为 Pydantic `BaseModel`
  - 使用 `Field(exclude=True, repr=False)` 排除 `emitter` 字段的序列化
  - 配置 `ConfigDict` 支持 `arbitrary_types_allowed=True` 和 `frozen=True`
  - 解决 LangChain 内部序列化 `ModelRequest`/`ToolRuntime` 时的 Pydantic 警告

- **日志记录优化** (`backend/app/core/logging.py`, `backend/app/services/agent/middleware/logging.py`):
  - 移除 `ChatContext` 的特殊处理逻辑，直接使用 Pydantic 的 `model_dump()` 方法
  - 增强 `_summarize_tool_calls` 函数，添加 `args_preview` 显示参数预览
  - 新增 `_ensure_serializable` 函数，确保对象完全序列化为基本类型
  - 调整 `_safe_for_logging` 函数，增加深度限制并特殊处理 `tool_calls.items`
  - 在日志记录前完全序列化 `response_data`，避免嵌套结构被截断

- **工具函数改进** (`backend/app/services/agent/tools/`):
  - 所有工具函数使用 `Annotated` 类型注解替代简单类型
  - 简化工具启动和结束事件的记录逻辑
  - 删除不必要的输入模式类，精简代码库
  - 增强错误处理和日志记录

##### 🐛 Bug 修复 (Bug Fixes)

- 修复 `tool_calls.items` 在日志中显示为 `['...']` 的问题
- 修复 Pydantic 序列化警告：`PydanticSerializationUnexpectedValue(Expected 'none' - serialized value may not be as expected [field_name='context'])`

##### 📝 代码质量 (Code Quality)

- 改进类型注解，提升代码可读性和 IDE 支持
- 统一日志记录格式，确保关键信息完整显示
- 优化序列化逻辑，避免深层嵌套导致的日志截断

---

## [0.1.3] - 2025-12-17

### 🔄 多 LLM 提供商支持 (Multi-Provider Support)

#### ✨ 核心改进 (Core Improvements)

- **多提供商架构**: 重构配置系统，支持 OpenAI、Anthropic、DeepSeek、SiliconFlow 等多个 LLM 提供商
- **统一配置接口**: 使用通用的 `LLM_*` 配置变量替代平台特定的 `SILICONFLOW_*` 变量
- **灵活混合配置**: 支持为 LLM、Embeddings、Rerank 使用不同的提供商，优化成本和性能
- **自动迁移工具**: 提供 `migrate_env.py` 脚本，自动迁移旧配置到新格式

#### 🔧 技术实现 (Technical Changes)

- **配置层重构** (`backend/app/core/config.py`):
  - 新增 `LLM_PROVIDER`、`LLM_API_KEY`、`LLM_BASE_URL`、`LLM_CHAT_MODEL`
  - 新增 `EMBEDDING_PROVIDER`、`RERANK_PROVIDER` 支持独立配置
  - 添加 `effective_*` 属性方法，自动回退到主配置
  
- **Chat Models 重构** (`backend/app/core/chat_models/`):
  - 重命名 `providers/siliconflow.py` → `providers/reasoning_content.py`
  - 按推理字段类型分类而非平台名称
  - 更新注册机制，支持多平台自动匹配

- **核心模块更新**:
  - `backend/app/core/llm.py`: 支持多提供商初始化
  - `backend/app/core/rerank.py`: 通用化 Rerank 客户端
  - `backend/app/core/models_dev.py`: 支持动态 provider_id

#### 📝 配置变更 (Configuration Changes)

**旧配置格式**:
```bash
SILICONFLOW_API_KEY=sk-xxx
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1
SILICONFLOW_CHAT_MODEL=moonshotai/Kimi-K2-Instruct
```

**新配置格式**:
```bash
LLM_PROVIDER=siliconflow
LLM_API_KEY=sk-xxx
LLM_BASE_URL=https://api.siliconflow.cn/v1
LLM_CHAT_MODEL=moonshotai/Kimi-K2-Instruct
```

#### 🛠️ 迁移指南 (Migration Guide)

1. **自动迁移** (推荐):
   ```bash
   cd backend
   python migrate_env.py
   ```

2. **手动迁移**:
   - 将所有 `SILICONFLOW_*` 变量重命名为对应的通用变量
   - 添加 `LLM_PROVIDER=siliconflow`
   - 参考 `backend/.env.example` 查看完整配置

#### 📚 文档更新 (Documentation)

- 更新 `README.md` 添加多提供商配置说明和示例
- 更新 `backend/app/core/chat_models/README.md` 反映新架构
- 创建 `backend/.env.example` 提供配置模板

#### ⚠️ 破坏性变更 (Breaking Changes)

- 所有 `SILICONFLOW_*` 环境变量已废弃，需要迁移到新的通用变量
- 旧配置文件不兼容，必须使用迁移脚本或手动更新

#### 🎯 优势 (Benefits)

- **灵活性**: 轻松切换不同 LLM 提供商
- **成本优化**: 为不同功能选择性价比最高的提供商
- **可扩展性**: 添加新提供商只需最小改动
- **供应商独立**: 不被单一供应商锁定

---

## [0.1.3] - 2025-12-16

### 🚀 检索与推荐能力增强 (Retrieval Improvements)

- **增强检索链路**: 新增混合检索策略（向量检索 + 关键词过滤 + 相关性重排序）
- **Rerank 重排序**: 对接 Rerank API，失败自动回退本地打分；新增配置项 `RERANK_*`

### 🧠 意图识别与工具选择 (Intent & Tooling)

- **意图识别中间件**: 基于规则识别意图，动态过滤可用工具，并注入意图上下文提示
- **结构化意图模型**: 新增 `IntentAnalysis` / `IntentType` / `INTENT_TO_TOOLS`
- **工具体系模块化**: 原 `tools.py` 拆分为 `tools/` 包（`search_products` / `get_product_details` / `compare_products` / `filter_by_price`）并补充说明文档

### 🛑 流式对话可中断 (Streaming Abort)

- **前端支持停止生成**: `AbortController` + UI “停止”按钮；中断后移除未完成的 assistant 消息
- **后端中断检测**: 通过 `request.is_disconnected()` / `CancelledError` 及时停止生成，且不落库不完整消息
- **数据库会话稳定性**: 取消/异常路径 rollback 更稳健，避免二次异常

### 🔧 工程与可观测性 (Engineering)

- **日志稳定性增强**: 复杂对象安全序列化，修复 loguru enqueue/pickle 问题；异常栈转义；日志 file 路径显示为相对路径

#### ⚠️ 行为变更 (Behavior Changes)

- 客户端主动中断后，后端不会保存未完成的 assistant 消息（前端已同步适配）

## [0.1.2] - 2025-12-16

### 🔧 技术改进 (Technical Improvements)

- **版本管理脚本优化**: 修复 `version.sh` 脚本语法问题，替换为更稳定的 Python 版本管理脚本 `update_version.py`
- **构建系统改进**: 优化版本自动更新流程，提高发布效率

## [0.1.1] - 2025-12-16

### 🚀 架构重构：SSE事件系统职责分离

#### ✨ 核心改进 (Core Improvements)

- **统一流式事件协议**: 新增 `StreamEvent` envelope，支持版本化扩展
- **职责分离架构**: Agent业务逻辑、事件编排、SSE传输完全解耦
- **Context事件注入**: 工具和中间件可实时emit事件，实现多源事件合流
- **类型安全提升**: 事件类型枚举化，减少魔法字符串，提高可维护性

#### 🔧 技术实现 (Technical Changes)

- **新增模块**:
  - `backend/app/schemas/events.py`: 事件类型枚举与payload类型定义
  - `backend/app/schemas/stream.py`: 统一流式事件协议
  - `backend/app/services/streaming/`: SSE编解码与Context注入
  - `backend/app/services/chat_stream.py`: 聊天流编排核心

- **重构模块**:
  - `backend/app/services/agent/`: 输出domain events而非SSE格式
  - `backend/app/routers/chat.py`: 简化路由层职责
  - `frontend/types/chat.ts`: 协议类型升级，支持判别联合
  - `frontend/hooks/use-chat.ts`: 适配新事件渲染逻辑

#### 📡 事件协议升级 (Event Protocol)

- **新增事件类型**:
  - `meta.start`: 流开始，提供message_id对齐
  - `assistant.delta`: 文本增量
  - `assistant.reasoning.delta`: 推理内容增量
  - `assistant.products`: 商品数据
  - `assistant.final`: 最终完整状态
  - `tool.start/end`: 工具执行状态
  - `llm.call.start/end`: LLM调用状态

- **协议特性**:
  - 统一envelope: `v/id/seq/ts/conversation_id/message_id/type/payload`
  - 版本化支持: `v`字段预留协议升级空间
  - 类型安全: 前端TypeScript判别联合自动推导payload结构

#### 🏗️ 架构优势 (Architecture Benefits)

- **可扩展性**: 新增事件类型只需在枚举中添加，无需改动传输层
- **职责清晰**: Agent专注业务，编排层专注聚合，传输层专注SSE
- **实时性**: 工具执行状态可实时推送到前端，提升用户体验
- **一致性**: 前端显示与后端存储使用相同message_id

#### ⚠️ 破坏性变更 (Breaking Changes)

- 事件协议升级，前端需同步更新类型定义
- 部分内部API签名调整（向后兼容）

---

## [0.1.0] - 2025-12-12

### 🎉 初始版本发布

#### 📥 数据嵌入角度 (Data Embedding)

- **商品向量化存储**
  - 商品描述智能分块处理 (RecursiveCharacterTextSplitter)
  - Qdrant 向量数据库
  - 支持商品元数据关联 (名称、价格、URL等)

- **嵌入流程**
  ```
  JSON商品数据 → 文本分块 → 向量嵌入 → Qdrant存储
      ↓            ↓          ↓          ↓
   商品描述 → chunk_size=1000 → 嵌入模型 → collection=products
  ```

#### 🔍 查询意图角度 (Query Intent)

- **智能推荐流程**
  ```
  用户查询 → Agent推理 → 工具调用 → 向量相似度 → 商品推荐 → 流式回复
     ↓         ↓         ↓         ↓            ↓         ↓
  "降噪耳机" → 意图识别 → search_products → k=5检索 → 生成回复 → SSE推送
  ```

#### ✨ 核心功能 (Features)

- **对话系统**: 匿名用户 + 会话历史 + 流式回复
- **推荐引擎**: 向量检索 + 智能排序 + 商品卡片展示
- **技术栈**: FastAPI + Next.js + LangChain + Qdrant

#### 🏗️ 架构设计 (Architecture)

- **后端**: Python 3.13 + FastAPI + LangGraph + SQLite
- **前端**: Next.js 15 + React + TypeScript + Tailwind
- **AI**: LangChain v1.1 + Qdrant

---
