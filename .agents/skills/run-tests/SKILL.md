---
name: run-tests
description: |
  后端代码测试验证规则。此技能在以下情况下自动触发：
  - 任何后端代码修改（backend/ 目录下的 .py 文件）
  - 新增功能开发
  - Bug 修复
  - 代码重构

  核心原则：
  1. 后端代码修改必须有对应的测试用例
  2. 修改业务逻辑时必须同步更新相关测试用例
  3. 测试全部通过才算功能完成

  触发关键词：后端、backend、python、测试、test、pytest、功能、feature、修复、fix、实现、修改、完成、验证
  alwaysApply: true
---

# 后端测试验证规则

## 一、强制要求

**当修改后端代码时，必须遵循以下规则：**

1. **新功能必须有测试**
   - 每个新增的函数/类必须有对应的单元测试
   - 测试文件放在 `backend/tests/` 对应目录下
   - 测试函数命名：`test_<功能名>_<场景>`

2. **修改代码必须同步更新测试**
   - 修改业务逻辑后，必须检查并更新相关测试用例
   - 如果修改导致测试失败，需判断是代码 bug 还是测试需要更新
   - **业务变更 → 更新测试用例**
   - **代码 bug → 修复代码**

3. **测试必须全部通过**
   - 功能完成的标准：所有相关测试通过
   - 不允许跳过或注释掉失败的测试

4. **测试用例必须反映最新业务**
   - 测试用例应该与当前业务逻辑保持一致
   - 修改功能时，同时更新测试的预期结果

## 二、验证命令

### 2.1 测试命令
```bash
# 运行所有测试
cd backend && uv run pytest tests/ -v

# 运行特定模块测试
cd backend && uv run pytest tests/<module>/ -v

# 运行单个测试文件
cd backend && uv run pytest tests/<module>/test_<name>.py -v

# 运行匹配名称的测试
cd backend && uv run pytest -k "<pattern>" -v
```

### 2.2 代码质量检查（必须）
```bash
# 测试通过后，必须运行 ruff 检查并自动修复
cd backend && uv run ruff check --fix

# 如果有无法自动修复的问题，手动修复后重新检查
cd backend && uv run ruff check
```

**注意**：测试通过 + ruff 检查通过，才算代码验证完成。

## 三、测试目录结构

```
backend/tests/
├── conftest.py          # 共享 fixtures
├── core/                # 核心模块测试
│   ├── test_config.py
│   └── test_errors.py
├── models/              # 数据模型测试
│   └── test_conversation.py
├── repositories/        # 仓库层测试
│   └── test_base.py
├── schemas/             # Schema 测试
│   ├── test_agent.py
│   ├── test_chat.py
│   ├── test_events.py
│   └── test_websocket.py
└── services/            # 服务层测试
    ├── test_conversation.py
    └── test_streaming.py
```

## 四、工作流程

### 4.1 新增功能时

1. **先写测试**（推荐 TDD）
   ```python
   # tests/services/test_new_feature.py
   def test_new_feature_basic():
       """测试新功能的基本场景"""
       result = new_feature(input)
       assert result == expected

   def test_new_feature_edge_case():
       """测试边界情况"""
       ...

   def test_new_feature_error_handling():
       """测试错误处理"""
       with pytest.raises(ExpectedError):
           new_feature(invalid_input)
   ```

2. **实现功能代码**

3. **运行测试验证**
   ```bash
   cd backend && uv run pytest tests/services/test_new_feature.py -v
   ```

4. **测试通过后才算完成**

### 4.2 修改现有功能时

1. **先找到相关测试文件**
   ```bash
   # 搜索相关测试
   grep -r "test_<功能名>" backend/tests/
   ```

2. **理解当前测试的预期行为**

3. **修改业务代码**

4. **同步更新测试用例**
   - 如果返回值/行为变了 → 更新测试的 `assert` 语句
   - 如果新增了字段/参数 → 新增测试覆盖
   - 如果删除了功能 → 删除相关测试

5. **运行测试验证**
   ```bash
   cd backend && uv run pytest tests/ -v
   ```

### 4.3 修复 Bug 时

1. **先写失败测试**（复现 Bug）
2. **修复代码**
3. **验证测试通过**
4. **运行完整测试套件确保无回归**

### 4.4 重构时

1. **先运行现有测试确保通过**
2. **进行重构**
3. **重新运行测试确保通过**

## 五、测试编写规范

### 5.1 测试函数命名
```python
def test_<被测对象>_<场景>_<预期结果>():
    # 例如：
    def test_create_agent_with_valid_data_returns_agent():
    def test_create_agent_with_empty_name_raises_error():
```

### 5.2 测试结构（AAA 模式）
```python
def test_example():
    # Arrange - 准备测试数据
    input_data = {...}

    # Act - 执行被测代码
    result = function_under_test(input_data)

    # Assert - 验证结果
    assert result == expected
```

### 5.3 使用 fixtures
```python
# conftest.py
@pytest.fixture
def sample_agent():
    return Agent(name="test", type="faq")

# test_file.py
def test_agent_update(sample_agent):
    sample_agent.name = "updated"
    assert sample_agent.name == "updated"
```

## 六、完成标准

**功能完成的检查清单：**

- [ ] 新增代码有对应的测试用例
- [ ] 修改的代码已同步更新相关测试用例
- [ ] 测试覆盖正常路径和异常路径
- [ ] 所有测试通过：`uv run pytest tests/ -v`
- [ ] 代码质量检查通过：`uv run ruff check --fix`
- [ ] 无跳过或禁用的测试
- [ ] 测试用例反映当前最新业务逻辑

**验证流程：**
```bash
# 1. 运行测试
cd backend && uv run pytest tests/ -v

# 2. 运行代码质量检查
cd backend && uv run ruff check --fix

# 两个命令都通过，功能才算完成
```

**只有满足以上所有条件，功能才算真正完成。**

## 七、常见场景示例

### 场景 1：修改函数返回值
```python
# 原代码：返回 {"id": id, "name": name}
# 修改后：返回 {"id": id, "name": name, "status": "active"}

# 需要更新测试：
def test_get_item():
    result = get_item(1)
    assert result["id"] == 1
    assert result["name"] == "test"
    assert result["status"] == "active"  # 新增断言
```

### 场景 2：修改函数签名
```python
# 原代码：def process(data)
# 修改后：def process(data, options=None)

# 需要新增测试：
def test_process_with_options():
    result = process(data, options={"flag": True})
    assert result == expected_with_options
```

### 场景 3：修改业务逻辑
```python
# 原逻辑：价格 < 100 返回 "cheap"
# 新逻辑：价格 < 200 返回 "cheap"

# 需要更新测试：
def test_price_category_cheap():
    assert get_category(150) == "cheap"  # 原来期望 "normal"，现在期望 "cheap"
```