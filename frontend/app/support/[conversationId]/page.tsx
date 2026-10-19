"use client";

/**
 * 客服会话工作台页面
 *
 * 这个页面承载人工客服处理单个用户会话的完整操作流，包括接入会话、查看客诉上下文、
 * 切换历史问题单，以及直接在人工介入过程中完成解决或重开。
 */

import { useCallback, useEffect, useState, useRef } from "react";
import Image from "next/image";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  PhoneOff,
  Circle,
  PanelRight,
  Headphones,
  UserRound,
  Check,
  Plus,
  ImagePlus,
  X,
  Trash2,
  Pencil,
  MoreHorizontal,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useSupportWebSocket } from "@/hooks/use-websocket";
import { useSupportWorkbenchStore } from "@/stores/support-workbench-store";
import { useSupportStore } from "@/stores";
import {
  getConversationDetail,
  getSupportStats,
  getConversationState,
  getConversationTickets,
  getSupportTicketDetail,
  reopenSupportTicket,
  resolveSupportTicket,
  startHandoff,
  endHandoff,
  type ConversationDetailResponse,
  type TicketDetail,
  type TicketSummary,
} from "@/lib/api/support";
import { FAQFormSheet } from "@/components/admin/faq/faq-form-sheet";
import {
  createFAQEntry,
  getAgent,
  type Agent,
  type FAQEntry,
} from "@/lib/api/agents";
import type {
  SupportMessage,
  ConversationState,
  MessageWithdrawnPayload,
  MessageEditedPayload,
  MessagesDeletedPayload,
  ReadReceiptPayload,
} from "@/types/websocket";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import type { ImageAttachment } from "@/types/chat";
import { uploadImage } from "@/lib/api/upload";
import { Markdown } from "@/components/prompt-kit/markdown";
import { ChatRichInput } from "@/components/features/chat/ChatRichInput";
import { ComplaintActivityFeed } from "@/app/support/components/complaint-activity-feed";
import { SupportDetails } from "@/app/support/components/support-details";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
  SheetTrigger,
} from "@/components/ui/sheet";
import { ComplaintWorkbenchPanel } from "@/app/support/components/complaint-workbench-panel";
import { ComplaintTicketHistoryPanel } from "@/app/support/components/complaint-ticket-history-panel";
import { ComplaintLiveEventStream } from "@/app/support/components/complaint-live-event-stream";

/** Keyed route content prevents pending uploads and drafts from crossing customer boundaries. */
export default function SupportChatPage() {
  const params = useParams();
  return <SupportChatContent key={String(params.conversationId)} />;
}

/** Keeps the original handoff, WebSocket, ticket, image and FAQ workflows in the redesigned shell. */
function SupportChatContent() {
  const params = useParams();
  const router = useRouter();
  const conversationId = params.conversationId as string;

  // 简单的 agentId（实际应从认证获取）
  // 注意：这里不要添加 agent_ 前缀，WebSocketManager 会自动添加
  const [agentId] = useState(() => {
    if (typeof window !== "undefined") {
      let id = localStorage.getItem("support_agent_id");
      if (!id) {
        id = Math.random().toString(36).slice(2, 10);
        localStorage.setItem("support_agent_id", id);
      }
      // 如果旧数据有 agent_ 前缀，去掉它
      if (id.startsWith("agent_")) {
        id = id.slice(6);
        localStorage.setItem("support_agent_id", id);
      }
      return id;
    }
    return "default";
  });

  const [conversation, setConversation] =
    useState<ConversationDetailResponse | null>(null);

  // 使用 SupportStore 管理消息和状态
  const messages = useSupportStore((s) => s.messages);
  const setMessages = useSupportStore((s) => s.setMessages);
  const addMessage = useSupportStore((s) => s.addMessage);
  const storeWithdrawMessage = useSupportStore((s) => s.withdrawMessage);
  const storeEditMessage = useSupportStore((s) => s.editMessage);
  const storeDeleteMessages = useSupportStore((s) => s.deleteMessages);
  const updateMessage = useSupportStore((s) => s.updateMessage);
  const updateConversationState = useSupportStore(
    (s) => s.updateConversationState,
  );
  const setHandoffState = useSupportStore((s) => s.setHandoffState);
  const storeHandoffState = useSupportStore((s) => s.handoffState);
  const currentTicket = useSupportStore((s) => s.currentTicket);
  const reviewSummary = useSupportStore((s) => s.reviewSummary);
  const recentTasks = useSupportStore((s) => s.recentTasks);
  const secondaryIssues = useSupportStore((s) => s.secondaryIssues);
  const handoffSummary = useSupportStore((s) => s.handoffSummary);
  const handoffReason = useSupportStore((s) => s.handoffReason);
  const setStoreConversationId = useSupportStore((s) => s.setConversationId);
  const unreadCount = useSupportStore((s) => s.unreadCount);
  const setUnreadCount = useSupportStore((s) => s.setUnreadCount);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const ticketSnapshotRef = useRef<string | null>(null);
  const supportDetailSnapshotRef = useRef<string | null>(null);
  const autoReadMessageIdsRef = useRef<Set<string>>(new Set());

  // 图片上传相关状态
  const [pendingImages, setPendingImages] = useState<ImageAttachment[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [ticketActionLoading, setTicketActionLoading] = useState<
    "resolve" | "reopen" | null
  >(null);
  const [conversationTickets, setConversationTickets] = useState<
    TicketSummary[]
  >([]);
  const [selectedTicketId, setSelectedTicketId] = useState<string | null>(null);
  const [selectedTicketDetail, setSelectedTicketDetail] =
    useState<TicketDetail | null>(null);
  const [isTicketHistoryLoading, setIsTicketHistoryLoading] = useState(false);

  // FAQ 相关状态
  const [faqAgent, setFaqAgent] = useState<Agent | null>(null);
  const [faqSheetOpen, setFaqSheetOpen] = useState(false);
  const [selectedQuestion, setSelectedQuestion] = useState("");
  const [selectedAnswer, setSelectedAnswer] = useState("");
  const [selectedSource, setSelectedSource] = useState("");

  // 撤回/编辑相关状态
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editingMessage, setEditingMessage] = useState<SupportMessage | null>(
    null,
  );
  const [editContent, setEditContent] = useState("");
  const [editRegenerate, setEditRegenerate] = useState(true);
  const [withdrawDialogOpen, setWithdrawDialogOpen] = useState(false);
  const [withdrawingMessage, setWithdrawingMessage] =
    useState<SupportMessage | null>(null);

  // 初始化 Store 的 conversationId
  useEffect(() => {
    setStoreConversationId(conversationId);
    autoReadMessageIdsRef.current.clear();
  }, [conversationId, setStoreConversationId]);

  // WebSocket 消息回调 - 使用 SupportStore
  const handleNewMessage = useCallback(
    (message: SupportMessage) => {
      addMessage(message);
    },
    [addMessage],
  );

  // WebSocket 状态变更回调 - 使用 SupportStore
  const handleStateChange = useCallback(
    (state: ConversationState) => {
      updateConversationState(state);
    },
    [updateConversationState],
  );

  // 消息撤回回调 - 使用 SupportStore
  const handleMessageWithdrawn = useCallback(
    (payload: MessageWithdrawnPayload) => {
      storeWithdrawMessage(
        payload.message_id,
        payload.withdrawn_at,
        payload.withdrawn_by,
      );
    },
    [storeWithdrawMessage],
  );

  // 消息编辑回调 - 使用 SupportStore
  const handleMessageEdited = useCallback(
    (payload: MessageEditedPayload) => {
      storeEditMessage(
        payload.message_id,
        payload.new_content,
        payload.edited_at,
        payload.edited_by,
      );
    },
    [storeEditMessage],
  );

  // 消息删除回调 - 使用 SupportStore
  const handleMessagesDeleted = useCallback(
    (payload: MessagesDeletedPayload) => {
      storeDeleteMessages(payload.message_ids);
    },
    [storeDeleteMessages],
  );

  /**
   * 处理用户侧已读回执。
   *
   * 这个方法服务于人工客服查看自己发送消息是否已被用户阅读，避免客服只能看到“已发送”
   * 而不知道用户是否真正看到。
   */
  const handleReadReceipt = useCallback(
    (payload: ReadReceiptPayload) => {
      payload.message_ids.forEach((messageId) => {
        updateMessage(messageId, {
          read_at: payload.read_at,
          read_by: payload.read_by,
        });
      });
    },
    [updateMessage],
  );

  // WebSocket 连接
  const {
    isConnected,
    conversationState,
    userTyping,
    sendMessage,
    markAsRead,
    withdrawMessage,
    editMessage,
  } = useSupportWebSocket({
    conversationId,
    agentId,
    onMessage: handleNewMessage,
    onStateChange: handleStateChange,
    onReadReceipt: handleReadReceipt,
    onMessageWithdrawn: handleMessageWithdrawn,
    onMessageEdited: handleMessageEdited,
    onMessagesDeleted: handleMessagesDeleted,
  });

  // 有效的 handoff 状态（使用 Store 状态）
  const effectiveHandoffState = storeHandoffState;
  const handoffModeLabel =
    effectiveHandoffState === "human"
      ? "人工模式"
      : effectiveHandoffState === "pending"
        ? "待接入"
        : "AI 模式";

  /**
   * 把后端客服状态写入前端工作台。
   *
   * 这个方法服务于页面初次加载、人工操作回写以及 WebSocket 状态广播，确保人工工作台与后端主状态保持一致。
   */
  const applySupportState = useCallback(
    (supportState: Awaited<ReturnType<typeof getConversationState>>) => {
      if (supportState.handoff_state) {
        setHandoffState(
          supportState.handoff_state as "ai" | "pending" | "human",
          supportState.handoff_operator ?? null,
        );
      }
      updateConversationState({
        conversation_mode:
          supportState.conversation_mode as ConversationState["conversation_mode"],
        handoff_state: supportState.handoff_state as "ai" | "pending" | "human",
        operator: supportState.handoff_operator ?? undefined,
        handoff_reason: supportState.handoff_reason ?? null,
        user_online: supportState.user_online,
        agent_online: true,
        peer_last_online_at: supportState.peer_last_online_at ?? undefined,
        unread_count: supportState.unread_count,
        current_ticket: supportState.current_ticket ?? null,
        review_summary: supportState.review_summary ?? null,
        recent_tasks: supportState.recent_tasks ?? [],
        secondary_issues: supportState.secondary_issues ?? [],
        handoff_summary: supportState.handoff_summary ?? null,
      });
    },
    [setHandoffState, updateConversationState],
  );

  /**
   * 加载当前选中的问题单详情。
   *
   * 这个方法服务于客服查看某张历史 ticket 的完整处理轨迹，不局限于当前主问题单。
   */
  const loadSelectedTicketDetail = useCallback(
    async (ticketId: string | null) => {
      if (!ticketId) {
        setSelectedTicketDetail(null);
        return;
      }

      const detail = await getSupportTicketDetail(ticketId);
      setSelectedTicketDetail(detail);
    },
    [],
  );

  /**
   * 刷新会话的问题单历史面板。
   *
   * 这个方法服务于初次加载、客服手动解决、重新打开问题单等场景，确保历史列表和详情面板始终与后端状态一致。
   */
  const refreshConversationTickets = useCallback(
    async (options?: {
      preferredTicketId?: string | null;
      supportState?: Awaited<ReturnType<typeof getConversationState>> | null;
    }) => {
      setIsTicketHistoryLoading(true);

      try {
        const response = await getConversationTickets(conversationId);
        const tickets = response.items ?? [];
        setConversationTickets(tickets);

        const preferredTicketId = options?.preferredTicketId ?? null;
        const activeTicketId =
          options?.supportState?.current_ticket?.id ??
          currentTicket?.id ??
          null;
        const currentSelectedTicketId =
          selectedTicketId &&
          tickets.some((ticket) => ticket.id === selectedTicketId)
            ? selectedTicketId
            : null;
        const nextSelectedTicketId =
          (preferredTicketId &&
          tickets.some((ticket) => ticket.id === preferredTicketId)
            ? preferredTicketId
            : null) ??
          (activeTicketId &&
          tickets.some((ticket) => ticket.id === activeTicketId)
            ? activeTicketId
            : null) ??
          currentSelectedTicketId ??
          tickets[0]?.id ??
          null;

        setSelectedTicketId(nextSelectedTicketId);
        setSelectedTicketDetail(null);

        if (!nextSelectedTicketId) {
          return;
        }

        await loadSelectedTicketDetail(nextSelectedTicketId);
      } catch (e) {
        setError(e instanceof Error ? e.message : "问题单历史加载失败");
      } finally {
        setIsTicketHistoryLoading(false);
      }
    },
    [
      conversationId,
      currentTicket?.id,
      loadSelectedTicketDetail,
      selectedTicketId,
    ],
  );

  /**
   * 切换客服当前查看的问题单。
   *
   * 这个方法服务于人工沿着同一会话追查历史 ticket，判断是持续追单、返工还是已解决旧单。
   */
  const handleSelectTicket = useCallback(
    async (ticketId: string) => {
      if (!ticketId || ticketId === selectedTicketId) {
        return;
      }

      try {
        setIsTicketHistoryLoading(true);
        setSelectedTicketId(ticketId);
        setSelectedTicketDetail(null);
        await loadSelectedTicketDetail(ticketId);
      } catch (e) {
        setError(e instanceof Error ? e.message : "问题单详情加载失败");
      } finally {
        setIsTicketHistoryLoading(false);
      }
    },
    [loadSelectedTicketDetail, selectedTicketId],
  );

  /**
   * 根据当前主问题单快照同步历史面板。
   *
   * 这个副作用服务于 AI 在页面打开期间继续推进 ticket 的场景，确保人工看到的问题单列表、当前状态和详情不会停留在旧快照。
   */
  useEffect(() => {
    if (isLoading) {
      return;
    }

    const snapshotKey = `${currentTicket?.id ?? "none"}:${currentTicket?.status ?? "none"}`;
    if (ticketSnapshotRef.current === snapshotKey) {
      return;
    }

    ticketSnapshotRef.current = snapshotKey;
    void refreshConversationTickets({
      preferredTicketId: selectedTicketId ?? currentTicket?.id ?? null,
    });
  }, [
    currentTicket?.id,
    currentTicket?.status,
    isLoading,
    refreshConversationTickets,
    selectedTicketId,
  ]);

  /**
   * 根据最新的 ticket、review 和任务快照刷新选中问题单详情。
   *
   * 这个副作用服务于 WebSocket 实时推进场景，确保客服正在查看的工单详情
   * 不会因为只收到了 ticket/review 快照而停留在旧数据。
   */
  useEffect(() => {
    if (isLoading || !selectedTicketId) {
      return;
    }

    const detailSnapshotKey = JSON.stringify({
      selectedTicketId,
      currentTicketId: currentTicket?.id ?? null,
      currentTicketStatus: currentTicket?.status ?? null,
      currentTicketUpdatedAt: currentTicket?.updated_at ?? null,
      reviewStatus: reviewSummary?.status ?? null,
      reviewCreatedAt: reviewSummary?.created_at ?? null,
      taskHead: recentTasks
        .slice(0, 3)
        .map(
          (task) => `${task.id}:${task.status}:${task.review_status ?? "none"}`,
        ),
      handoffReason: handoffReason ?? null,
    });

    if (supportDetailSnapshotRef.current === detailSnapshotKey) {
      return;
    }

    supportDetailSnapshotRef.current = detailSnapshotKey;
    void refreshConversationTickets({
      preferredTicketId: selectedTicketId,
    });
  }, [
    currentTicket?.id,
    currentTicket?.status,
    currentTicket?.updated_at,
    handoffReason,
    isLoading,
    recentTasks,
    refreshConversationTickets,
    reviewSummary?.created_at,
    reviewSummary?.status,
    selectedTicketId,
  ]);

  // Keep a stable initial loader: selecting historical tickets must not reload the message history.
  const refreshTicketsRef = useRef(refreshConversationTickets);
  useEffect(() => {
    refreshTicketsRef.current = refreshConversationTickets;
  }, [refreshConversationTickets]);

  // 加载会话详情和历史消息；忽略已切走会话的迟到响应，避免覆盖新客户消息。
  useEffect(() => {
    let cancelled = false;
    async function loadConversation() {
      try {
        setIsLoading(true);
        const [data, supportState] = await Promise.all([
          getConversationDetail(conversationId),
          getConversationState(conversationId),
        ]);
        if (cancelled) return;
        setConversation(data);
        applySupportState(supportState);
        ticketSnapshotRef.current = `${supportState.current_ticket?.id ?? "none"}:${supportState.current_ticket?.status ?? "none"}`;
        await refreshTicketsRef.current({ supportState });
        if (cancelled) return;

        // 转换历史消息格式（包含图片信息）
        autoReadMessageIdsRef.current.clear();
        const historyMessages: SupportMessage[] = data.messages.map((m) => ({
          id: m.id,
          role: m.role as SupportMessage["role"],
          content: m.content,
          created_at: m.created_at,
          operator: m.extra_metadata?.operator,
          images: m.extra_metadata?.images,
          is_delivered: m.is_delivered,
          delivered_at: m.delivered_at ?? undefined,
          read_at: m.read_at ?? undefined,
          read_by: m.read_by ?? undefined,
          is_withdrawn: m.is_withdrawn,
          withdrawn_at: m.withdrawn_at ?? undefined,
          withdrawn_by: m.withdrawn_by ?? undefined,
          is_edited: m.is_edited,
          edited_at: m.edited_at ?? undefined,
          edited_by: m.edited_by ?? undefined,
        }));
        if (cancelled) return;
        setMessages(historyMessages);

        // 加载 Agent 信息，检查是否为 FAQ 类型
        if (data.agent_id) {
          try {
            const agentData = await getAgent(data.agent_id);
            if (agentData.type === "faq") {
              setFaqAgent(agentData);
            }
          } catch {
            // Agent 加载失败不影响主流程
          }
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "加载失败");
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    if (conversationId) {
      void loadConversation();
    }
    return () => {
      cancelled = true;
    };
  }, [applySupportState, conversationId, setMessages]);

  // The active socket belongs to this pane, so propagate its authoritative snapshots to the persistent queue.
  useEffect(() => {
    if (isLoading || !conversation) return;
    const workbench = useSupportWorkbenchStore.getState();
    const latest = messages.at(-1);
    workbench.patchConversation(conversationId, {
      handoff_state: effectiveHandoffState,
      unread_count: unreadCount,
      user_online: conversationState.user_online,
      ticket_status: currentTicket?.status,
      current_ticket_id: currentTicket?.id,
      risk_level: currentTicket?.risk_level,
      review_status: reviewSummary?.status,
      review_score: reviewSummary?.score,
      ...(latest
        ? {
            lastMessage: latest.content.slice(0, 100),
            updated_at: latest.created_at,
          }
        : {}),
    });
    let cancelled = false;
    void getSupportStats()
      .then((value) => {
        if (!cancelled) workbench.setStats(value);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [
    isLoading,
    conversation,
    conversationId,
    effectiveHandoffState,
    unreadCount,
    conversationState.user_online,
    currentTicket,
    reviewSummary,
    messages,
  ]);

  // FAQ 相关操作
  const handleAddToFAQ = useCallback(
    (userContent: string, assistantContent: string) => {
      setSelectedQuestion(userContent);
      setSelectedAnswer(assistantContent);
      setSelectedSource(`chat:${conversationId}`);
      setFaqSheetOpen(true);
    },
    [conversationId],
  );

  const handleSaveFAQ = useCallback(
    async (data: Partial<FAQEntry>) => {
      if (!faqAgent) return {};
      const result = await createFAQEntry({
        ...data,
        agent_id: faqAgent.id,
      });
      return { merged: result.merged, target_id: result.target_id };
    },
    [faqAgent],
  );

  // 滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
        ? "auto"
        : "smooth",
      block: "nearest",
    });
  }, [messages]);

  /**
   * 人工接管后自动把当前会话里的未读用户消息标记为已读。
   *
   * 这个副作用服务于客服真实处理场景。只有在会话已经进入人工模式时才自动清未读，
   * 避免客服只是点开排队会话预览就提前把待接入消息清掉。
   */
  useEffect(() => {
    if (!isConnected || effectiveHandoffState !== "human" || !agentId) {
      return;
    }

    const unreadUserMessages = messages.filter(
      (message) =>
        message.role === "user" &&
        !message.read_at &&
        !autoReadMessageIdsRef.current.has(message.id),
    );

    if (unreadUserMessages.length === 0) {
      return;
    }

    const unreadMessageIds = unreadUserMessages.map((message) => message.id);
    unreadMessageIds.forEach((messageId) => {
      autoReadMessageIdsRef.current.add(messageId);
    });

    const readAt = new Date().toISOString();
    unreadMessageIds.forEach((messageId) => {
      updateMessage(messageId, {
        read_at: readAt,
        read_by: agentId,
      });
    });

    setUnreadCount(
      messages.filter(
        (message) =>
          message.role === "user" &&
          !message.read_at &&
          !unreadMessageIds.includes(message.id),
      ).length,
    );

    markAsRead(unreadMessageIds);
  }, [
    agentId,
    effectiveHandoffState,
    isConnected,
    markAsRead,
    messages,
    setUnreadCount,
    updateMessage,
  ]);

  // 处理图片选择
  const handleImageSelect = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      if (!files || files.length === 0) return;

      setIsUploading(true);
      setError(null);

      try {
        for (const file of Array.from(files)) {
          // 验证文件类型
          if (!file.type.startsWith("image/")) {
            setError(`文件 ${file.name} 不是图片`);
            continue;
          }
          // 验证文件大小 (10MB)
          if (file.size > 10 * 1024 * 1024) {
            setError(`图片 ${file.name} 超过 10MB 限制`);
            continue;
          }

          const result = await uploadImage(file, agentId);
          const imageAttachment: ImageAttachment = {
            id: result.id,
            url: result.url,
            thumbnail_url: result.thumbnail_url,
            filename: result.filename,
            size: result.size,
            width: result.width,
            height: result.height,
            mime_type: result.mime_type,
          };
          setPendingImages((prev) => [...prev, imageAttachment]);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "图片上传失败");
      } finally {
        setIsUploading(false);
        // 清空 input
        if (fileInputRef.current) {
          fileInputRef.current.value = "";
        }
      }
    },
    [agentId],
  );

  // 移除待发送图片
  const removePendingImage = useCallback((imageId: string) => {
    setPendingImages((prev) => prev.filter((img) => img.id !== imageId));
  }, []);

  // 发送消息（支持图片）
  const handleSend = useCallback(() => {
    const hasContent = inputValue.trim().length > 0;
    const hasImages = pendingImages.length > 0;

    if (!hasContent && !hasImages) {
      setError("请输入回复内容或添加图片。");
      return;
    }
    if (!isConnected) {
      setError("连接已断开，请等待重新连接后发送。");
      return;
    }

    if (effectiveHandoffState !== "human") {
      setError("接入会话后，开始与客户沟通…");
      return;
    }

    const optimisticMessageId = sendMessage(
      inputValue.trim(),
      hasImages ? pendingImages : undefined,
    );

    // 本地立即显示（乐观更新）
    const localMessage: SupportMessage = {
      id: optimisticMessageId,
      role: "human_agent",
      content: inputValue.trim(),
      created_at: new Date().toISOString(),
      operator: agentId,
      is_delivered: false,
      images: hasImages
        ? pendingImages.map((img) => ({
            id: img.id,
            url: img.url,
            thumbnail_url: img.thumbnail_url || undefined,
            filename: img.filename || undefined,
          }))
        : undefined,
    };
    addMessage(localMessage);
    setInputValue("");
    setPendingImages([]);
  }, [
    addMessage,
    inputValue,
    pendingImages,
    effectiveHandoffState,
    sendMessage,
    agentId,
    isConnected,
  ]);

  const [handoffLoading, setHandoffLoading] = useState(false);

  // 开始介入
  const handleStartHandoff = useCallback(async () => {
    if (handoffLoading) return;
    setHandoffLoading(true);
    try {
      const startReason =
        effectiveHandoffState === "pending" ? "" : "客服主动接入";
      const result = await startHandoff(conversationId, agentId, startReason);
      if (result.success) {
        // 使用 API 返回的最新状态（保底机制），等待服务器广播
        setHandoffState(result.handoff_state || "human", agentId);
      } else if (result.error) {
        setError(result.error);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "接入失败");
    } finally {
      setHandoffLoading(false);
    }
  }, [
    conversationId,
    agentId,
    effectiveHandoffState,
    setHandoffState,
    handoffLoading,
  ]);

  // 结束介入
  const handleEndHandoff = useCallback(async () => {
    if (handoffLoading) return;
    setHandoffLoading(true);
    try {
      const result = await endHandoff(conversationId, agentId, "客服结束服务");
      if (result.success) {
        // 使用 API 返回的最新状态（保底机制），等待服务器广播
        setHandoffState(result.handoff_state || "ai", null);
      } else if (result.error) {
        setError(result.error);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "结束失败");
    } finally {
      setHandoffLoading(false);
    }
  }, [conversationId, agentId, setHandoffState, handoffLoading]);

  /**
   * 按工单 ID 执行手动解决。
   *
   * 这个方法服务于当前主问题单和历史问题单的统一处理入口，避免客服只能操作当前活动单。
   */
  const handleResolveTicketById = useCallback(
    async (ticketId: string) => {
      if (!ticketId) return;

      try {
        setTicketActionLoading("resolve");
        const operatedTicketId = ticketId;
        const result = await resolveSupportTicket(
          operatedTicketId,
          agentId,
          "客服人工确认当前问题已解决",
        );
        if (!result.success) {
          setError(result.error || "问题单解决失败");
          return;
        }

        const supportState = await getConversationState(conversationId);
        applySupportState(supportState);
        ticketSnapshotRef.current = `${supportState.current_ticket?.id ?? "none"}:${supportState.current_ticket?.status ?? "none"}`;
        await refreshConversationTickets({
          preferredTicketId: operatedTicketId,
          supportState,
        });
      } catch (e) {
        setError(e instanceof Error ? e.message : "问题单解决失败");
      } finally {
        setTicketActionLoading(null);
      }
    },
    [agentId, applySupportState, conversationId, refreshConversationTickets],
  );

  /**
   * 按工单 ID 执行手动重开。
   *
   * 这个方法服务于人工复核历史已解决工单后重新交回 AI 主链路继续处理。
   */
  const handleReopenTicketById = useCallback(
    async (ticketId: string) => {
      if (!ticketId) return;

      try {
        setTicketActionLoading("reopen");
        const operatedTicketId = ticketId;
        const result = await reopenSupportTicket(
          operatedTicketId,
          agentId,
          "客服确认问题仍未解决，重新交回 AI 主链路",
        );
        if (!result.success) {
          setError(result.error || "问题单重开失败");
          return;
        }

        const supportState = await getConversationState(conversationId);
        applySupportState(supportState);
        ticketSnapshotRef.current = `${supportState.current_ticket?.id ?? "none"}:${supportState.current_ticket?.status ?? "none"}`;
        await refreshConversationTickets({
          preferredTicketId: operatedTicketId,
          supportState,
        });
      } catch (e) {
        setError(e instanceof Error ? e.message : "问题单重开失败");
      } finally {
        setTicketActionLoading(null);
      }
    },
    [agentId, applySupportState, conversationId, refreshConversationTickets],
  );

  /**
   * 解决当前主问题单。
   *
   * 这个方法服务于顶部工作台的快捷操作按钮，默认针对当前主 ticket 执行。
   */
  const handleResolveTicket = useCallback(() => {
    if (!currentTicket) {
      return;
    }
    void handleResolveTicketById(currentTicket.id);
  }, [currentTicket, handleResolveTicketById]);

  /**
   * 重开当前主问题单。
   *
   * 这个方法服务于顶部工作台的快捷操作按钮，默认针对当前主 ticket 执行。
   */
  const handleReopenTicket = useCallback(() => {
    if (!currentTicket) {
      return;
    }
    void handleReopenTicketById(currentTicket.id);
  }, [currentTicket, handleReopenTicketById]);

  // 检查消息是否在可操作时间范围内（5分钟）
  const isWithinTimeLimit = (createdAt: string) => {
    const created = new Date(createdAt);
    const now = new Date();
    const diffMs = now.getTime() - created.getTime();
    return diffMs <= 5 * 60 * 1000; // 5 分钟
  };

  // 打开编辑弹窗
  const openEditDialog = (message: SupportMessage) => {
    setEditingMessage(message);
    setEditContent(message.content);
    setEditRegenerate(message.role === "user");
    setEditDialogOpen(true);
  };

  // 确认编辑
  const confirmEdit = () => {
    if (editingMessage && editContent.trim()) {
      editMessage(editingMessage.id, editContent.trim(), editRegenerate);
      setEditDialogOpen(false);
      setEditingMessage(null);
      setEditContent("");
    }
  };

  // 打开撤回确认弹窗
  const openWithdrawDialog = (message: SupportMessage) => {
    setWithdrawingMessage(message);
    setWithdrawDialogOpen(true);
  };

  // 确认撤回
  const confirmWithdraw = () => {
    if (withdrawingMessage) {
      withdrawMessage(withdrawingMessage.id);
      setWithdrawDialogOpen(false);
      setWithdrawingMessage(null);
    }
  };

  // 渲染消息
  const renderMessage = (message: SupportMessage, index: number) => {
    const isUser = message.role === "user";
    const isAgent = message.role === "human_agent";
    const isAI = message.role === "assistant";
    const isSystem = message.role === "system";
    const isWithdrawn = message.is_withdrawn;
    const isEdited = message.is_edited;
    const canOperate = isWithinTimeLimit(message.created_at) && !isWithdrawn;

    // 检查是否可以添加到 FAQ（用户消息后紧跟 AI 回复）
    const nextMsg = messages[index + 1];
    const canAddToFAQ =
      faqAgent && isUser && nextMsg?.role === "assistant" && !isWithdrawn;

    // 系统消息居中显示
    if (isSystem) {
      return (
        <div key={message.id} className="flex justify-center my-4">
          <div className="px-4 py-1.5 text-xs text-zinc-500 bg-zinc-100 dark:bg-zinc-800 rounded-full">
            {message.content}
          </div>
        </div>
      );
    }

    // 已撤回消息
    if (isWithdrawn) {
      return (
        <div
          key={message.id}
          className={cn(
            "flex w-full mb-3",
            isUser ? "justify-start" : "justify-end",
          )}
        >
          <div className="max-w-[75%] rounded-3xl px-5 py-2.5 bg-zinc-200 dark:bg-zinc-700 text-zinc-500 dark:text-zinc-400 italic text-sm">
            [此消息已被客服撤回]
          </div>
        </div>
      );
    }

    return (
      <div
        key={message.id}
        className={cn(
          "group flex w-full mb-6",
          isUser ? "justify-start" : "justify-end",
        )}
      >
        <div className="flex min-w-0 items-end gap-2 max-w-[94%] md:max-w-[88%]">
          {/* 操作菜单 - 左侧（用户消息时） */}
          {isUser && canOperate && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button
                  aria-label="消息操作"
                  className="mb-1 rounded p-1 text-muted-foreground opacity-100 transition-opacity hover:bg-accent md:opacity-0 md:group-hover:opacity-100 md:focus-visible:opacity-100 data-[state=open]:opacity-100"
                >
                  <MoreHorizontal className="h-4 w-4 text-zinc-400" />
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent
                align="end"
                className="support-theme dark w-32"
              >
                <DropdownMenuItem onClick={() => openEditDialog(message)}>
                  <Pencil className="h-4 w-4 mr-2" />
                  编辑
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() => openWithdrawDialog(message)}
                  className="text-red-600 focus:text-red-600"
                >
                  <Trash2 className="h-4 w-4 mr-2" />
                  撤回
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          )}

          {/* 消息气泡 */}
          <div
            className={cn(
              "min-w-0 rounded-[20px] border border-border px-4 py-3 text-foreground md:px-5",
              isUser && "bg-card",
              isAI && "bg-secondary",
              isAgent && "bg-accent",
            )}
          >
            {/* 图片展示 */}
            {message.images && message.images.length > 0 && (
              <div className="flex flex-wrap gap-2 mb-2">
                {message.images.map((img) => (
                  <a
                    key={img.id}
                    href={img.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block"
                  >
                    <Image
                      src={img.thumbnail_url || img.url}
                      alt={img.filename || "图片"}
                      width={200}
                      height={150}
                      unoptimized
                      className="max-w-[200px] max-h-[150px] rounded-lg object-cover"
                    />
                  </a>
                ))}
              </div>
            )}
            {/* 消息内容 */}
            {message.content && (
              <div
                className={cn(
                  "support-message-content prose prose-sm prose-invert max-w-none",
                )}
              >
                <Markdown>{message.content}</Markdown>
              </div>
            )}
            {/* 时间和标签 */}
            <div
              className={cn(
                "mt-2 flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground",
              )}
            >
              <span>
                {new Date(message.created_at).toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </span>
              {isEdited && <span>· 已编辑</span>}
              {isAI && <span>· AI 客服助手</span>}
              {isAgent && <span>· 人工客服</span>}
              {!isUser && message.read_at && <span>· 已读</span>}
              {!isUser && !message.read_at && message.is_delivered && (
                <span>· 已送达</span>
              )}
              {!isUser && message.is_delivered === false && (
                <span>· 待送达</span>
              )}
              {canAddToFAQ && (
                <button
                  onClick={() =>
                    handleAddToFAQ(message.content, nextMsg.content)
                  }
                  className="flex items-center gap-1 px-1.5 py-0.5 rounded bg-white/20 hover:bg-white/30 transition-colors"
                >
                  <Plus className="h-2.5 w-2.5" />
                  FAQ
                </button>
              )}
            </div>
          </div>

          {/* 操作菜单 - 右侧（AI/客服消息时） */}
          {!isUser && canOperate && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button
                  aria-label="消息操作"
                  className="mb-1 rounded p-1 text-muted-foreground opacity-100 transition-opacity hover:bg-accent md:opacity-0 md:group-hover:opacity-100 md:focus-visible:opacity-100 data-[state=open]:opacity-100"
                >
                  <MoreHorizontal className="h-4 w-4 text-zinc-400" />
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent
                align="start"
                className="support-theme dark w-32"
              >
                {isAgent && (
                  <DropdownMenuItem onClick={() => openEditDialog(message)}>
                    <Pencil className="h-4 w-4 mr-2" />
                    编辑
                  </DropdownMenuItem>
                )}
                <DropdownMenuItem
                  onClick={() => openWithdrawDialog(message)}
                  className="text-red-600 focus:text-red-600"
                >
                  <Trash2 className="h-4 w-4 mr-2" />
                  撤回
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          )}
        </div>
      </div>
    );
  };

  const inspector = (
    <SupportDetails
      overview={
        <ComplaintWorkbenchPanel
          currentTicket={currentTicket}
          reviewSummary={reviewSummary}
          handoffReason={handoffReason}
          recentTasks={recentTasks}
          secondaryIssues={secondaryIssues}
          handoffSummary={handoffSummary}
          ticketActionLoading={ticketActionLoading}
          onResolveTicket={handleResolveTicket}
          onReopenTicket={handleReopenTicket}
        />
      }
      history={
        <ComplaintTicketHistoryPanel
          tickets={conversationTickets}
          activeTicketId={currentTicket?.id ?? null}
          selectedTicketId={selectedTicketId}
          selectedTicketDetail={selectedTicketDetail}
          isLoading={isTicketHistoryLoading}
          ticketActionLoading={ticketActionLoading}
          onSelectTicket={handleSelectTicket}
          onResolveTicket={handleResolveTicketById}
          onReopenTicket={handleReopenTicketById}
        />
      }
      activity={
        <>
          <ComplaintActivityFeed
            currentTicket={currentTicket}
            reviewSummary={reviewSummary}
            handoffReason={handoffReason}
            recentTasks={recentTasks}
          />
          <ComplaintLiveEventStream
            conversationId={conversationId}
            currentTicket={currentTicket}
            reviewSummary={reviewSummary}
            recentTasks={recentTasks}
            handoffReason={handoffReason}
            handoffState={effectiveHandoffState}
          />
        </>
      }
    />
  );

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center bg-background">
        <div className="text-center">
          <div className="mb-4 h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent mx-auto" />
          <p className="text-sm text-zinc-500">加载会话...</p>
        </div>
      </div>
    );
  }

  if (!conversation) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-4 px-6 text-center">
        <h2 className="text-lg font-semibold">暂时无法打开会话</h2>
        <p role="alert" className="max-w-sm text-sm text-muted-foreground">
          {error || "会话可能不存在，请返回列表重新选择。"}
        </p>
        <Button
          variant="outline"
          className="rounded-full"
          onClick={() => router.push("/support")}
        >
          返回会话列表
        </Button>
      </div>
    );
  }

  return (
    <div className="flex h-full min-h-0 overflow-hidden">
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="support-conversation-header flex min-h-[84px] shrink-0 items-center justify-between gap-2 border-b border-border bg-card px-5 py-4">
          <div className="flex min-w-0 items-center gap-3">
            <Button
              variant="ghost"
              size="icon"
              className="size-8 shrink-0 md:hidden"
              aria-label="返回会话列表"
              onClick={() => router.push("/support")}
            >
              <ArrowLeft className="size-4" />
            </Button>
            <span className="hidden size-9 shrink-0 items-center justify-center rounded-xl bg-secondary md:flex">
              <UserRound className="size-4" />
            </span>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <h2
                  className="support-conversation-title truncate text-[17px] font-semibold"
                  title={conversation?.title}
                >
                  客户 {conversation?.user_id?.slice(0, 8) ?? "未知"}
                </h2>
                <span
                  className={cn(
                    "support-badge hidden sm:inline-flex",
                    effectiveHandoffState === "pending"
                      ? "support-warning"
                      : effectiveHandoffState === "human"
                        ? "support-success"
                        : "bg-secondary text-muted-foreground",
                  )}
                >
                  {handoffModeLabel}
                </span>
              </div>
              <p
                className="mt-1 max-w-[230px] truncate text-xs text-muted-foreground"
                title={conversation?.title}
              >
                {conversation?.title || "新会话"} ·{" "}
                {conversationState.user_online ? "当前在线" : "当前离线"}
                {unreadCount > 0 ? ` · ${unreadCount} 条未读` : ""}
              </p>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <Sheet>
              <SheetTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="size-8 xl:hidden"
                  aria-label="查看会话详情"
                >
                  <PanelRight className="size-4" />
                </Button>
              </SheetTrigger>
              <SheetContent className="support-theme dark w-[min(92vw,400px)] gap-0 bg-card text-foreground">
                <SheetHeader className="border-b border-border">
                  <SheetTitle>会话详情</SheetTitle>
                  <SheetDescription>问题单、审查与处理记录</SheetDescription>
                </SheetHeader>
                {inspector}
              </SheetContent>
            </Sheet>
            {currentTicket && (
              <Button
                variant="outline"
                size="sm"
                className="hidden rounded-full 2xl:inline-flex"
                disabled={ticketActionLoading !== null}
                onClick={
                  currentTicket.status === "resolved" ||
                  currentTicket.status === "closed"
                    ? handleReopenTicket
                    : handleResolveTicket
                }
              >
                <Check className="size-3.5" />
                {ticketActionLoading
                  ? "处理中…"
                  : currentTicket.status === "resolved" ||
                      currentTicket.status === "closed"
                    ? "重新打开"
                    : "标记解决"}
              </Button>
            )}
            {effectiveHandoffState !== "human" ? (
              <Button
                size="sm"
                className="rounded-full"
                disabled={handoffLoading}
                onClick={handleStartHandoff}
              >
                <Headphones className="size-3.5" />
                <span>{handoffLoading ? "接入中…" : "接入会话"}</span>
              </Button>
            ) : (
              <Button
                variant="outline"
                size="sm"
                className="rounded-full"
                disabled={handoffLoading}
                onClick={handleEndHandoff}
              >
                <PhoneOff className="size-3.5" />
                <span>{handoffLoading ? "结束中…" : "结束服务"}</span>
              </Button>
            )}
          </div>
        </header>
        <div className="support-conversation-notice flex shrink-0 items-center justify-between gap-2 border-b border-border bg-card px-5 py-3 text-xs text-muted-foreground">
          <span className="truncate">
            {handoffReason ||
              (effectiveHandoffState === "human"
                ? "你已接入，正在为当前客户服务"
                : "AI 正在跟进，人工可随时接入会话")}
          </span>
          <span
            className={cn(
              "flex shrink-0 items-center gap-1.5",
              !isConnected && "text-destructive",
            )}
          >
            <Circle className="size-1.5 fill-current" />
            {isConnected ? "实时连接" : "连接已断开"}
          </span>
        </div>
        {error && (
          <div
            role="alert"
            className="mx-4 mt-3 shrink-0 rounded-xl border border-destructive/40 bg-destructive/10 p-3 text-xs text-destructive"
          >
            {error}
            <button className="ml-2 underline" onClick={() => setError(null)}>
              关闭
            </button>
          </div>
        )}
        {/* 消息列表 */}
        <div
          className="min-h-0 flex-1 overflow-y-auto px-4 py-6 md:px-6"
          aria-label="会话消息"
          tabIndex={0}
        >
          <div className="mx-auto max-w-3xl space-y-1">
            {messages.length === 0 ? (
              <div className="text-center text-zinc-500 py-10">暂无消息</div>
            ) : (
              messages.map((msg, idx) => renderMessage(msg, idx))
            )}

            {/* 用户正在输入 */}
            {userTyping && (
              <div className="flex w-full justify-end mb-3">
                <div className="bg-blue-500/20 rounded-3xl px-5 py-2.5">
                  <div className="flex gap-1">
                    <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" />
                    <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce [animation-delay:0.1s]" />
                    <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce [animation-delay:0.2s]" />
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* 输入区域 */}
        <div className="support-composer shrink-0 border-t border-border bg-card px-3 pt-3 pb-3 md:px-5 md:pb-4">
          <div className="mx-auto max-w-3xl">
            <div className="mb-2 flex items-center justify-between px-1 text-xs">
              <span>回复客户</span>
              <span className="text-muted-foreground">
                {effectiveHandoffState === "human"
                  ? "Enter 发送 · Shift + Enter 换行"
                  : "接入后可回复"}
              </span>
            </div>
            {effectiveHandoffState !== "human" ? (
              /* 未接入时显示提示 */
              <div className="flex items-center justify-center py-4">
                <div className="w-full rounded-xl bg-transparent px-2 py-4 text-sm text-muted-foreground">
                  接入会话后，开始与客户沟通…
                </div>
              </div>
            ) : (
              <>
                {/* 待发送图片预览 */}
                {pendingImages.length > 0 && (
                  <div className="flex flex-wrap gap-2 mb-3 px-2">
                    {pendingImages.map((img) => (
                      <div key={img.id} className="relative group">
                        <Image
                          src={img.thumbnail_url || img.url}
                          alt={img.filename || "待发送图片"}
                          width={64}
                          height={64}
                          unoptimized
                          className="h-16 w-16 rounded-lg object-cover border border-zinc-700"
                        />
                        <button
                          aria-label={`移除图片 ${img.filename || "附件"}`}
                          onClick={() => removePendingImage(img.id)}
                          className="absolute -top-1.5 -right-1.5 h-5 w-5 rounded-full bg-red-500 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                        >
                          <X className="h-3 w-3" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
                {/* 隐藏的文件输入 */}
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  multiple
                  onChange={handleImageSelect}
                  className="hidden"
                />
                {/* 输入框容器 - 深色主题 */}
                <div className="relative support-reply-editor">
                  <ChatRichInput
                    ariaLabel="回复客户"
                    hasAttachments={pendingImages.length > 0}
                    value={inputValue}
                    onValueChange={setInputValue}
                    onSubmit={handleSend}
                    placeholder={
                      isConnected
                        ? "输入回复，帮助客户解决当前问题…"
                        : "连接已断开，正在重新连接…"
                    }
                    disabled={!isConnected || isUploading}
                    isLoading={false}
                    showToolbar={true}
                    className="flex-1"
                    imageButton={
                      <button
                        aria-label="添加图片附件"
                        onClick={() => fileInputRef.current?.click()}
                        disabled={isUploading}
                        className={cn(
                          "flex h-7 w-7 shrink-0 items-center justify-center rounded-lg transition-colors",
                          "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-700",
                          "disabled:opacity-50 disabled:cursor-not-allowed",
                        )}
                      >
                        <ImagePlus
                          className={cn(
                            "h-4 w-4",
                            isUploading && "animate-pulse",
                          )}
                        />
                      </button>
                    }
                  />
                </div>
              </>
            )}
          </div>
        </div>
      </div>
      <aside
        aria-label="会话详情"
        className="hidden w-[280px] shrink-0 flex-col border-l border-border bg-card xl:flex 2xl:w-[308px]"
      >
        <div className="flex h-[65px] shrink-0 items-center justify-between border-b border-border px-5">
          <h2 className="text-sm font-semibold">会话详情</h2>
          <span className="text-xs text-muted-foreground">当前会话</span>
        </div>
        {inspector}
      </aside>

      {/* FAQ 表单（仅 FAQ Agent 显示） */}
      {faqAgent && (
        <FAQFormSheet
          open={faqSheetOpen}
          entry={null}
          agents={[faqAgent]}
          onClose={() => {
            setFaqSheetOpen(false);
            setSelectedQuestion("");
            setSelectedAnswer("");
            setSelectedSource("");
          }}
          onSave={handleSaveFAQ}
          initialQuestion={selectedQuestion}
          initialAnswer={selectedAnswer}
          initialSource={selectedSource}
          initialAgentId={faqAgent.id}
          readOnlyAgent
        />
      )}

      {/* 撤回确认弹窗 */}
      <Dialog open={withdrawDialogOpen} onOpenChange={setWithdrawDialogOpen}>
        <DialogContent className="support-theme dark sm:max-w-md">
          <DialogHeader>
            <DialogTitle>确认撤回</DialogTitle>
            <DialogDescription>
              确定要撤回这条消息吗？撤回后用户将看到「此消息已被客服撤回」。
            </DialogDescription>
          </DialogHeader>
          {withdrawingMessage && (
            <div className="p-3 bg-zinc-100 dark:bg-zinc-800 rounded-lg text-sm text-zinc-700 dark:text-zinc-300 max-h-32 overflow-y-auto">
              {withdrawingMessage.content.length > 100
                ? `${withdrawingMessage.content.slice(0, 100)}...`
                : withdrawingMessage.content}
            </div>
          )}
          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              variant="outline"
              onClick={() => setWithdrawDialogOpen(false)}
            >
              取消
            </Button>
            <Button variant="destructive" onClick={confirmWithdraw}>
              确认撤回
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 编辑消息弹窗 */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent className="support-theme dark sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>编辑消息</DialogTitle>
            <DialogDescription>
              修改消息内容。
              {editingMessage?.role === "user" &&
                "编辑用户消息后可以选择重新生成 AI 回复。"}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label className="text-sm font-medium mb-2 block">消息内容</Label>
              <Textarea
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
                rows={4}
                className="resize-none"
                placeholder="输入新的消息内容..."
              />
            </div>
            {editingMessage?.role === "user" && (
              <div className="flex items-center gap-3 p-3 bg-amber-50 dark:bg-amber-900/20 rounded-lg">
                <Switch
                  id="regenerate"
                  checked={editRegenerate}
                  onCheckedChange={setEditRegenerate}
                />
                <Label htmlFor="regenerate" className="text-sm cursor-pointer">
                  删除后续 AI 回复并重新生成
                </Label>
              </div>
            )}
          </div>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              variant="outline"
              onClick={() => {
                setEditDialogOpen(false);
                setEditingMessage(null);
                setEditContent("");
              }}
            >
              取消
            </Button>
            <Button
              onClick={confirmEdit}
              disabled={!editContent.trim()}
              className="bg-green-500 hover:bg-green-600"
            >
              保存
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
