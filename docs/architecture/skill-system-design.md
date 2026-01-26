# Skill 系统架构设计

基于 LangChain Skills 模式，为多智能体系统添加可扩展的技能支持。

## 1. 概述

### 1.1 目标

- 四个智能体（Product/FAQ/Knowledge/Support）均支持 Skill 能力
- Supervisor 引导者支持 Skill 调度
- 后台管理界面配置 Skill
- AI 辅助生成 Skill（根据用户描述）
- 系统默认 Skill（不可修改/删除）

### 1.2 核心概念

```
┌─────────────────────────────────────────────────────────────┐
│                        Skill System                         │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ System Skill│  │ User Skill  │  │ AI Generated│         │
│  │ (内置/只读) │  │ (用户创建) │  │   Skill     │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│         │                │                │                 │
│         └────────────────┼────────────────┘                 │
│                          ▼                                  │
│              ┌─────────────────────┐                        │
│              │   Skill Registry    │                        │
│              │   (技能注册表)      │                        │
│              └─────────────────────┘                        │
│                          │                                  │
│         ┌────────────────┼────────────────┐                 │
│         ▼                ▼                ▼                 │
│  ┌───────────┐    ┌───────────┐    ┌───────────┐           │
│  │ Product   │    │    FAQ    │    │ Knowledge │           │
│  │  Agent    │    │   Agent   │    │   Agent   │           │
│  └───────────┘    └───────────┘    └───────────┘           │
│         │                │                │                 │
│         └────────────────┼────────────────┘                 │
│                          ▼                                  │
│              ┌─────────────────────┐                        │
│              │    Supervisor       │                        │
│              │   (引导者/调度器)   │                        │
│              └─────────────────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

## 2. 数据模型设计

### 2.1 Skill 模型

```python
# backend/app/models/skill.py

from enum import Enum
from sqlalchemy import Column, String, Text, Boolean, JSON, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class SkillType(str, Enum):
    SYSTEM = "system"      # 系统内置（不可修改/删除）
    USER = "user"          # 用户创建
    AI_GENERATED = "ai"    # AI 生成

class SkillCategory(str, Enum):
    PROMPT = "prompt"           # 提示词增强
    RETRIEVAL = "retrieval"     # 检索增强
    TOOL = "tool"               # 工具扩展
    WORKFLOW = "workflow"       # 工作流

class Skill(BaseModel):
    """技能模型"""
    __tablename__ = "skills"
    
    # 基础信息
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=False)
    
    # 类型和分类
    type = Column(SQLEnum(SkillType), default=SkillType.USER)
    category = Column(SQLEnum(SkillCategory), default=SkillCategory.PROMPT)
    
    # 技能内容
    content = Column(Text, nullable=False)  # 技能主体内容（Markdown/提示词）
    
    # 触发配置
    trigger_keywords = Column(JSON, default=list)    # 触发关键词
    trigger_intents = Column(JSON, default=list)     # 触发意图
    always_apply = Column(Boolean, default=False)    # 是否始终应用
    
    # 适用范围
    applicable_agents = Column(JSON, default=list)   # 适用的 Agent 类型列表
    applicable_modes = Column(JSON, default=list)    # 适用的模式列表
    
    # 元数据
    version = Column(String(20), default="1.0.0")
    author = Column(String(100))
    
    # 状态
    is_active = Column(Boolean, default=True)
    is_system = Column(Boolean, default=False)       # 系统内置标记
    
    # 关联
    agent_skills = relationship("AgentSkill", back_populates="skill")


class AgentSkill(BaseModel):
    """Agent-Skill 关联表"""
    __tablename__ = "agent_skills"
    
    agent_id = Column(String(36), ForeignKey("agents.id"), nullable=False)
    skill_id = Column(String(36), ForeignKey("skills.id"), nullable=False)
    
    # 优先级（数值越小优先级越高）
    priority = Column(Integer, default=100)
    
    # 是否启用
    is_enabled = Column(Boolean, default=True)
    
    # 关联
    agent = relationship("Agent", back_populates="agent_skills")
    skill = relationship("Skill", back_populates="agent_skills")
```

### 2.2 Schema 定义

```python
# backend/app/schemas/skill.py

from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional

class SkillType(str, Enum):
    SYSTEM = "system"
    USER = "user"
    AI_GENERATED = "ai"

class SkillCategory(str, Enum):
    PROMPT = "prompt"
    RETRIEVAL = "retrieval"
    TOOL = "tool"
    WORKFLOW = "workflow"

class SkillBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=10)
    category: SkillCategory = SkillCategory.PROMPT
    content: str = Field(..., min_length=10)
    trigger_keywords: list[str] = []
    trigger_intents: list[str] = []
    always_apply: bool = False
    applicable_agents: list[str] = []  # ["product", "faq", "knowledge", "support"]
    applicable_modes: list[str] = []   # ["natural", "strict", "free"]

class SkillCreate(SkillBase):
    pass

class SkillUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[SkillCategory] = None
    content: Optional[str] = None
    trigger_keywords: Optional[list[str]] = None
    trigger_intents: Optional[list[str]] = None
    always_apply: Optional[bool] = None
    applicable_agents: Optional[list[str]] = None
    applicable_modes: Optional[list[str]] = None
    is_active: Optional[bool] = None

class SkillRead(SkillBase):
    id: str
    type: SkillType
    version: str
    author: Optional[str]
    is_active: bool
    is_system: bool
    created_at: datetime
    updated_at: datetime

class SkillListResponse(BaseModel):
    items: list[SkillRead]
    total: int
    page: int
    page_size: int

# AI 生成相关
class SkillGenerateRequest(BaseModel):
    """AI 生成 Skill 请求"""
    description: str = Field(..., min_length=20, description="技能描述")
    category: Optional[SkillCategory] = None
    applicable_agents: list[str] = []
    examples: Optional[list[str]] = None  # 示例对话

class SkillGenerateResponse(BaseModel):
    """AI 生成 Skill 响应"""
    skill: SkillCreate
    confidence: float
    suggestions: list[str]

# Agent Skill 配置
class AgentSkillConfig(BaseModel):
    skill_id: str
    priority: int = 100
    is_enabled: bool = True

class AgentSkillsUpdate(BaseModel):
    skills: list[AgentSkillConfig]
```

## 3. 服务层设计

### 3.1 Skill 服务

```python
# backend/app/services/skill/service.py

class SkillService:
    """技能管理服务"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self._cache: dict[str, Skill] = {}
    
    # ========== CRUD ==========
    
    async def create_skill(self, data: SkillCreate, author: str = None) -> Skill:
        """创建技能"""
        
    async def get_skill(self, skill_id: str) -> Skill | None:
        """获取技能"""
        
    async def list_skills(
        self,
        type: SkillType | None = None,
        category: SkillCategory | None = None,
        is_active: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> SkillListResponse:
        """列出技能"""
        
    async def update_skill(self, skill_id: str, data: SkillUpdate) -> Skill:
        """更新技能（系统技能不可更新）"""
        
    async def delete_skill(self, skill_id: str) -> bool:
        """删除技能（系统技能不可删除）"""
    
    # ========== Agent 关联 ==========
    
    async def get_skills_for_agent(
        self,
        agent_id: str,
        mode: str = "natural",
    ) -> list[Skill]:
        """获取 Agent 可用的技能列表"""
        
    async def update_agent_skills(
        self,
        agent_id: str,
        skills: list[AgentSkillConfig],
    ) -> None:
        """更新 Agent 的技能配置"""
    
    # ========== 技能加载 ==========
    
    async def load_skill_content(self, skill_id: str) -> str:
        """加载技能内容（用于 LLM 上下文注入）"""
        
    async def get_applicable_skills(
        self,
        agent_type: str,
        mode: str,
        user_message: str | None = None,
    ) -> list[Skill]:
        """获取适用的技能
        
        根据 agent_type、mode 和用户消息匹配：
        1. always_apply=True 的技能
        2. 关键词匹配的技能
        3. 意图匹配的技能
        """
    
    # ========== 系统技能 ==========
    
    async def init_system_skills(self) -> None:
        """初始化系统内置技能"""
        
    async def get_system_skills(self) -> list[Skill]:
        """获取所有系统技能"""
```

### 3.2 AI 生成服务

```python
# backend/app/services/skill/generator.py

class SkillGenerator:
    """AI 技能生成器"""
    
    GENERATE_PROMPT = '''你是一个专业的 AI 技能设计师。
    
根据用户的描述，生成一个结构化的技能定义。

## 用户描述
{description}

## 适用范围
- Agent 类型: {applicable_agents}
- 分类建议: {category}

## 示例对话（如有）
{examples}

## 输出要求
生成以下 JSON 格式的技能定义：
```json
{
    "name": "技能名称（简洁有力）",
    "description": "技能描述（说明用途和触发条件）",
    "category": "prompt|retrieval|tool|workflow",
    "content": "技能内容（Markdown 格式的提示词或工作流）",
    "trigger_keywords": ["关键词1", "关键词2"],
    "trigger_intents": ["意图1", "意图2"],
    "always_apply": false,
    "applicable_agents": ["product", "faq"],
    "applicable_modes": ["natural", "strict"]
}
```

请确保：
1. content 是高质量的提示词，能有效增强 Agent 能力
2. trigger_keywords 覆盖用户可能的表达方式
3. applicable_agents 和 applicable_modes 合理
'''

    def __init__(self):
        self.model = get_chat_model()
    
    async def generate(
        self,
        request: SkillGenerateRequest,
    ) -> SkillGenerateResponse:
        """根据描述生成技能"""
        
    async def refine(
        self,
        skill: Skill,
        feedback: str,
    ) -> SkillGenerateResponse:
        """根据反馈优化技能"""
        
    async def suggest_improvements(
        self,
        skill: Skill,
    ) -> list[str]:
        """建议改进点"""
```

### 3.3 Skill 注册表

```python
# backend/app/services/skill/registry.py

class SkillRegistry:
    """技能注册表 - 管理运行时技能加载"""
    
    _instance: "SkillRegistry | None" = None
    _skills: dict[str, Skill] = {}
    _agent_skills: dict[str, list[str]] = {}  # agent_id -> [skill_ids]
    
    def __new__(cls) -> "SkillRegistry":
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def reload(self) -> None:
        """重新加载所有技能"""
        
    def get_skill(self, skill_id: str) -> Skill | None:
        """获取技能"""
        
    def get_skills_for_agent(
        self,
        agent_id: str,
        agent_type: str,
        mode: str,
    ) -> list[Skill]:
        """获取 Agent 的技能列表"""
        
    def match_skills(
        self,
        agent_type: str,
        mode: str,
        message: str,
    ) -> list[Skill]:
        """匹配适用的技能（基于关键词和意图）"""
        
    def build_skill_context(
        self,
        skills: list[Skill],
    ) -> str:
        """构建技能上下文（注入到 system prompt）"""

skill_registry = SkillRegistry()
```

## 4. Agent 集成

### 4.1 修改 AgentConfig

```python
# backend/app/schemas/agent.py (扩展)

class AgentConfig(BaseModel):
    # ... 现有字段 ...
    
    # 新增：技能配置
    skills: list[SkillConfig] = []
    skill_loading_mode: Literal["eager", "lazy"] = "lazy"
    # eager: 启动时加载所有技能到 context
    # lazy: 按需加载（通过 load_skill 工具）
```

### 4.2 修改 Agent 工厂

```python
# backend/app/services/agent/core/factory.py (修改)

async def _build_single_agent(
    config: AgentConfig,
    checkpointer: BaseCheckpointSaver,
    use_structured_output: bool = False,
) -> CompiledStateGraph:
    """构建单个 Agent 实例"""
    
    # 1. 获取 LLM
    model = get_chat_model()
    
    # 2. 构建完整 system prompt
    system_prompt = config.system_prompt
    
    # 2.1 注入 always_apply 技能
    always_apply_skills = await skill_registry.get_always_apply_skills(
        agent_type=config.type,
        mode=config.mode,
    )
    if always_apply_skills:
        skill_context = skill_registry.build_skill_context(always_apply_skills)
        system_prompt = f"{system_prompt}\n\n{skill_context}"
    
    # 2.2 添加模式后缀
    mode_suffix = MODE_PROMPT_SUFFIX.get(config.mode, "")
    if mode_suffix:
        system_prompt = system_prompt + mode_suffix
    
    # 3. 获取工具列表
    tools = get_tools_for_agent(config)
    
    # 3.1 添加 load_skill 工具（lazy 模式）
    if config.skill_loading_mode == "lazy":
        load_skill_tool = create_load_skill_tool(config)
        tools.append(load_skill_tool)
    
    # ... 后续构建逻辑 ...
```

### 4.3 load_skill 工具

```python
# backend/app/services/agent/tools/skill.py

from langchain_core.tools import tool

def create_load_skill_tool(config: AgentConfig):
    """创建 load_skill 工具"""
    
    available_skills = skill_registry.get_skills_for_agent(
        agent_id=config.agent_id,
        agent_type=config.type,
        mode=config.mode,
    )
    
    skill_descriptions = "\n".join([
        f"- {s.name}: {s.description}"
        for s in available_skills
    ])
    
    @tool
    async def load_skill(skill_name: str) -> str:
        """加载专业技能的提示词和上下文。
        
        可用技能：
        {skill_descriptions}
        
        Args:
            skill_name: 要加载的技能名称
            
        Returns:
            技能的提示词和上下文内容
        """
        skill = next(
            (s for s in available_skills if s.name == skill_name),
            None
        )
        if not skill:
            return f"技能 '{skill_name}' 不存在或不可用"
        
        return skill.content
    
    # 动态更新 docstring
    load_skill.__doc__ = load_skill.__doc__.format(
        skill_descriptions=skill_descriptions
    )
    
    return load_skill
```

### 4.4 Supervisor 集成

```python
# backend/app/services/agent/core/factory.py (Supervisor 部分)

async def build_supervisor_agent(
    config: AgentConfig,
    checkpointer: BaseCheckpointSaver,
    session: "AsyncSession | None" = None,
) -> CompiledStateGraph:
    """构建 Supervisor Agent"""
    
    # ... 现有逻辑 ...
    
    # 为 Supervisor 添加技能调度能力
    supervisor_skills = await skill_registry.get_skills_for_agent(
        agent_id=config.agent_id,
        agent_type="supervisor",
        mode=config.mode,
    )
    
    if supervisor_skills:
        skill_context = skill_registry.build_skill_context(supervisor_skills)
        supervisor_prompt = f"{supervisor_prompt}\n\n## 可用技能\n{skill_context}"
    
    # ... 后续构建逻辑 ...
```

## 5. API 路由设计

```python
# backend/app/routers/skills.py

router = APIRouter(
    prefix="/api/v1/admin/skills",
    tags=["skills"],
)

# ========== 技能 CRUD ==========

@router.get("", response_model=SkillListResponse)
async def list_skills(
    type: SkillType | None = None,
    category: SkillCategory | None = None,
    is_active: bool | None = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db_session),
):
    """获取技能列表"""

@router.post("", response_model=SkillRead, status_code=201)
async def create_skill(
    data: SkillCreate,
    db: AsyncSession = Depends(get_db_session),
):
    """创建技能"""

@router.get("/{skill_id}", response_model=SkillRead)
async def get_skill(
    skill_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """获取技能详情"""

@router.put("/{skill_id}", response_model=SkillRead)
async def update_skill(
    skill_id: str,
    data: SkillUpdate,
    db: AsyncSession = Depends(get_db_session),
):
    """更新技能（系统技能不可更新）"""

@router.delete("/{skill_id}", status_code=204)
async def delete_skill(
    skill_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """删除技能（系统技能不可删除）"""

# ========== AI 生成 ==========

@router.post("/generate", response_model=SkillGenerateResponse)
async def generate_skill(
    data: SkillGenerateRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """AI 生成技能"""

@router.post("/{skill_id}/refine", response_model=SkillGenerateResponse)
async def refine_skill(
    skill_id: str,
    feedback: str = Body(...),
    db: AsyncSession = Depends(get_db_session),
):
    """AI 优化技能"""

# ========== Agent 技能配置 ==========

@router.get("/agents/{agent_id}", response_model=list[SkillRead])
async def get_agent_skills(
    agent_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """获取 Agent 的技能列表"""

@router.put("/agents/{agent_id}", status_code=204)
async def update_agent_skills(
    agent_id: str,
    data: AgentSkillsUpdate,
    db: AsyncSession = Depends(get_db_session),
):
    """更新 Agent 的技能配置"""

# ========== 系统技能 ==========

@router.get("/system", response_model=list[SkillRead])
async def get_system_skills(
    db: AsyncSession = Depends(get_db_session),
):
    """获取系统内置技能"""

@router.post("/system/init", status_code=204)
async def init_system_skills(
    db: AsyncSession = Depends(get_db_session),
):
    """初始化系统内置技能（仅管理员）"""
```

## 6. 前端设计

### 6.1 页面结构

```
frontend/app/admin/skills/
├── page.tsx              # 技能列表页
├── [id]/
│   └── page.tsx          # 技能详情/编辑页
├── create/
│   └── page.tsx          # 创建技能页
├── generate/
│   └── page.tsx          # AI 生成技能页
└── components/
    ├── SkillCard.tsx     # 技能卡片
    ├── SkillForm.tsx     # 技能表单
    ├── SkillEditor.tsx   # 技能内容编辑器（Markdown）
    ├── SkillPreview.tsx  # 技能预览
    └── SkillGenerator.tsx # AI 生成组件
```

### 6.2 技能列表页

```tsx
// frontend/app/admin/skills/page.tsx

export default function SkillsPage() {
  return (
    <div className="space-y-6">
      {/* 页头 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">技能管理</h1>
          <p className="text-muted-foreground">
            管理智能体的专业技能，支持自定义和 AI 生成
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" asChild>
            <Link href="/admin/skills/generate">
              <Sparkles className="mr-2 h-4 w-4" />
              AI 生成
            </Link>
          </Button>
          <Button asChild>
            <Link href="/admin/skills/create">
              <Plus className="mr-2 h-4 w-4" />
              创建技能
            </Link>
          </Button>
        </div>
      </div>
      
      {/* 筛选器 */}
      <div className="flex gap-4">
        <Select>
          <SelectTrigger className="w-[150px]">
            <SelectValue placeholder="类型" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部类型</SelectItem>
            <SelectItem value="system">系统内置</SelectItem>
            <SelectItem value="user">用户创建</SelectItem>
            <SelectItem value="ai">AI 生成</SelectItem>
          </SelectContent>
        </Select>
        
        <Select>
          <SelectTrigger className="w-[150px]">
            <SelectValue placeholder="分类" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部分类</SelectItem>
            <SelectItem value="prompt">提示词增强</SelectItem>
            <SelectItem value="retrieval">检索增强</SelectItem>
            <SelectItem value="tool">工具扩展</SelectItem>
            <SelectItem value="workflow">工作流</SelectItem>
          </SelectContent>
        </Select>
      </div>
      
      {/* 技能列表 */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {skills.map((skill) => (
          <SkillCard key={skill.id} skill={skill} />
        ))}
      </div>
    </div>
  )
}
```

### 6.3 AI 生成页

```tsx
// frontend/app/admin/skills/generate/page.tsx

export default function GenerateSkillPage() {
  const [description, setDescription] = useState("")
  const [category, setCategory] = useState<string>()
  const [agents, setAgents] = useState<string[]>([])
  const [examples, setExamples] = useState<string[]>([])
  const [result, setResult] = useState<SkillGenerateResponse | null>(null)
  const [isGenerating, setIsGenerating] = useState(false)
  
  const handleGenerate = async () => {
    setIsGenerating(true)
    try {
      const res = await generateSkill({
        description,
        category,
        applicable_agents: agents,
        examples,
      })
      setResult(res)
    } finally {
      setIsGenerating(false)
    }
  }
  
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      {/* 左侧：输入区 */}
      <Card>
        <CardHeader>
          <CardTitle>AI 生成技能</CardTitle>
          <CardDescription>
            描述你想要的技能，AI 将自动生成结构化定义
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>技能描述</Label>
            <Textarea
              placeholder="例如：帮助用户进行商品对比，突出不同商品的优劣势..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={4}
            />
          </div>
          
          <div className="space-y-2">
            <Label>分类建议</Label>
            <Select value={category} onValueChange={setCategory}>
              <SelectTrigger>
                <SelectValue placeholder="选择分类" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="prompt">提示词增强</SelectItem>
                <SelectItem value="retrieval">检索增强</SelectItem>
                <SelectItem value="tool">工具扩展</SelectItem>
                <SelectItem value="workflow">工作流</SelectItem>
              </SelectContent>
            </Select>
          </div>
          
          <div className="space-y-2">
            <Label>适用 Agent</Label>
            <div className="flex flex-wrap gap-2">
              {["product", "faq", "knowledge", "support"].map((agent) => (
                <Badge
                  key={agent}
                  variant={agents.includes(agent) ? "default" : "outline"}
                  className="cursor-pointer"
                  onClick={() => toggleAgent(agent)}
                >
                  {agent}
                </Badge>
              ))}
            </div>
          </div>
          
          <Button
            onClick={handleGenerate}
            disabled={!description || isGenerating}
            className="w-full"
          >
            {isGenerating ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                生成中...
              </>
            ) : (
              <>
                <Sparkles className="mr-2 h-4 w-4" />
                生成技能
              </>
            )}
          </Button>
        </CardContent>
      </Card>
      
      {/* 右侧：预览区 */}
      <Card>
        <CardHeader>
          <CardTitle>生成结果</CardTitle>
        </CardHeader>
        <CardContent>
          {result ? (
            <SkillPreview
              skill={result.skill}
              confidence={result.confidence}
              suggestions={result.suggestions}
              onSave={handleSave}
              onRefine={handleRefine}
            />
          ) : (
            <div className="text-center text-muted-foreground py-12">
              输入描述后点击生成
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
```

## 7. 系统内置技能

### 7.1 预置技能列表

```python
# backend/app/services/skill/system_skills.py

SYSTEM_SKILLS = [
    {
        "name": "商品对比专家",
        "description": "帮助用户进行多商品对比，分析优劣势",
        "category": "prompt",
        "content": """## 商品对比技能

当用户询问多个商品的对比时，按以下结构组织回答：

### 对比维度
1. **价格区间**：列出各商品价格
2. **核心功能**：突出差异化特性
3. **适用场景**：推荐最适合的使用场景
4. **性价比评估**：综合评分

### 输出格式
使用表格形式呈现对比结果，最后给出推荐建议。
""",
        "trigger_keywords": ["对比", "区别", "哪个好", "推荐哪个", "比较"],
        "trigger_intents": ["compare", "recommendation"],
        "applicable_agents": ["product"],
        "applicable_modes": ["natural", "strict"],
    },
    {
        "name": "FAQ 精准匹配",
        "description": "提高 FAQ 匹配精度，减少无关回答",
        "category": "retrieval",
        "content": """## FAQ 匹配技能

### 匹配规则
1. 优先精确匹配用户问题关键词
2. 相似度阈值：0.8 以上才推荐
3. 多个匹配时，按相关度排序展示前 3 条

### 回答格式
- 直接回答核心问题
- 引用 FAQ 来源
- 提供相关问题链接
""",
        "always_apply": True,
        "applicable_agents": ["faq"],
        "applicable_modes": ["natural", "strict"],
    },
    # ... 更多系统技能
]
```

## 8. 实现步骤

### Phase 1: 基础架构（1-2 天）
1. 创建 Skill 数据模型
2. 实现 SkillService CRUD
3. 创建 API 路由
4. 初始化系统内置技能

### Phase 2: Agent 集成（1-2 天）
1. 修改 AgentConfig 支持技能
2. 实现 SkillRegistry
3. 创建 load_skill 工具
4. 修改 Agent 工厂集成技能

### Phase 3: AI 生成（1 天）
1. 实现 SkillGenerator
2. 创建生成 API
3. 优化生成提示词

### Phase 4: 前端界面（2-3 天）
1. 技能列表页
2. 技能创建/编辑页
3. AI 生成页
4. Agent 技能配置

### Phase 5: 测试与优化（1 天）
1. 单元测试
2. 集成测试
3. 性能优化
