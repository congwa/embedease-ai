/**
 * 聊天主题注册系统
 * 
 * 设计原则：
 * 1. 每个主题是一个独立的配置对象
 * 2. 主题只影响聊天对话区域，不影响其他部分
 * 3. 支持运行时动态注册新主题
 * 4. 提供类型安全的主题配置
 */

export type ChatThemeId = "default" | "ethereal" | "industrial" | "techbiz" | "warmshop" | "luxemin";

export interface ChatThemeConfig {
  id: ChatThemeId;
  name: string;
  description: string;
  // CSS 类名前缀，用于样式隔离
  classPrefix: string;
  // 预览色，用于主题选择器
  previewColors: {
    primary: string;
    background: string;
    accent: string;
  };
  // 组件样式类名映射
  components: {
    // 容器
    chatContainer: string;
    header: string;
    messageArea: string;
    inputArea: string;
    // 消息气泡
    userMessage: string;
    aiMessage: string;
    // 输入框
    inputWrapper: string;
    inputTextarea: string;
    sendButton: string;
    sendButtonActive: string;
    // 空状态
    emptyState: string;
    emptyIcon: string;
    emptyTitle: string;
    emptyDescription: string;
    suggestionButton: string;
    // LLM 调用状态
    llmCallCluster: string;
    llmCallHeader: string;
    llmCallBody: string;
    // 工具调用
    toolCall: string;
    // 推理区域
    reasoning: string;
    // 内容区域
    content: string;
  };
  // 动效配置
  motion: {
    messageAppear: string;
    buttonPress: string;
    transition: string;
  };
}

// 默认主题 - 当前风格
const defaultTheme: ChatThemeConfig = {
  id: "default",
  name: "默认",
  description: "简洁现代的默认风格",
  classPrefix: "theme-default",
  previewColors: {
    primary: "#18181b",
    background: "#ffffff",
    accent: "#f97316",
  },
  components: {
    chatContainer: "chat-default",
    header: "chat-default-header",
    messageArea: "chat-default-messages",
    inputArea: "chat-default-input-area",
    userMessage: "chat-default-user-msg",
    aiMessage: "chat-default-ai-msg",
    inputWrapper: "chat-default-input-wrapper",
    inputTextarea: "chat-default-textarea",
    sendButton: "chat-default-send-btn",
    sendButtonActive: "chat-default-send-btn-active",
    emptyState: "chat-default-empty",
    emptyIcon: "chat-default-empty-icon",
    emptyTitle: "chat-default-empty-title",
    emptyDescription: "chat-default-empty-desc",
    suggestionButton: "chat-default-suggestion",
    llmCallCluster: "chat-default-llm-cluster",
    llmCallHeader: "chat-default-llm-header",
    llmCallBody: "chat-default-llm-body",
    toolCall: "chat-default-tool",
    reasoning: "chat-default-reasoning",
    content: "chat-default-content",
  },
  motion: {
    messageAppear: "animate-fade-in",
    buttonPress: "active:scale-95",
    transition: "transition-all duration-200",
  },
};

// 晨曦纸境主题
const etherealTheme: ChatThemeConfig = {
  id: "ethereal",
  name: "晨曦纸境",
  description: "温润的暖奶油色调，如纸质书般的舒适感",
  classPrefix: "theme-ethereal",
  previewColors: {
    primary: "#4A453E",
    background: "#F9F7F2",
    accent: "#E6A23C",
  },
  components: {
    chatContainer: "chat-ethereal",
    header: "chat-ethereal-header",
    messageArea: "chat-ethereal-messages",
    inputArea: "chat-ethereal-input-area",
    userMessage: "chat-ethereal-user-msg",
    aiMessage: "chat-ethereal-ai-msg",
    inputWrapper: "chat-ethereal-input-wrapper",
    inputTextarea: "chat-ethereal-textarea",
    sendButton: "chat-ethereal-send-btn",
    sendButtonActive: "chat-ethereal-send-btn-active",
    emptyState: "chat-ethereal-empty",
    emptyIcon: "chat-ethereal-empty-icon",
    emptyTitle: "chat-ethereal-empty-title",
    emptyDescription: "chat-ethereal-empty-desc",
    suggestionButton: "chat-ethereal-suggestion",
    llmCallCluster: "chat-ethereal-llm-cluster",
    llmCallHeader: "chat-ethereal-llm-header",
    llmCallBody: "chat-ethereal-llm-body",
    toolCall: "chat-ethereal-tool",
    reasoning: "chat-ethereal-reasoning",
    content: "chat-ethereal-content",
  },
  motion: {
    messageAppear: "animate-ethereal-float",
    buttonPress: "active:scale-90",
    transition: "transition-all duration-300 ease-out",
  },
};

// 极简工业·钛度主题
const industrialTheme: ChatThemeConfig = {
  id: "industrial",
  name: "极简工业·钛度",
  description: "冷硬的金属质感，精密的工业美学",
  classPrefix: "theme-industrial",
  previewColors: {
    primary: "#D1D1D1",
    background: "#121213",
    accent: "#FF4500",
  },
  components: {
    chatContainer: "chat-industrial",
    header: "chat-industrial-header",
    messageArea: "chat-industrial-messages",
    inputArea: "chat-industrial-input-area",
    userMessage: "chat-industrial-user-msg",
    aiMessage: "chat-industrial-ai-msg",
    inputWrapper: "chat-industrial-input-wrapper",
    inputTextarea: "chat-industrial-textarea",
    sendButton: "chat-industrial-send-btn",
    sendButtonActive: "chat-industrial-send-btn-active",
    emptyState: "chat-industrial-empty",
    emptyIcon: "chat-industrial-empty-icon",
    emptyTitle: "chat-industrial-empty-title",
    emptyDescription: "chat-industrial-empty-desc",
    suggestionButton: "chat-industrial-suggestion",
    llmCallCluster: "chat-industrial-llm-cluster",
    llmCallHeader: "chat-industrial-llm-header",
    llmCallBody: "chat-industrial-llm-body",
    toolCall: "chat-industrial-tool",
    reasoning: "chat-industrial-reasoning",
    content: "chat-industrial-content",
  },
  motion: {
    messageAppear: "animate-industrial-scan",
    buttonPress: "active:shadow-industrial-inset",
    transition: "transition-all duration-150",
  },
};

// 科技商务风主题
const techbizTheme: ChatThemeConfig = {
  id: "techbiz",
  name: "科技商务",
  description: "专业可信的科技蓝调，适合企业级应用",
  classPrefix: "theme-techbiz",
  previewColors: {
    primary: "#2563EB",
    background: "#FAFBFC",
    accent: "#F59E0B",
  },
  components: {
    chatContainer: "chat-techbiz",
    header: "chat-techbiz-header",
    messageArea: "chat-techbiz-messages",
    inputArea: "chat-techbiz-input-area",
    userMessage: "chat-techbiz-user-msg",
    aiMessage: "chat-techbiz-ai-msg",
    inputWrapper: "chat-techbiz-input-wrapper",
    inputTextarea: "chat-techbiz-textarea",
    sendButton: "chat-techbiz-send-btn",
    sendButtonActive: "chat-techbiz-send-btn-active",
    emptyState: "chat-techbiz-empty",
    emptyIcon: "chat-techbiz-empty-icon",
    emptyTitle: "chat-techbiz-empty-title",
    emptyDescription: "chat-techbiz-empty-desc",
    suggestionButton: "chat-techbiz-suggestion",
    llmCallCluster: "chat-techbiz-llm-cluster",
    llmCallHeader: "chat-techbiz-llm-header",
    llmCallBody: "chat-techbiz-llm-body",
    toolCall: "chat-techbiz-tool",
    reasoning: "chat-techbiz-reasoning",
    content: "chat-techbiz-content",
  },
  motion: {
    messageAppear: "animate-fade-in",
    buttonPress: "active:scale-95",
    transition: "transition-all duration-200",
  },
};

// 温暖电商风主题
const warmshopTheme: ChatThemeConfig = {
  id: "warmshop",
  name: "温暖电商",
  description: "亲和友好的暖橙色调，促进商业转化",
  classPrefix: "theme-warmshop",
  previewColors: {
    primary: "#FF6B35",
    background: "#FFF9F5",
    accent: "#1E3A5F",
  },
  components: {
    chatContainer: "chat-warmshop",
    header: "chat-warmshop-header",
    messageArea: "chat-warmshop-messages",
    inputArea: "chat-warmshop-input-area",
    userMessage: "chat-warmshop-user-msg",
    aiMessage: "chat-warmshop-ai-msg",
    inputWrapper: "chat-warmshop-input-wrapper",
    inputTextarea: "chat-warmshop-textarea",
    sendButton: "chat-warmshop-send-btn",
    sendButtonActive: "chat-warmshop-send-btn-active",
    emptyState: "chat-warmshop-empty",
    emptyIcon: "chat-warmshop-empty-icon",
    emptyTitle: "chat-warmshop-empty-title",
    emptyDescription: "chat-warmshop-empty-desc",
    suggestionButton: "chat-warmshop-suggestion",
    llmCallCluster: "chat-warmshop-llm-cluster",
    llmCallHeader: "chat-warmshop-llm-header",
    llmCallBody: "chat-warmshop-llm-body",
    toolCall: "chat-warmshop-tool",
    reasoning: "chat-warmshop-reasoning",
    content: "chat-warmshop-content",
  },
  motion: {
    messageAppear: "animate-fade-in",
    buttonPress: "active:scale-90",
    transition: "transition-all duration-250 ease-out",
  },
};

// 极简高端风主题
const luxeminTheme: ChatThemeConfig = {
  id: "luxemin",
  name: "极简高端",
  description: "黑金配色的奢华质感，彰显品牌格调",
  classPrefix: "theme-luxemin",
  previewColors: {
    primary: "#18181B",
    background: "#FFFFFF",
    accent: "#D4AF37",
  },
  components: {
    chatContainer: "chat-luxemin",
    header: "chat-luxemin-header",
    messageArea: "chat-luxemin-messages",
    inputArea: "chat-luxemin-input-area",
    userMessage: "chat-luxemin-user-msg",
    aiMessage: "chat-luxemin-ai-msg",
    inputWrapper: "chat-luxemin-input-wrapper",
    inputTextarea: "chat-luxemin-textarea",
    sendButton: "chat-luxemin-send-btn",
    sendButtonActive: "chat-luxemin-send-btn-active",
    emptyState: "chat-luxemin-empty",
    emptyIcon: "chat-luxemin-empty-icon",
    emptyTitle: "chat-luxemin-empty-title",
    emptyDescription: "chat-luxemin-empty-desc",
    suggestionButton: "chat-luxemin-suggestion",
    llmCallCluster: "chat-luxemin-llm-cluster",
    llmCallHeader: "chat-luxemin-llm-header",
    llmCallBody: "chat-luxemin-llm-body",
    toolCall: "chat-luxemin-tool",
    reasoning: "chat-luxemin-reasoning",
    content: "chat-luxemin-content",
  },
  motion: {
    messageAppear: "animate-fade-in",
    buttonPress: "active:scale-98",
    transition: "transition-all duration-150",
  },
};

// 主题注册表
class ThemeRegistry {
  private themes: Map<ChatThemeId, ChatThemeConfig> = new Map();

  constructor() {
    // 注册内置主题
    this.register(defaultTheme);
    this.register(etherealTheme);
    this.register(industrialTheme);
    this.register(techbizTheme);
    this.register(warmshopTheme);
    this.register(luxeminTheme);
  }

  register(theme: ChatThemeConfig): void {
    this.themes.set(theme.id, theme);
  }

  get(id: ChatThemeId): ChatThemeConfig {
    return this.themes.get(id) || defaultTheme;
  }

  getAll(): ChatThemeConfig[] {
    return Array.from(this.themes.values());
  }

  getAllIds(): ChatThemeId[] {
    return Array.from(this.themes.keys());
  }
}

// 单例导出
export const themeRegistry = new ThemeRegistry();

// 便捷函数
export function getTheme(id: ChatThemeId): ChatThemeConfig {
  return themeRegistry.get(id);
}

export function getAllThemes(): ChatThemeConfig[] {
  return themeRegistry.getAll();
}
