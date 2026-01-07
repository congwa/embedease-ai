"use client";

import { forwardRef, useEffect, useImperativeHandle, useState } from "react";
import { cn } from "@/lib/utils";
import type { Command } from "../types";

interface CommandListProps {
  items: Command[];
  command: (item: Command) => void;
}

export interface CommandListRef {
  onKeyDown: (event: KeyboardEvent) => boolean;
}

export const CommandList = forwardRef<CommandListRef, CommandListProps>(
  ({ items, command }, ref) => {
    const [selectedIndex, setSelectedIndex] = useState(0);

    useEffect(() => {
      setSelectedIndex(0);
    }, [items]);

    useImperativeHandle(ref, () => ({
      onKeyDown: (event: KeyboardEvent) => {
        if (event.key === "ArrowUp") {
          setSelectedIndex((prev) => (prev - 1 + items.length) % items.length);
          return true;
        }

        if (event.key === "ArrowDown") {
          setSelectedIndex((prev) => (prev + 1) % items.length);
          return true;
        }

        if (event.key === "Enter") {
          const item = items[selectedIndex];
          if (item) {
            command(item);
          }
          return true;
        }

        return false;
      },
    }));

    if (items.length === 0) {
      return (
        <div className="p-3 text-center text-sm text-zinc-500">
          没有找到匹配的命令
        </div>
      );
    }

    return (
      <div className="max-h-[300px] overflow-y-auto py-1">
        {items.map((item, index) => {
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => command(item)}
              className={cn(
                "flex w-full items-center gap-3 px-3 py-2 text-left text-sm transition-colors",
                index === selectedIndex
                  ? "bg-zinc-100 dark:bg-zinc-700"
                  : "hover:bg-zinc-50 dark:hover:bg-zinc-800"
              )}
            >
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded bg-zinc-100 dark:bg-zinc-700">
                <Icon className="h-4 w-4 text-zinc-600 dark:text-zinc-400" />
              </div>
              <div className="flex-1 overflow-hidden">
                <div className="truncate font-medium">{item.title}</div>
                <div className="truncate text-xs text-zinc-500">
                  {item.description}
                </div>
              </div>
            </button>
          );
        })}
      </div>
    );
  }
);

CommandList.displayName = "CommandList";

export default CommandList;
