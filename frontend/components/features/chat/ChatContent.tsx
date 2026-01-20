"use client";

import { useRef, useState } from "react";
import { AlertCircle, ArrowUp, Bot, Network, Square, X } from "lucide-react";
import {
  ChatContainerContent,
  ChatContainerRoot,
} from "@/components/prompt-kit/chat-container";
import { Message } from "@/components/prompt-kit/message";
import {
  PromptInput,
  PromptInputActions,
  PromptInputTextarea,
} from "@/components/prompt-kit/prompt-input";
import { ScrollButton } from "@/components/prompt-kit/scroll-button";
import { Button } from "@/components/ui/button";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { useConversationStore, useChatStore, type TimelineItem } from "@/stores";
import {
  LLMCallCluster,
  TimelineUserMessageItem,
  TimelineErrorItem,
  TimelineToolCallItem,
  TimelineSupportEventItem,
  TimelineGreetingItem,
  TimelineWaitingItem,
} from "./timeline";
import {
  useChatThemeOptional,
  ThemeSwitcherIcon,
  ThemedEmptyState,
  ThemedEmptyIcon,
  ThemedEmptyTitle,
  ThemedEmptyDescription,
  ThemedSuggestionButton,
} from "./themes";
import { QuickQuestionBar } from "./QuickQuestionBar";
import { useSuggestedQuestions } from "@/lib/hooks/use-suggested-questions";
import { useAgentStore } from "@/stores/agent-store";

export function ChatContent() {
  // 从 Store 获取状态
  const timeline = useChatStore((s) => s.timelineState.timeline);
  const isStreaming = useChatStore((s) => s.isStreaming);
  const error = useChatStore((s) => s.error);
  const sendMessage = useChatStore((s) => s.sendMessage);
  const abortStream = useChatStore((s) => s.abortStream);
  
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
  
  const title = currentConversation?.title || "";
  const [prompt, setPrompt] = useState("");
  const [dismissedError, setDismissedError] = useState<string | null>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const isErrorVisible = Boolean(error) && dismissedError !== error;
  
  // 主题系统
  const theme = useChatThemeOptional();
  const themeId = theme?.themeId || "default";

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

  const renderTimelineItem = (item: TimelineItem, index: number) => {
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
        return (
          <Message
            key={item.id}
            className="mx-auto flex w-full max-w-3xl flex-col gap-2 px-6 items-start"
          >
            <TimelineWaitingItem item={item} />
          </Message>
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
                <div className="mt-6 flex flex-wrap justify-center gap-2">
                  {(suggestedQuestions.welcome.length > 0
                    ? suggestedQuestions.welcome
                    : [{id: "1", question: "推荐一款降噪耳机"}, {id: "2", question: "有什么好的跑步鞋"}, {id: "3", question: "想买一台破壁机"}]
                  ).map((item) => (
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
              </ThemedEmptyState>
            )}

            {timeline.map((item, index) => renderTimelineItem(item, index))}
          </ChatContainerContent>

          <div className="absolute bottom-4 left-1/2 flex w-full max-w-3xl -translate-x-1/2 justify-end px-5">
            <ScrollButton className="shadow-sm" />
          </div>
        </ChatContainerRoot>
      </div>

      {/* 输入区域 */}
      <div className={cn(
        "z-10 shrink-0 px-3 pb-3 md:px-5 md:pb-5",
        themeId === "default" && "bg-white dark:bg-zinc-900",
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
          <PromptInput
            isLoading={isStreaming}
            value={prompt}
            onValueChange={setPrompt}
            onSubmit={handleButtonClick}
            className={cn(
              "relative z-10 w-full p-0 pt-1",
              themeId === "default" && "rounded-3xl border border-zinc-200 bg-white shadow-sm dark:border-zinc-700 dark:bg-zinc-800",
              themeId === "ethereal" && "chat-ethereal-input-wrapper",
              themeId === "industrial" && "chat-industrial-input-wrapper"
            )}
          >
            <div className="flex flex-col">
              <PromptInputTextarea
                placeholder={themeId === "industrial" ? "INPUT QUERY..." : "描述你想要的商品..."}
                className={cn(
                  "min-h-[44px] pl-4 pt-3 text-base leading-[1.3]",
                  themeId === "ethereal" && "chat-ethereal-textarea",
                  themeId === "industrial" && "chat-industrial-textarea"
                )}
              />

              <PromptInputActions className="mt-5 flex w-full items-center justify-end gap-2 px-3 pb-3">
                <Button
                  size="icon"
                  disabled={!isStreaming && !prompt.trim()}
                  onClick={handleButtonClick}
                  className={cn(
                    "h-9 w-9 transition-colors",
                    themeId === "default" && "rounded-full",
                    themeId === "ethereal" && cn(
                      "rounded-full",
                      prompt.trim() || isStreaming ? "chat-ethereal-send-btn-active" : "chat-ethereal-send-btn"
                    ),
                    themeId === "industrial" && cn(
                      "rounded-sm",
                      prompt.trim() || isStreaming ? "chat-industrial-send-btn-active" : "chat-industrial-send-btn"
                    ),
                    isStreaming && themeId === "default" && "bg-red-500 hover:bg-red-600 dark:bg-red-600 dark:hover:bg-red-700"
                  )}
                  title={isStreaming ? "停止生成" : "发送消息"}
                >
                  {isStreaming ? (
                    <Square className="h-4 w-4" />
                  ) : (
                    <ArrowUp className="h-4 w-4" />
                  )}
                </Button>
              </PromptInputActions>
            </div>
          </PromptInput>
        </div>
      </div>
    </main>
  );
}
