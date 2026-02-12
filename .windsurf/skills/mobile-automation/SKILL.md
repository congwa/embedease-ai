# mobile-automation

Mobile MCP + 飞书 MCP 双协作自动化测试专家。

核心能力：
- 飞书多维表格用例管理（读取、执行、回写结果）
- Mobile MCP 移动端自动化（Android/iOS）
- 智能重试与降级策略
- 每10条用例自动分批，打开新会话继续
- Token 优化策略（减少 80% 的截图消耗）

触发关键词：手机自动化、移动端测试、App 测试、mobile_mcp、点击手机、操作手机、执行飞书用例、批量执行、多维表格

---

## 🔗 双MCP协作架构

```
┌─────────────────────────────────────────────────────────────┐
│                     AI（Windsurf）                           │
│                                                             │
│   ┌──────────────┐              ┌──────────────┐           │
│   │  飞书 MCP    │              │  Mobile MCP  │           │
│   │              │              │              │           │
│   │ • 读取用例   │              │ • 启动App    │           │
│   │ • 写入结果   │              │ • 点击元素   │           │
│   │ • 更新状态   │              │ • 输入文本   │           │
│   └──────┬───────┘              └──────┬───────┘           │
│          │                             │                    │
│          ▼                             ▼                    │
│   ┌──────────────┐              ┌──────────────┐           │
│   │ 飞书多维表格 │              │   手机设备   │           │
│   └──────────────┘              └──────────────┘           │
└─────────────────────────────────────────────────────────────┘
```

## 🎯 核心原则

### 1. Token 优化（最重要）

**永远优先使用 `list_elements`，而不是截图！**

| 方式 | Token 消耗 | 使用场景 |
|------|-----------|---------|
| `list_elements` | ~500 | ✅ 确认页面状态、查找元素 |
| `take_screenshot` | ~2000 | ❌ 只在需要视觉分析时使用 |

```
❌ 错误流程：截图 → 分析 → 点击 → 截图确认
✅ 正确流程：list_elements → 点击 → list_elements 确认
```

### 2. 工具选择优先级

点击元素时，按以下优先级选择工具：

```
1️⃣ click_by_text（最稳定，跨设备兼容）
   ↓ 找不到文本？
2️⃣ click_by_id（需要 resource-id）
   ↓ 没有 id？
3️⃣ click_by_percent（百分比坐标，跨分辨率）
   ↓ 复杂场景？
4️⃣ click_at_coords（兜底，需要截图获取坐标）
```

### 3. 验证策略

**使用 verify 参数减少额外调用：**

```python
# ❌ 低效（3次调用）
list_elements()
click_by_text("登录")
list_elements()  # 确认

# ✅ 高效（2次调用）
list_elements()
click_by_text("登录", verify="首页")  # 自动验证"首页"出现
```

---

## 📱 常见场景

### 场景 1：启动 App 并处理弹窗

```python
# 标准流程
1. launch_app("com.example.app")
2. wait(2)  # 等待启动
3. close_popup()  # 自动检测并关闭弹窗（无需先截图）
4. list_elements()  # 确认主页面
```

**注意**：`close_popup` 会自动检测是否有弹窗，如果没有会直接返回"无弹窗"，不会误操作。

### 场景 2：登录流程

```python
# 推荐流程
1. list_elements()  # 获取输入框 ID
2. input_text_by_id("username_input", "test123")
3. input_text_by_id("password_input", "password")
4. hide_keyboard()  # ⭐ 必须！收起键盘，确保协议复选框可点击
5. click_by_text("我已阅读并同意")  # 勾选用户协议
6. click_by_text("登录", verify="首页")  # 点击并验证跳转
```

**⚠️ 重要**：输入密码后键盘可能遮挡协议复选框，必须先调用 `hide_keyboard()` 收起键盘！

### 场景 3：滚动查找元素

```python
# 元素可能在屏幕外时
max_scrolls = 5
for i in range(max_scrolls):
    elements = list_elements()
    if "目标文本" in str(elements):
        click_by_text("目标文本")
        break
    swipe("up")  # 向上滑动
    wait(0.5)
else:
    # 滚动到底还没找到
    return "未找到目标元素"
```

### 场景 4：处理多个相同文案

当页面有多个相同文本的元素时，使用 position 参数：

```python
# 点击上方的"更多"
click_by_text("更多", position="top")

# 点击下方的"确定"
click_by_text("确定", position="bottom")

# 支持的位置：top/bottom/left/right/center
```

### 场景 5：录制测试脚本

```python
# 1. 开始录制
clear_operation_history()

# 2. 执行测试步骤（正常操作）
launch_app("com.example.app")
click_by_text("登录")
input_text_by_id("username", "test")
click_by_text("提交")

# 3. 生成脚本
generate_test_script(
    test_name="登录测试",
    package_name="com.example.app",
    filename="login_test"
)
```

生成的脚本会自动：
- 将坐标转换为百分比（跨分辨率兼容）
- 优先使用 text/id 定位
- 包含智能等待

---

## 🚫 弹窗处理策略

### 工具选择

| 场景 | 推荐工具 |
|------|---------|
| 通用弹窗（权限、广告） | `close_popup` |
| 广告弹窗 | `close_ad` |
| 已知模板的 X 按钮 | `template_close` |
| 需要先确认位置 | `find_close_button` |

### close_popup 工作原理

1. **控件树查找**：找 ×、关闭、跳过、取消 等文本
2. **resource-id 匹配**：找包含 close/dismiss/skip 的 id
3. **小元素检测**：找角落的小型 clickable 元素
4. **视觉兜底**：返回 SoM 截图让 AI 识别

### 处理顽固弹窗

```python
# 如果 close_popup 失败
1. find_close_button()  # 获取推荐的点击方式
2. 按返回的 click_command 执行

# 如果还是失败
1. screenshot_with_som()  # SoM 标注截图
2. click_by_som(编号)  # 点击 X 号对应的编号

# 学习新的 X 按钮模板
template_add(template_name="app_x_button", x_percent=95, y_percent=8, size=60)
```

---

## ⚠️ 错误处理

### 元素找不到

```python
# 可能原因及解决
1. 文本不完全匹配 → 用 list_elements 确认完整文本
2. 元素在屏幕外 → swipe 滚动后重试
3. 页面未加载完 → wait(1-2秒) 后重试
4. 被弹窗遮挡 → close_popup 后重试
```

### 设备连接问题

```python
# 检查连接
check_connection()

# 如果断开，提示用户：
# Android: adb devices / adb kill-server && adb start-server
# iOS: tidevice list / 重启 WebDriverAgent
```

### 点击无效

```python
# 可能是元素 clickable=false，尝试：
1. 点击父元素
2. 使用坐标点击
3. 长按后操作
```

---

## 🍞 Toast 验证（仅 Android）

```python
# 正确流程（必须先监听）
1. start_toast_watch()  # 开始监听
2. click_by_text("提交")  # 触发 Toast 的操作
3. assert_toast("提交成功")  # 验证 Toast 内容

# ❌ 错误：操作后才监听，会错过 Toast
```

---

## 📝 最佳实践检查清单

执行操作前，确认：

- [ ] 用 `list_elements` 而不是截图确认页面
- [ ] 优先使用 `click_by_text`，其次 `click_by_id`
- [ ] 使用 `verify` 参数减少确认调用
- [ ] 启动 App 后调用 `close_popup` 处理弹窗
- [ ] Toast 验证前先 `start_toast_watch`
- [ ] 录制脚本前先 `clear_operation_history`

---

## 🔧 工具速查

### 页面分析
- `list_elements` - 📋 列出元素（首选）
- `take_screenshot` - 📸 截图（token 高）
- `screenshot_with_som` - 📸 SoM 标注截图
- `get_screen_size` - 📐 屏幕尺寸

### 点击操作
- `click_by_text` - 👆 文本点击（推荐）
- `click_by_id` - 👆 ID 点击
- `click_by_percent` - 👆 百分比点击
- `click_by_som` - 👆 SoM 编号点击
- `click_at_coords` - 👆 坐标点击（兜底）

### 长按操作
- `long_press_by_text` - 👆 文本长按
- `long_press_by_id` - 👆 ID 长按
- `long_press_by_percent` - 👆 百分比长按
- `long_press_at_coords` - 👆 坐标长按

### 输入操作
- `input_text_by_id` - ⌨️ ID 输入
- `input_at_coords` - ⌨️ 坐标输入

### 导航操作
- `swipe` - 👆 滑动（up/down/left/right）
- `press_key` - ⌨️ 按键（home/back/enter）
- `hide_keyboard` - ⌨️ 收起键盘（⭐ 登录场景必备）
- `wait` - ⏰ 等待

### 应用管理
- `launch_app` - 🚀 启动应用
- `terminate_app` - ⏹️ 终止应用
- `list_apps` - 📦 列出应用

### 弹窗处理
- `close_popup` - 🚫 智能关闭弹窗
- `close_ad` - 🚫 关闭广告
- `find_close_button` - 🔍 查找关闭按钮
- `template_close` - 🎯 模板匹配关闭

### 验证断言
- `assert_text` - ✅ 断言文本存在
- `assert_toast` - ✅ 断言 Toast 内容

### 脚本生成
- `clear_operation_history` - 🗑️ 清空历史
- `get_operation_history` - 📜 获取历史
- `generate_test_script` - 📝 生成 pytest 脚本

---

## 📋 批量执行 YAML 测试用例

当用户说"执行 xxx.yaml"时，按以下规则执行：

### YAML 结构

```yaml
config:
  app_package: com.example.app  # App 包名

cases:
  - name: 用例名称
    setup: launch_app  # 可选：启动方式
    steps:
      - 等待2秒
      - 点击登录
    verify: 首页  # 可选：验证页面包含该文本
```

### setup 执行规则

| setup 值 | 执行动作 |
|----------|---------|
| `launch_app` | **先 terminate_app 杀掉App，再 launch_app 启动**（确保干净状态） |
| `none` 或不填 | 不做任何启动操作，继续当前页面 |

### 步骤理解映射

| 自然语言步骤 | 对应工具调用 |
|-------------|-------------|
| 等待N秒 | `wait(N)` |
| 关闭弹窗 | 检测后 `close_popup()` |
| 点击XXX | `click_by_text("XXX")` |
| 在XXX输入YYY | `input_text_by_id("XXX", "YYY")` |
| 向上/下滑动 | `swipe("up/down")` |
| 按返回键 | `press_key("back")` |
| 收起键盘 | `hide_keyboard()` |
| 勾选协议/勾选用户协议 | `hide_keyboard()` + `click_by_text("协议文本")` |
| 开始监听Toast | `start_toast_watch()` |
| 验证Toast包含XXX | `assert_toast("XXX")` |

### 降级策略

当 MCP 工具返回 `fallback=vision` 时：
1. 调用 `screenshot_with_som` 获取 SoM 截图
2. 识别目标元素编号
3. 调用 `click_by_som(编号)` 点击
4. 如还失败，尝试 `close_popup` 后重试

---

## 📊 飞书多维表格批量执行

当用户说"执行飞书用例"或"继续执行飞书用例"时，按以下规则执行：

### 飞书MCP工具速查

| 工具 | 用途 | 示例 |
|------|------|------|
| `bitable_v1_appTableRecord_search` | 查询用例 | 读取待执行的用例 |
| `bitable_v1_appTableRecord_update` | 更新记录 | 回写执行结果 |
| `bitable_v1_appTableRecord_create` | 创建记录 | 新增用例 |
| `bitable_v1_appTableField_list` | 列出字段 | 获取表格结构 |

### 表格结构要求

| 字段 | 类型 | 说明 |
|------|------|------|
| 用例编号 | 数字 | 唯一标识 |
| 用例名称 | 文本 | 用例名称 |
| 预置条件 | 多行文本 | 前置依赖条件（AI理解自然语言） |
| 测试步骤 | 文本 | 自然语言描述的步骤 |
| 预期结果 | 文本 | 期望的最终状态 |
| 验证点 | 多选 | 最终验证内容（可选） |
| 执行结果 | 文本 | PASS / FAIL |
| 失败原因 | 单选/文本 | 失败时的原因 |

### 执行流程

1. **读取用例**：优先执行结果为空 → 再执行 FAIL 的用例，按编号升序
2. **处理预置条件**：AI 理解自然语言，执行重启/登录/切换账号/AB实验等
3. **边执行边验证**：每个步骤执行后立即验证对应的预期结果
4. **回写结果**：每条用例执行完立即回写飞书（PASS/FAIL）
5. **分批继续**：每 10 条自动打开新会话继续

### 步骤失败重试策略（最多5步，禁止循环）

```
尝试1: click_by_text("登录")
  ↓ 失败
尝试2: list_elements → 找相似文本 → click_by_text
  ↓ 失败
尝试3: screenshot_with_som → click_by_som(编号)
  ↓ 失败
尝试4: close_popup() → 重试 click_by_text
  ↓ 失败
尝试5: take_screenshot → AI分析坐标 → click_at_coords
  ↓ 失败
━━━ 放弃！标记FAIL，继续下一条用例 ━━━
```

**⚠️ 禁止行为**：
- 不要无限重试同一个步骤
- 不要反复滑动查找超过3次
- 不要重复截图超过2次
- 5步全试过必须放弃，写明失败原因

### 失败标注规则

| 失败场景 | 失败原因 |
|---------|---------|
| 元素找不到 | 元素未找到: {文本} |
| 视觉识别失败 | SoM识别失败 |
| 验证不通过 | 验证失败: 未找到"{验证点}" |
| 超时 | 操作超时 |
| 设备断开 | 设备连接失败 |

### 表格Token获取

执行用例前必须先获取表格Token：
1. 用户直接提供表格URL或app_token + table_id
2. 从飞书URL解析：`https://xxx.feishu.cn/base/{app_token}?table={table_id}`
3. 从配置或环境变量获取
4. 主动询问用户

**禁止使用占位符**，Token缺失时必须询问用户。

---

## ⚠️ 注意事项

### 1. 权限要求
- **飞书应用**: 需要多维表格读写权限
- **macOS辅助功能**: 系统设置 → 隐私与安全 → 辅助功能 → 添加 Windsurf

### 2. 错误恢复
如果执行中断：
- 已执行的用例状态已保存在飞书
- 说"继续执行飞书用例"会自动从未执行的用例继续

### 3. 并发限制
- 飞书API有调用频率限制
- 每条用例执行后立即回写，避免批量写入
