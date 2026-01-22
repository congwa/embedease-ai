// 聊天主题系统导出

export { ChatThemeProvider, useChatTheme, useChatThemeOptional, type ColorMode } from "./chat-theme-provider";
export { ThemeSwitcher, ThemeSwitcherIcon, ThemeSwitcherWithLabel } from "./theme-switcher";
export { ThemeSettingsDialog } from "./ThemeSettingsDialog";
export { themeRegistry, getTheme, getAllThemes, type ChatThemeId, type ChatThemeConfig } from "./theme-registry";

// 主题化组件
export {
  ThemedChatContainer,
  ThemedHeader,
  ThemedMessageArea,
  ThemedInputArea,
  ThemedUserMessage,
  ThemedAIMessage,
  ThemedInputWrapper,
  ThemedSendButton,
  ThemedEmptyState,
  ThemedEmptyIcon,
  ThemedEmptyTitle,
  ThemedEmptyDescription,
  ThemedSuggestionButton,
  ThemedLLMCluster,
  ThemedLLMHeader,
  ThemedLLMBody,
  ThemedReasoning,
  ThemedContent,
} from "./themed-components";
