import React from "react";
import { createRoot } from "react-dom/client";
import { EmbedWidget } from "./EmbedWidget";

interface EmbedConfig {
  apiBaseUrl?: string;
  position?: "bottom-right" | "bottom-left";
  primaryColor?: string;
  title?: string;
  placeholder?: string;
}

declare global {
  interface Window {
    EmbedAiChat: {
      init: (config?: EmbedConfig) => void;
      destroy: () => void;
    };
  }
}

let root: ReturnType<typeof createRoot> | null = null;
let container: HTMLDivElement | null = null;

function init(config: EmbedConfig = {}) {
  // 防止重复初始化
  if (container) {
    console.warn("[EmbedAiChat] Already initialized");
    return;
  }

  // 创建容器
  container = document.createElement("div");
  container.id = "embed-ai-chat-root";
  container.style.cssText = "position: fixed; z-index: 2147483647;";
  document.body.appendChild(container);

  // 渲染组件
  root = createRoot(container);
  root.render(<EmbedWidget config={config} />);

  console.log("[EmbedAiChat] Initialized", config);
}

function destroy() {
  if (root) {
    root.unmount();
    root = null;
  }
  if (container) {
    container.remove();
    container = null;
  }
  console.log("[EmbedAiChat] Destroyed");
}

// 暴露全局 API
window.EmbedAiChat = { init, destroy };

// 自动初始化（如果 script 标签有 data-auto-init 属性）
const currentScript = document.currentScript as HTMLScriptElement | null;
if (currentScript?.dataset.autoInit !== undefined) {
  const config: EmbedConfig = {};
  if (currentScript.dataset.apiBaseUrl) {
    config.apiBaseUrl = currentScript.dataset.apiBaseUrl;
  }
  if (currentScript.dataset.position) {
    config.position = currentScript.dataset.position as EmbedConfig["position"];
  }
  if (currentScript.dataset.primaryColor) {
    config.primaryColor = currentScript.dataset.primaryColor;
  }
  if (currentScript.dataset.title) {
    config.title = currentScript.dataset.title;
  }

  // DOM ready 后自动初始化
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => init(config));
  } else {
    init(config);
  }
}
