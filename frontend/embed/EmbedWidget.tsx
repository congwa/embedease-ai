"use client";

import React, { useState, useCallback, useEffect } from "react";
import { MessageCircle, X, Trash2, Minus, AlertCircle, ArrowUp, Square } from "lucide-react";
import "./embed.css";

interface EmbedConfig {
  apiBaseUrl?: string;
  position?: "bottom-right" | "bottom-left";
  primaryColor?: string;
  title?: string;
  placeholder?: string;
}

interface EmbedWidgetProps {
  config: EmbedConfig;
}

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
}

// 简化版 API 调用
async function createUser(apiBaseUrl: string): Promise<{ user_id: string }> {
  const res = await fetch(`${apiBaseUrl}/api/v1/users`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  if (!res.ok) throw new Error("Failed to create user");
  return res.json();
}

async function createConversation(
  apiBaseUrl: string,
  userId: string
): Promise<{ id: string }> {
  const res = await fetch(`${apiBaseUrl}/api/v1/conversations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId }),
  });
  if (!res.ok) throw new Error("Failed to create conversation");
  return res.json();
}

async function* streamChat(
  apiBaseUrl: string,
  userId: string,
  conversationId: string,
  message: string,
  signal?: AbortSignal
): AsyncGenerator<{ type: string; payload: unknown }> {
  const res = await fetch(`${apiBaseUrl}/api/v1/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_id: userId,
      conversation_id: conversationId,
      message,
    }),
    signal,
  });

  if (!res.ok) throw new Error("Failed to send message");

  const reader = res.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try {
          const event = JSON.parse(line.slice(6));
          yield event;
        } catch {
          // ignore parse errors
        }
      }
    }
  }
}

export function EmbedWidget({ config }: EmbedWidgetProps) {
  const apiBaseUrl = config.apiBaseUrl || "";
  const position = config.position || "bottom-right";
  const title = config.title || "商品推荐助手";
  const placeholder = config.placeholder || "输入消息...";

  const [isOpen, setIsOpen] = useState(false);
  const [userId, setUserId] = useState<string | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [abortController, setAbortController] = useState<AbortController | null>(null);

  // 初始化用户
  useEffect(() => {
    const initUser = async () => {
      try {
        const storageKey = "embed_ai_user_id";
        let storedUserId = localStorage.getItem(storageKey);

        if (!storedUserId) {
          const { user_id } = await createUser(apiBaseUrl);
          storedUserId = user_id;
          localStorage.setItem(storageKey, user_id);
        }

        setUserId(storedUserId);
      } catch (err) {
        console.error("[EmbedWidget] Failed to init user:", err);
        // 使用临时 ID
        setUserId(crypto.randomUUID());
      } finally {
        setIsLoading(false);
      }
    };

    initUser();
  }, [apiBaseUrl]);

  // 发送消息
  const sendMessage = useCallback(
    async (content: string) => {
      if (!userId || !content.trim() || isStreaming) return;

      setError(null);
      setIsStreaming(true);

      // 添加用户消息
      const userMsg: Message = {
        id: crypto.randomUUID(),
        role: "user",
        content: content.trim(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setInput("");

      // 确保有会话
      let convId = conversationId;
      if (!convId) {
        try {
          const conv = await createConversation(apiBaseUrl, userId);
          convId = conv.id;
          setConversationId(convId);
        } catch (err) {
          setError("创建会话失败");
          setIsStreaming(false);
          return;
        }
      }

      // 创建 assistant 消息占位
      const assistantMsg: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: "",
      };
      setMessages((prev) => [...prev, assistantMsg]);

      // 流式请求
      const controller = new AbortController();
      setAbortController(controller);

      try {
        for await (const event of streamChat(
          apiBaseUrl,
          userId,
          convId,
          content.trim(),
          controller.signal
        )) {
          if (event.type === "assistant.delta") {
            const delta = (event.payload as { delta?: string })?.delta || "";
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsg.id
                  ? { ...m, content: m.content + delta }
                  : m
              )
            );
          }
        }
      } catch (err) {
        if (err instanceof Error && err.name !== "AbortError") {
          setError(err.message);
        }
      } finally {
        setIsStreaming(false);
        setAbortController(null);
      }
    },
    [userId, conversationId, apiBaseUrl, isStreaming]
  );

  // 中断流
  const handleAbort = useCallback(() => {
    abortController?.abort();
    setIsStreaming(false);
  }, [abortController]);

  // 清空对话
  const handleClear = useCallback(async () => {
    if (isStreaming) {
      handleAbort();
    }
    setMessages([]);
    setConversationId(null);
    setError(null);

    // 创建新会话
    if (userId) {
      try {
        const conv = await createConversation(apiBaseUrl, userId);
        setConversationId(conv.id);
      } catch {
        // ignore
      }
    }
  }, [userId, apiBaseUrl, isStreaming, handleAbort]);

  // 提交
  const handleSubmit = () => {
    if (isStreaming) {
      handleAbort();
    } else if (input.trim()) {
      sendMessage(input);
    }
  };

  // 键盘事件
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const positionClass =
    position === "bottom-left" ? "embed-position-left" : "embed-position-right";

  return (
    <div className={`embed-widget ${positionClass}`}>
      {/* 聊天面板 */}
      {isOpen && (
        <div className="embed-panel">
          {/* 头部 */}
          <div className="embed-header">
            <div className="embed-header-title">
              <span className="embed-header-icon">🛒</span>
              <span>{title}</span>
            </div>
            <div className="embed-header-actions">
              <button
                className="embed-icon-btn"
                onClick={handleClear}
                title="清空对话"
                disabled={isLoading}
              >
                <Trash2 size={16} />
              </button>
              <button
                className="embed-icon-btn"
                onClick={() => setIsOpen(false)}
                title="收起"
              >
                <Minus size={16} />
              </button>
            </div>
          </div>

          {/* 消息区域 */}
          <div className="embed-messages">
            {isLoading ? (
              <div className="embed-loading">
                <div className="embed-spinner" />
                <span>正在加载...</span>
              </div>
            ) : messages.length === 0 ? (
              <div className="embed-empty">
                <div className="embed-empty-icon">🛒</div>
                <div className="embed-empty-title">有什么可以帮您？</div>
                <div className="embed-empty-desc">告诉我你想要什么商品</div>
                <div className="embed-suggestions">
                  {["推荐降噪耳机", "好的跑步鞋", "买破壁机"].map((s) => (
                    <button
                      key={s}
                      className="embed-suggestion-btn"
                      onClick={() => sendMessage(s)}
                      disabled={isStreaming}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`embed-message embed-message-${msg.role}`}
                >
                  <div className="embed-message-content">{msg.content}</div>
                </div>
              ))
            )}
          </div>

          {/* 输入区域 */}
          <div className="embed-input-area">
            {error && (
              <div className="embed-error">
                <AlertCircle size={14} />
                <span>{error}</span>
                <button onClick={() => setError(null)}>
                  <X size={14} />
                </button>
              </div>
            )}
            <div className="embed-input-wrapper">
              <textarea
                className="embed-input"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={placeholder}
                rows={1}
                disabled={isLoading}
              />
              <button
                className={`embed-send-btn ${isStreaming ? "embed-send-btn-stop" : ""}`}
                onClick={handleSubmit}
                disabled={isLoading || (!isStreaming && !input.trim())}
              >
                {isStreaming ? <Square size={14} /> : <ArrowUp size={14} />}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 悬浮按钮 */}
      <button
        className={`embed-fab ${isOpen ? "embed-fab-close" : ""}`}
        onClick={() => setIsOpen(!isOpen)}
      >
        {isOpen ? <X size={24} /> : <MessageCircle size={24} />}
      </button>
    </div>
  );
}
