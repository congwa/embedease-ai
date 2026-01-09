"use client";

import { MessageSquare, Plus, Search, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
} from "@/components/ui/sidebar";
import type { Conversation } from "@/types/conversation";
import { useConversationStore } from "@/stores";

export function ChatSidebar() {
  // 从 Store 获取状态
  const conversations = useConversationStore((s) => s.conversations);
  const currentConversationId = useConversationStore((s) => s.currentConversationId);
  const createNewConversation = useConversationStore((s) => s.createNewConversation);
  const selectConversation = useConversationStore((s) => s.selectConversation);
  const removeConversation = useConversationStore((s) => s.removeConversation);

  // 按日期分组会话
  const groupedConversations = groupConversationsByDate(conversations);

  return (
    <Sidebar>
      <SidebarHeader className="flex flex-row items-center justify-between gap-2 px-2 py-4">
        <div className="flex flex-row items-center gap-2 px-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-orange-500/10">
            <MessageSquare className="h-4 w-4 text-orange-500" />
          </div>
          <div className="text-md font-medium tracking-tight text-zinc-900 dark:text-zinc-100">
            商品推荐
          </div>
        </div>
        <Button variant="ghost" size="icon" className="h-8 w-8">
          <Search className="h-4 w-4" />
        </Button>
      </SidebarHeader>
      
      <SidebarContent className="pt-4">
        <div className="px-4">
          <Button
            variant="outline"
            className="mb-4 flex w-full items-center gap-2"
            onClick={createNewConversation}
          >
            <Plus className="h-4 w-4" />
            <span>新对话</span>
          </Button>
        </div>
        
        {groupedConversations.map((group) => (
          <SidebarGroup key={group.period}>
            <SidebarGroupLabel>{group.period}</SidebarGroupLabel>
            <SidebarMenu>
              {group.conversations.map((conversation) => (
                <div key={conversation.id} className="group relative">
                  <SidebarMenuButton
                    isActive={conversation.id === currentConversationId}
                    onClick={() => selectConversation(conversation.id)}
                    className="pr-8"
                  >
                    <span className="truncate">{conversation.title}</span>
                  </SidebarMenuButton>
                  
                  <Button
                    variant="ghost"
                    size="icon"
                    className="absolute right-1 top-1/2 h-6 w-6 -translate-y-1/2 opacity-0 group-hover:opacity-100"
                    onClick={(e) => {
                      e.stopPropagation();
                      removeConversation(conversation.id);
                    }}
                  >
                    <Trash2 className="h-3 w-3 text-zinc-400 hover:text-red-500" />
                  </Button>
                </div>
              ))}
            </SidebarMenu>
          </SidebarGroup>
        ))}
        
        {conversations.length === 0 && (
          <div className="px-4 py-8 text-center text-sm text-zinc-500">
            暂无会话记录
          </div>
        )}
      </SidebarContent>
    </Sidebar>
  );
}

// 辅助函数：按日期分组会话
interface GroupedConversations {
  period: string;
  conversations: Conversation[];
}

export function groupConversationsByDate(
  conversations: Conversation[]
): GroupedConversations[] {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today.getTime() - 24 * 60 * 60 * 1000);
  const lastWeek = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);

  const groups: Record<string, Conversation[]> = {
    今天: [],
    昨天: [],
    近7天: [],
    更早: [],
  };

  for (const conversation of conversations) {
    const date = new Date(conversation.updated_at);
    
    if (date >= today) {
      groups["今天"].push(conversation);
    } else if (date >= yesterday) {
      groups["昨天"].push(conversation);
    } else if (date >= lastWeek) {
      groups["近7天"].push(conversation);
    } else {
      groups["更早"].push(conversation);
    }
  }

  return Object.entries(groups)
    .filter(([, convs]) => convs.length > 0)
    .map(([period, convs]) => ({
      period,
      conversations: convs,
    }));
}
