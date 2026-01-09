"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { MessageCircle, X, Trash2, Minus, ChevronUp } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { EmbedChatContent } from "./EmbedChatContent";
import { useUserStore, useChatStore } from "@/stores";
import { createConversation } from "@/lib/api";

interface FloatingChatWidgetProps {
  className?: string;
}

const BUBBLE_SIZE = 56;
const EDGE_MARGIN = 16;
const SNAP_THRESHOLD = 24;
// 贴边时的长条尺寸：左右 20×80， 上下 80×20
const BAR_SHORT = 20;
const BAR_LONG = 80;
const PANEL_WIDTH = 380;
const PANEL_HEIGHT = 500;

const clamp = (value: number, min: number, max: number) => Math.min(Math.max(value, min), max);

const getInitialPosition = (): { x: number; y: number } => {
  if (typeof window === "undefined") {
    return { x: EDGE_MARGIN, y: EDGE_MARGIN };
  }
  return {
    x: window.innerWidth - BUBBLE_SIZE - EDGE_MARGIN,
    y: window.innerHeight - BUBBLE_SIZE - EDGE_MARGIN,
  };
};

type DockEdge = "left" | "right" | "top" | "bottom" | null;

export function FloatingChatWidget({ className }: FloatingChatWidgetProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [position, setPosition] = useState({ x: EDGE_MARGIN, y: EDGE_MARGIN });
  const [dockEdge, setDockEdge] = useState<DockEdge>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [isMounted, setIsMounted] = useState(false);

  // 从 Store 获取状态
  const userId = useUserStore((s) => s.userId);
  const isUserLoading = useUserStore((s) => s.isLoading);
  const initUser = useUserStore((s) => s.initUser);
  
  const timeline = useChatStore((s) => s.timelineState.timeline);
  const isStreaming = useChatStore((s) => s.isStreaming);
  const error = useChatStore((s) => s.error);
  const sendMessageToStore = useChatStore((s) => s.sendMessage);
  const clearMessages = useChatStore((s) => s.clearMessages);
  const abortStream = useChatStore((s) => s.abortStream);

  // 初始化用户
  useEffect(() => {
    initUser();
  }, [initUser]);

  // 发送消息（自动创建会话）
  const handleSendMessage = useCallback(
    async (content: string) => {
      if (!userId) return;

      let convId = conversationId;

      // 如果没有会话，先创建
      if (!convId) {
        try {
          const conversation = await createConversation({ user_id: userId });
          convId = conversation.id;
          setConversationId(convId);
        } catch (err) {
          console.error("[embed] 创建会话失败:", err);
          return;
        }
      }

      sendMessageToStore(content);
    },
    [userId, conversationId, sendMessageToStore]
  );

  // 清空对话（创建新会话）
  const handleClearChat = useCallback(async () => {
    if (!userId) return;

    // 如果正在流式传输，先中断
    if (isStreaming) {
      abortStream();
    }

    // 清空消息
    clearMessages();

    // 创建新会话
    try {
      const conversation = await createConversation({ user_id: userId });
      setConversationId(conversation.id);
      console.log("[embed] 创建新会话:", conversation.id);
    } catch (err) {
      console.error("[embed] 创建新会话失败:", err);
      setConversationId(null);
    }
  }, [userId, isStreaming, abortStream, clearMessages]);

  const buttonRef = useRef<HTMLButtonElement | null>(null);
  const dragStateRef = useRef<{
    pointerId: number | null;
    offsetX: number;
    offsetY: number;
  }>({
    pointerId: null,
    offsetX: 0,
    offsetY: 0,
  });
  const cleanupRef = useRef<(() => void) | null>(null);
  const didDragRef = useRef(false);
  const positionRef = useRef(position);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    positionRef.current = position;
  }, [position]);

  // 挂载后设置初始位置到右下角（避免 SSR 初始 0 尺寸）
  useEffect(() => {
    if (!isMounted || typeof window === "undefined") return;
    setPosition({
      x: window.innerWidth - BUBBLE_SIZE - EDGE_MARGIN,
      y: window.innerHeight - BUBBLE_SIZE - EDGE_MARGIN,
    });
  }, [isMounted]);

  useEffect(() => {
    const handleResize = () => {
      setPosition((prev) => {
        if (typeof window === "undefined") return prev;
        return {
          x: clamp(prev.x, 0, window.innerWidth - BUBBLE_SIZE),
          y: clamp(prev.y, 0, window.innerHeight - BUBBLE_SIZE),
        };
      });
    };
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  useEffect(() => {
    return () => {
      cleanupRef.current?.();
    };
  }, []);

  useEffect(() => {
    if (isDragging) {
      setDockEdge(null);
    }
  }, [isDragging]);

  const checkAndSnapToEdge = useCallback((x: number, y: number) => {
    if (typeof window === "undefined") return;
    const vw = window.innerWidth;
    const vh = window.innerHeight;

    const distLeft = x;
    const distRight = vw - (x + BUBBLE_SIZE);
    const distTop = y;
    const distBottom = vh - (y + BUBBLE_SIZE);

    const minDist = Math.min(distLeft, distRight, distTop, distBottom);

    if (minDist > SNAP_THRESHOLD) {
      setDockEdge(null);
      setPosition({ x, y });
      return;
    }

    let edge: DockEdge = null;
    let nextX = x;
    let nextY = y;

    if (minDist === distLeft) {
      edge = "left";
      const dockWidth = BAR_SHORT;
      const dockHeight = BAR_LONG;
      nextX = 0;
      nextY = clamp(y, 0, vh - dockHeight);
      setPosition({ x: nextX, y: nextY });
      setDockEdge(edge);
      return;
    } else if (minDist === distRight) {
      edge = "right";
      const dockWidth = BAR_SHORT;
      const dockHeight = BAR_LONG;
      nextX = vw - dockWidth;
      nextY = clamp(y, 0, vh - dockHeight);
      setPosition({ x: nextX, y: nextY });
      setDockEdge(edge);
      return;
    } else if (minDist === distTop) {
      edge = "top";
      const dockWidth = BAR_LONG;
      const dockHeight = BAR_SHORT;
      nextY = 0;
      nextX = clamp(x, 0, vw - dockWidth);
      setPosition({ x: nextX, y: nextY });
      setDockEdge(edge);
      return;
    } else {
      edge = "bottom";
      const dockWidth = BAR_LONG;
      const dockHeight = BAR_SHORT;
      nextY = vh - dockHeight;
      nextX = clamp(x, 0, vw - dockWidth);
      setPosition({ x: nextX, y: nextY });
      setDockEdge(edge);
      return;
    }
  }, []);

  const handleDragPointerDown = useCallback(
    (event: React.PointerEvent<HTMLButtonElement>) => {
      if (event.button !== 0) return;
      const rect = buttonRef.current?.getBoundingClientRect();
      if (!rect) return;

      dragStateRef.current = {
        pointerId: event.pointerId,
        offsetX: event.clientX - rect.left,
        offsetY: event.clientY - rect.top,
      };
      didDragRef.current = false;
      setIsDragging(true);

      const handlePointerMove = (moveEvent: PointerEvent) => {
        if (moveEvent.pointerId !== dragStateRef.current.pointerId) return;
        didDragRef.current = true;

        if (rafRef.current != null) return;
        rafRef.current = window.requestAnimationFrame(() => {
          const vw = window.innerWidth;
          const vh = window.innerHeight;
          const nextX = clamp(
            moveEvent.clientX - dragStateRef.current.offsetX,
            0,
            vw - BUBBLE_SIZE
          );
          const nextY = clamp(
            moveEvent.clientY - dragStateRef.current.offsetY,
            0,
            vh - BUBBLE_SIZE
          );
          setPosition({ x: nextX, y: nextY });
          rafRef.current = null;
        });
      };

      const handlePointerUp = (upEvent: PointerEvent) => {
        if (upEvent.pointerId !== dragStateRef.current.pointerId) return;
        cleanupRef.current?.();
        cleanupRef.current = null;
        if (rafRef.current != null) {
          cancelAnimationFrame(rafRef.current);
          rafRef.current = null;
        }

        const vw = window.innerWidth;
        const vh = window.innerHeight;
        const releaseX = clamp(
          upEvent.clientX - dragStateRef.current.offsetX,
          0,
          vw - BUBBLE_SIZE
        );
        const releaseY = clamp(
          upEvent.clientY - dragStateRef.current.offsetY,
          0,
          vh - BUBBLE_SIZE
        );

        checkAndSnapToEdge(releaseX, releaseY);
        dragStateRef.current = { pointerId: null, offsetX: 0, offsetY: 0 };
        setTimeout(() => {
          didDragRef.current = false;
        }, 0);
        setIsDragging(false);
      };

      window.addEventListener("pointermove", handlePointerMove);
      window.addEventListener("pointerup", handlePointerUp);
      cleanupRef.current = () => {
        window.removeEventListener("pointermove", handlePointerMove);
        window.removeEventListener("pointerup", handlePointerUp);
      };
    },
    [checkAndSnapToEdge]
  );

  const toggleOpen = useCallback(() => {
    if (didDragRef.current) return;
    setIsOpen((prev) => !prev);
  }, []);

  const isVerticalDock = dockEdge === "left" || dockEdge === "right";
  const isHorizontalDock = dockEdge === "top" || dockEdge === "bottom";
  const isDocked = dockEdge !== null;

  const bubbleWidth = isDocked
    ? isVerticalDock
      ? BAR_SHORT
      : BAR_LONG
    : BUBBLE_SIZE;
  const bubbleHeight = isDocked
    ? isVerticalDock
      ? BAR_LONG
      : BAR_SHORT
    : BUBBLE_SIZE;

  const getPanelPosition = () => {
    if (typeof window === "undefined") return {};
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    let panelX = position.x;
    let panelY = position.y - PANEL_HEIGHT - 12;

    if (panelX + PANEL_WIDTH > vw) {
      panelX = vw - PANEL_WIDTH - EDGE_MARGIN;
    }
    if (panelX < EDGE_MARGIN) {
      panelX = EDGE_MARGIN;
    }
    if (panelY < EDGE_MARGIN) {
      panelY = position.y + bubbleHeight + 12;
    }
    if (panelY + PANEL_HEIGHT > vh) {
      panelY = vh - PANEL_HEIGHT - EDGE_MARGIN;
    }

    return { left: panelX, top: panelY };
  };

  return (
    <>
      {/* 聊天面板 */}
      {isOpen && (
        <div
          className="fixed z-50 flex h-[500px] w-[380px] flex-col overflow-hidden rounded-2xl border border-zinc-200 bg-white shadow-2xl transition-all dark:border-zinc-700 dark:bg-zinc-900"
          style={getPanelPosition()}
        >
          {/* 头部 */}
          <div className="flex h-12 shrink-0 items-center justify-between border-b border-zinc-200 bg-zinc-50 px-4 dark:border-zinc-700 dark:bg-zinc-800">
            <div className="flex items-center gap-2">
              <div className="flex h-7 w-7 items-center justify-center rounded-full bg-orange-500/10">
                <span className="text-sm">🛒</span>
              </div>
              <span className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                商品推荐助手
              </span>
            </div>
            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                onClick={handleClearChat}
                title="清空对话"
                disabled={isUserLoading}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                onClick={toggleOpen}
                title="收起"
              >
                <Minus className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {/* 聊天内容 */}
          <EmbedChatContent
            timeline={timeline}
            isStreaming={isStreaming}
            isLoading={isUserLoading}
            error={error}
            onSendMessage={handleSendMessage}
            onAbortStream={abortStream}
          />
        </div>
      )}

      {/* 悬浮气泡 */}
      {isMounted && (
        <Button
          ref={buttonRef}
          onClick={toggleOpen}
          onPointerDown={handleDragPointerDown}
          className={cn(
            "fixed z-50 shadow-lg transition-all",
            "flex items-center justify-center",
            isDocked ? "rounded-lg" : "rounded-full",
            isOpen
              ? "bg-zinc-600 hover:bg-zinc-700 text-white"
              : "bg-orange-500 hover:bg-orange-600 text-white"
          )}
          style={{
            left: position.x,
            top: position.y,
            width: bubbleWidth,
            height: bubbleHeight,
            cursor: isDragging ? "grabbing" : "grab",
            transform: isDragging ? "scale(1.05)" : "scale(1)",
            transition: isDragging
              ? "none"
              : "left 120ms ease, top 120ms ease, transform 120ms ease, width 120ms ease, height 120ms ease",
          }}
        >
          {isOpen ? (
            <X className="h-5 w-5" />
          ) : (
            <MessageCircle className="h-5 w-5" />
          )}
        </Button>
      )}
    </>
  );
}
