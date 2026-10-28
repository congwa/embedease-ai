"use client";

import { useRef, useState } from "react";
import { AlertCircle, Bot, Network, X } from "lucide-react";
import {
  ChatContainerContent,
  ChatContainerRoot,
} from "@/components/prompt-kit/chat-container";
import { Message } from "@/components/prompt-kit/message";
import { ScrollButton } from "@/components/prompt-kit/scroll-button";
import { ChatRichInput } from "@/components/features/chat/ChatRichInput";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { useConversationStore, useChatStore, type TimelineItem } from "@/stores";
import {
  LLMCallCluster,
  TimelineUserMessageItem,
  TimelineErrorItem,
  TimelineComplaintEventItem,
  TimelineToolCallItem,
  TimelineSupportEventItem,
  TimelineGreetingItem,
  TimelineSkillActivatedItem,
} from "@/components/features/chat/timeline";
import {
  useChatThemeOptional,
  ThemeSwitcherIcon,
  ThemedEmptyState,
  ThemedEmptyIcon,
  ThemedEmptyTitle,
  ThemedEmptyDescription,
  ThemedSuggestionButton,
} from "@/components/features/chat/themes";
import { QuickQuestionBar } from "@/components/features/chat/QuickQuestionBar";
import { useSuggestedQuestions } from "@/lib/hooks/use-suggested-questions";
import { useAgentStore } from "@/stores/agent-store";
import { ComplaintStatusBar } from "@/components/features/chat/ComplaintStatusBar";
import type { ComplaintEventItem } from "@/lib/timeline/types";
import { ChatRunStatus } from "./ChatRunStatus";

interface ChatContentProps {
  isHumanMode?: boolean;
  wsConnected?: boolean;
  wsSendMessage?: (content: string) => void;
}

export function ChatContent({ isHumanMode = false, wsConnected = false, wsSendMessage }: ChatContentProps) {
  // 从 Store 获取状态
  const timelineState = useChatStore((s) => s.timelineState);
  const timeline = timelineState.timeline;
  const isStreaming = useChatStore((s) => s.isStreaming);
  const error = useChatStore((s) => s.error);
  const sendMessageToAI = useChatStore((s) => s.sendMessage);
  const abortStream = useChatStore((s) => s.abortStream);
  const addUserMessageToTimeline = useChatStore((s) => s.addUserMessageOnly);
  
  const currentConversation = useConversationStore((s) => 
    s.conversations.find((c) => c.id === s.currentConversationId)
  );
  
  // 获取当前 Agent 和推荐问题
  const activeAgent = useAgentStore((s) => s.activeAgent());
  const agents = useAgentStore((s) => s.agents);
  const activateAgent = useAgentStore((s) => s.activateAgent);
  const { questions: suggestedQuestions, trackClick } = useSuggestedQuestions({
    agentId: activeAgent?.id,
  });
  
  // Supervisor 状态
  const currentAgentName = useChatStore((s) => s.currentAgentName);

  // 从 timeline 中提取客诉事件，用于状态栏
  const complaintEvents = timeline.filter(
    (item): item is ComplaintEventItem => item.type === "complaint.event"
  );
  
  const title = currentConversation?.title || "";
  const [prompt, setPrompt] = useState("");
  const [dismissedError, setDismissedError] = useState<string | null>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const isErrorVisible = Boolean(error) && dismissedError !== error;
  
  // 主题系统
  const theme = useChatThemeOptional();
  const themeId = theme?.themeId || "default";

  // 统一的消息发送函数：人工模式用 WebSocket，AI 模式用 API
  const sendMessage = (content: string) => {
    if (isHumanMode && wsConnected && wsSendMessage) {
      // 人工模式：添加用户消息到 timeline，然后通过 WebSocket 发送
      addUserMessageToTimeline(content);
      wsSendMessage(content);
    } else {
      // AI 模式：通过 API 发送（内部会添加用户消息到 timeline）
      sendMessageToAI(content);
    }
  };

  // 处理推荐问题点击
  const handleSuggestionClick = (question: string, questionId?: string) => {
    if (questionId) {
      trackClick(questionId);
    }
    sendMessage(question);
  };

  const handleButtonClick = () => {
    if (isStreaming) {
      abortStream();
    } else {
      if (!prompt.trim()) return;
      sendMessage(prompt.trim());
      setPrompt("");
    }
  };

  const renderTimelineItem = (item: TimelineItem) => {
    switch (item.type) {
      case "user.message":
        return (
          <Message
            key={item.id}
            className="mx-auto flex w-full max-w-3xl flex-col gap-2 px-6 items-end"
          >
            <TimelineUserMessageItem item={item} />
          </Message>
        );

      case "llm.call.cluster":
        return (
          <Message
            key={item.id}
            className="mx-auto flex w-full max-w-3xl flex-col gap-2 px-6 items-start"
          >
            <div className="flex w-full flex-col gap-3">
              <LLMCallCluster item={item} isStreaming={isStreaming} />
            </div>
          </Message>
        );

      case "tool.call":
        return (
          <Message
            key={item.id}
            className="mx-auto flex w-full max-w-3xl flex-col gap-2 px-6 items-start"
          >
            <div className="flex w-full flex-col gap-3">
              <TimelineToolCallItem item={item} />
            </div>
          </Message>
        );

      case "error":
        return (
          <div
            key={item.id}
            className="mx-auto w-full max-w-3xl px-6"
          >
            <TimelineErrorItem item={item} />
          </div>
        );

      case "final":
        // FinalItem 不单独渲染，streaming 结束的标志
        return null;

      case "memory.event":
        // 记忆事件暂不渲染（可后续扩展）
        return null;

      case "support.event":
        return (
          <Message
            key={item.id}
            className="mx-auto flex w-full max-w-3xl flex-col gap-2 px-6 items-start"
          >
            <TimelineSupportEventItem item={item} />
          </Message>
        );

      case "complaint.event":
        return (
          <Message
            key={item.id}
            className="mx-auto flex w-full max-w-3xl flex-col gap-2 px-6 items-start"
          >
            <TimelineComplaintEventItem item={item} />
          </Message>
        );

      case "greeting":
        return (
          <Message
            key={item.id}
            className="mx-auto flex w-full max-w-3xl flex-col gap-2 px-6 items-start"
          >
            <TimelineGreetingItem
              item={item}
              onCtaClick={(payload) => sendMessage(payload)}
            />
          </Message>
        );

      case "waiting":
        // The run-level status stays visible when llm.call.start removes this SDK placeholder.
        return null;

      case "skill.activated":
        return (
          <TimelineSkillActivatedItem key={item.id} item={item} />
        );

      default:
        return null;
    }
  };

  return (
    <main className={cn(
      "flex h-screen flex-col overflow-hidden",
      themeId === "ethereal" && "chat-ethereal",
      themeId === "industrial" && "chat-industrial"
    )}>
      {/* 顶部栏 */}
      <header className={cn(
        "z-10 flex h-16 w-full shrink-0 items-center gap-2 px-4",
        themeId === "default" && "border-b border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900",
        themeId === "ethereal" && "chat-ethereal-header",
        themeId === "industrial" && "chat-industrial-header"
      )}>
        <SidebarTrigger className="-ml-1" />
        <div className={cn(
          "flex-1 text-sm font-medium",
          themeId === "default" && "text-zinc-900 dark:text-zinc-100",
          themeId === "ethereal" && "text-[var(--chat-text-primary)]",
          themeId === "industrial" && "text-[var(--chat-text-primary)] uppercase tracking-wider text-xs"
        )}>
          {title || "新对话"}
        </div>

        {/* Supervisor 当前 Agent 显示 */}
        {currentAgentName && (
          <Badge variant="secondary" className="text-xs gap-1">
            <Network className="h-3 w-3" />
            {currentAgentName}
          </Badge>
        )}

        {/* Agent 切换器 */}
        {agents.length > 0 && (
          <Select
            value={activeAgent?.id || ""}
            onValueChange={(id) => activateAgent(id)}
          >
            <SelectTrigger className="w-[160px] h-8 text-xs">
              <Bot className="h-3 w-3 mr-1" />
              <SelectValue placeholder="选择 Agent" />
            </SelectTrigger>
            <SelectContent>
              {agents.filter(a => a.status === "enabled").map((agent) => (
                <SelectItem key={agent.id} value={agent.id} className="text-xs">
                  <div className="flex items-center gap-1">
                    {agent.is_supervisor && <Network className="h-3 w-3 text-orange-500" />}
                    {agent.name}
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}

        {/* 主题切换器 */}
        {theme && <ThemeSwitcherIcon />}
      </header>

      {/* 客诉处理阶段状态栏 */}
      {complaintEvents.length > 0 && (
        <ComplaintStatusBar complaintEvents={complaintEvents} />
      )}

      {/* 消息区域 */}
      <div ref={chatContainerRef} className={cn(
        "relative flex-1 overflow-y-auto",
        themeId === "ethereal" && "chat-ethereal-messages",
        themeId === "industrial" && "chat-industrial-messages"
      )}>
        <ChatContainerRoot className="h-full">
          <ChatContainerContent className="space-y-3 px-5 py-12">
            {timeline.length === 0 && (
              <ThemedEmptyState className="flex flex-col items-center justify-center py-20">
                <ThemedEmptyIcon className="mb-4 flex h-16 w-16 items-center justify-center rounded-full">
                  <span className="text-2xl">🛒</span>
                </ThemedEmptyIcon>
                <ThemedEmptyTitle className="mb-2 text-xl font-semibold">
                  商品推荐助手
                </ThemedEmptyTitle>
                <ThemedEmptyDescription className="text-center text-sm">
                  告诉我你想要什么，我来帮你找到最合适的商品
                </ThemedEmptyDescription>
                {suggestedQuestions.welcome.length > 0 && (
                  <div className="mt-6 flex flex-wrap justify-center gap-2">
                    {suggestedQuestions.welcome.map((item) => (
                      <ThemedSuggestionButton
                        key={item.id}
                        className="px-3 py-1.5 text-xs"
                        onClick={() => handleSuggestionClick(item.question, item.id)}
                        disabled={isStreaming}
                      >
                        {item.question}
                      </ThemedSuggestionButton>
                    ))}
                  </div>
                )}
              </ThemedEmptyState>
            )}

            {timeline.map((item) => renderTimelineItem(item))}
            <ChatRunStatus state={timelineState} isStreaming={isStreaming && !isHumanMode} />
          </ChatContainerContent>

          <div className="absolute bottom-4 left-1/2 flex w-full max-w-3xl -translate-x-1/2 justify-end px-5">
            <ScrollButton className="shadow-sm" />
          </div>
        </ChatContainerRoot>
      </div>

      {/* 输入区域 */}
      <div className={cn(
        "z-10 shrink-0 px-3 pb-3 md:px-5 md:pb-5",
        themeId === "ethereal" && "chat-ethereal-input-area",
        themeId === "industrial" && "chat-industrial-input-area"
      )}>
        <div className="mx-auto max-w-3xl">
          {/* 快捷问题栏 */}
          {suggestedQuestions.input.length > 0 && (
            <QuickQuestionBar
              questions={suggestedQuestions.input}
              onSelect={(question, id) => handleSuggestionClick(question, id)}
              disabled={isStreaming}
            />
          )}
          {/* 错误提示 */}
          {error && isErrorVisible && (
            <div className="mb-3 flex items-center gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-600 dark:bg-red-900/20 dark:text-red-400">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span className="flex-1">{error}</span>
              <button
                onClick={() => setDismissedError(error)}
                className="shrink-0 rounded p-1 hover:bg-red-100 dark:hover:bg-red-900/40"
                title="关闭错误提示"
                aria-label="关闭错误提示"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          )}
          <ChatRichInput
            value={prompt}
            onValueChange={setPrompt}
            onSubmit={handleButtonClick}
            placeholder={themeId === "industrial" ? "INPUT QUERY..." : "描述你想要的商品..."}
            isLoading={isStreaming}
            showToolbar={false}
            className={cn(
              "relative z-10 w-full shadow-sm",
              themeId === "ethereal" && "chat-ethereal-input-wrapper",
              themeId === "industrial" && "chat-industrial-input-wrapper"
            )}
          />
        </div>
      </div>
    </main>
  );
}
