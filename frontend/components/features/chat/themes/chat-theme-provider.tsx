"use client";

import React, { createContext, useContext, useState, useEffect, useCallback, useSyncExternalStore } from "react";
import { type ChatThemeId, type ChatThemeConfig, getTheme, getAllThemes } from "./theme-registry";

export type ColorMode = "light" | "dark" | "system";

interface ChatThemeContextValue {
  // 当前主题
  theme: ChatThemeConfig;
  themeId: ChatThemeId;
  // 切换主题
  setTheme: (id: ChatThemeId) => void;
  // 获取所有可用主题
  availableThemes: ChatThemeConfig[];
  // 便捷方法：获取组件类名
  getClass: (component: keyof ChatThemeConfig["components"]) => string;
  // 便捷方法：获取动效类名
  getMotion: (motion: keyof ChatThemeConfig["motion"]) => string;
  // 颜色模式
  colorMode: ColorMode;
  setColorMode: (mode: ColorMode) => void;
  // 实际生效的模式（system 会解析为 light 或 dark）
  resolvedColorMode: "light" | "dark";
}

const ChatThemeContext = createContext<ChatThemeContextValue | null>(null);

const THEME_STORAGE_KEY = "embedease-chat-theme";
const COLOR_MODE_STORAGE_KEY = "embedease-color-mode";

const VALID_THEMES: ChatThemeId[] = ["default", "ethereal", "industrial", "techbiz", "warmshop", "luxemin"];

interface ChatThemeProviderProps {
  children: React.ReactNode;
  defaultTheme?: ChatThemeId;
  defaultColorMode?: ColorMode;
}

export function ChatThemeProvider({ 
  children, 
  defaultTheme = "default",
  defaultColorMode = "system"
}: ChatThemeProviderProps) {
  // 初始化时从 localStorage 读取
  const getInitialTheme = (): ChatThemeId => {
    if (typeof window === "undefined") return defaultTheme;
    const stored = localStorage.getItem(THEME_STORAGE_KEY) as ChatThemeId | null;
    return stored && VALID_THEMES.includes(stored) ? stored : defaultTheme;
  };

  const getInitialColorMode = (): ColorMode => {
    if (typeof window === "undefined") return defaultColorMode;
    const stored = localStorage.getItem(COLOR_MODE_STORAGE_KEY) as ColorMode | null;
    return stored && ["light", "dark", "system"].includes(stored) ? stored : defaultColorMode;
  };

  const [themeId, setThemeId] = useState<ChatThemeId>(getInitialTheme);
  const [colorMode, setColorModeState] = useState<ColorMode>(getInitialColorMode);
  const [resolvedColorMode, setResolvedColorMode] = useState<"light" | "dark">("light");
  
  // 使用 useSyncExternalStore 检测客户端渲染，避免 hydration 问题
  const mounted = useSyncExternalStore(
    () => () => {},
    () => true,
    () => false
  );

  // 解析系统颜色模式
  useEffect(() => {
    const updateResolvedMode = () => {
      if (colorMode === "system") {
        const isDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
        setResolvedColorMode(isDark ? "dark" : "light");
      } else {
        setResolvedColorMode(colorMode);
      }
    };

    updateResolvedMode();

    // 监听系统主题变化
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    const handleChange = () => {
      if (colorMode === "system") {
        updateResolvedMode();
      }
    };

    mediaQuery.addEventListener("change", handleChange);
    return () => mediaQuery.removeEventListener("change", handleChange);
  }, [colorMode]);

  // 切换主题
  const setTheme = useCallback((id: ChatThemeId) => {
    setThemeId(id);
    localStorage.setItem(THEME_STORAGE_KEY, id);
    // DOM 更新统一在 useEffect 中处理，避免重复
  }, []);

  // 切换颜色模式
  const setColorMode = useCallback((mode: ColorMode) => {
    setColorModeState(mode);
    localStorage.setItem(COLOR_MODE_STORAGE_KEY, mode);
  }, []);

  // 更新 DOM 属性
  useEffect(() => {
    if (mounted) {
      document.documentElement.setAttribute("data-chat-theme", themeId);
      
      // 更新 dark 类
      if (resolvedColorMode === "dark") {
        document.documentElement.classList.add("dark");
      } else {
        document.documentElement.classList.remove("dark");
      }
    }
  }, [mounted, themeId, resolvedColorMode]);

  const theme = getTheme(themeId);
  const availableThemes = getAllThemes();

  const getClass = useCallback(
    (component: keyof ChatThemeConfig["components"]) => {
      return theme.components[component];
    },
    [theme]
  );

  const getMotion = useCallback(
    (motion: keyof ChatThemeConfig["motion"]) => {
      return theme.motion[motion];
    },
    [theme]
  );

  const value: ChatThemeContextValue = {
    theme,
    themeId,
    setTheme,
    availableThemes,
    getClass,
    getMotion,
    colorMode,
    setColorMode,
    resolvedColorMode,
  };

  // 避免 SSR 闪烁
  if (!mounted) {
    return (
      <ChatThemeContext.Provider value={value}>
        {children}
      </ChatThemeContext.Provider>
    );
  }

  return (
    <ChatThemeContext.Provider value={value}>
      {children}
    </ChatThemeContext.Provider>
  );
}

// Hook
export function useChatTheme(): ChatThemeContextValue {
  const context = useContext(ChatThemeContext);
  if (!context) {
    throw new Error("useChatTheme must be used within a ChatThemeProvider");
  }
  return context;
}

// 可选 Hook：检查是否在 Provider 内
export function useChatThemeOptional(): ChatThemeContextValue | null {
  return useContext(ChatThemeContext);
}
