/**
 * 中间件标签配置
 */

import {
  ListTodo,
  Brain,
  FileText,
  RotateCcw,
  Gauge,
  Eraser,
  Layers,
  Sparkles,
  Settings,
  Shield,
} from "lucide-react";
import type { MiddlewareInfo, MiddlewarePipelineInfoExtended } from "./types";

// ========== 中间件开关配置 ==========

export const MIDDLEWARE_LABELS: Record<string, MiddlewareInfo> = {
  todo_enabled: {
    label: "TODO 规划",
    desc: "自动拆解复杂任务为步骤",
    icon: ListTodo,
  },
  memory_enabled: {
    label: "记忆系统",
    desc: "记住用户偏好和历史",
    icon: Brain,
  },
  summarization_enabled: {
    label: "上下文压缩",
    desc: "压缩长对话保持上下文",
    icon: FileText,
  },
  tool_retry_enabled: {
    label: "工具重试",
    desc: "工具调用失败时自动重试",
    icon: RotateCcw,
  },
  tool_limit_enabled: {
    label: "工具限制",
    desc: "限制单次对话工具调用次数",
    icon: Gauge,
  },
  noise_filter_enabled: {
    label: "噪音过滤",
    desc: "过滤冗余信息提升质量",
    icon: Eraser,
  },
  sliding_window_enabled: {
    label: "滑动窗口",
    desc: "限制上下文长度节省 token",
    icon: Layers,
  },
  pii_enabled: {
    label: "PII 检测",
    desc: "检测并处理个人敏感信息",
    icon: Shield,
  },
};

export function getMiddlewareLabel(key: string): MiddlewareInfo {
  return (
    MIDDLEWARE_LABELS[key] || {
      label: key.replace(/_/g, " "),
      desc: "",
      icon: Settings,
    }
  );
}

// ========== 中间件管道配置 ==========

export const MIDDLEWARE_PIPELINE_LABELS: Record<string, MiddlewarePipelineInfoExtended> = {
  MemoryOrchestration: {
    label: "记忆编排",
    desc: "用户记忆的读取和写入",
    icon: Brain,
    details: [
      "对话开始时加载用户历史记忆",
      "对话过程中捕获重要信息",
      "对话结束时保存新记忆",
    ],
  },
  PIIDetection: {
    label: "隐私保护",
    desc: "检测和处理个人敏感信息",
    icon: Shield,
    details: [
      "检测邮箱、信用卡、IP 等敏感信息",
      "支持 block/redact/mask/hash 策略",
      "可配置检测范围（输入/输出）",
    ],
  },
  ResponseSanitization: {
    label: "响应净化",
    desc: "过滤敏感内容和异常响应",
    icon: Eraser,
    details: [
      "检测模型返回的异常格式",
      "过滤可能的敏感或不当内容",
      "替换为友好的用户提示",
    ],
  },
  SSE: {
    label: "流式输出",
    desc: "实时流式输出响应内容",
    icon: Sparkles,
    details: [
      "发送 llm.call.start 事件",
      "实时推送模型生成内容",
      "发送 llm.call.end 事件",
    ],
  },
  TodoList: {
    label: "任务规划",
    desc: "自动拆解复杂任务为步骤",
    icon: ListTodo,
    details: [
      "识别用户的复杂任务",
      "自动拆解为可执行步骤",
      "按步骤逐一完成",
    ],
  },
  SequentialToolExecution: {
    label: "顺序执行",
    desc: "按顺序执行工具调用",
    icon: Layers,
    details: [
      "收集模型的多个工具调用请求",
      "按顺序依次执行",
      "汇总结果返回给模型",
    ],
  },
  NoiseFilter: {
    label: "噪音过滤",
    desc: "过滤冗余信息提升质量",
    icon: Eraser,
    details: [
      "识别响应中的冗余信息",
      "过滤无关的系统输出",
      "保留核心有价值内容",
    ],
  },
  Logging: {
    label: "日志记录",
    desc: "记录请求和响应日志",
    icon: FileText,
    details: [
      "记录 LLM 请求参数",
      "记录响应内容和耗时",
      "支持调试和审计",
    ],
  },
  ToolRetry: {
    label: "工具重试",
    desc: "工具调用失败时自动重试",
    icon: RotateCcw,
    details: [
      "捕获工具执行异常",
      "按配置的次数自动重试",
      "超过重试次数后返回错误",
    ],
  },
  ToolCallLimit: {
    label: "调用限制",
    desc: "限制单次对话工具调用次数",
    icon: Gauge,
    details: [
      "统计当前对话的工具调用次数",
      "超过限制时阻止继续调用",
      "防止无限循环调用",
    ],
  },
  SlidingWindow: {
    label: "滑动窗口",
    desc: "限制上下文长度节省 token",
    icon: Layers,
    details: [
      "监控对话历史长度",
      "超出窗口时裁剪早期消息",
      "保留最近的对话上下文",
    ],
  },
  Summarization: {
    label: "上下文压缩",
    desc: "压缩长对话保持上下文",
    icon: FileText,
    details: [
      "检测对话历史过长",
      "自动生成历史摘要",
      "用摘要替换详细历史",
    ],
  },
};

export function getMiddlewarePipelineLabel(name: string): MiddlewarePipelineInfoExtended {
  return MIDDLEWARE_PIPELINE_LABELS[name] || { label: name, desc: "" };
}
