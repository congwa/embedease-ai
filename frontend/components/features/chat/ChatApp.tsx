"use client";

import { useEffect } from "react";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { useUserStore, useConversationStore, useChatStore } from "@/stores";
import { ChatSidebar } from "./ChatSidebar";
import { ChatContent } from "./ChatContent";
import { ChatThemeProvider } from "./themes";

export function ChatApp() {
  // Store 状态
  const userId = useUserStore((s) => s.userId);
  const isUserLoading = useUserStore((s) => s.isLoading);
  const initUser = useUserStore((s) => s.initUser);

  // 初始化用户
  useEffect(() => {
    initUser();
  }, [initUser]);

  // 加载中状态
  if (isUserLoading || !userId) {
    return (
      <div className="flex h-screen items-center justify-center bg-zinc-50 dark:bg-zinc-900">
        <div className="text-center">
          <div className="mb-4 h-8 w-8 animate-spin rounded-full border-2 border-orange-500 border-t-transparent mx-auto" />
          <p className="text-sm text-zinc-500">正在加载...</p>
        </div>
      </div>
    );
  }

  return (
    <ChatThemeProvider>
      <SidebarProvider>
        <ChatSidebar />
        <SidebarInset>
          <ChatContent />
        </SidebarInset>
      </SidebarProvider>
    </ChatThemeProvider>
  );
}
