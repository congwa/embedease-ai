/**
 * Chat SDK 切换配置
 *
 * 通过环境变量控制使用新 SDK 还是旧 SDK：
 * - NEXT_PUBLIC_USE_NEW_CHAT_SDK=true  → 使用新 SDK（默认）
 * - NEXT_PUBLIC_USE_NEW_CHAT_SDK=false → 回退到旧 SDK
 */

export const ChatSDKConfig = {
  /** 是否使用新 SDK（默认 true） */
  get useNewSDK(): boolean {
    // 服务端渲染时默认使用新 SDK
    if (typeof window === "undefined") {
      return process.env.NEXT_PUBLIC_USE_NEW_CHAT_SDK !== "false";
    }
    return process.env.NEXT_PUBLIC_USE_NEW_CHAT_SDK !== "false";
  },

  /** 调试模式 */
  debug: process.env.NODE_ENV === "development",
} as const;

/**
 * 检查是否启用新 SDK
 */
export function isNewSDKEnabled(): boolean {
  return ChatSDKConfig.useNewSDK;
}

/**
 * 获取当前 SDK 版本标识（用于日志）
 */
export function getSDKVersion(): "new" | "legacy" {
  return isNewSDKEnabled() ? "new" : "legacy";
}
