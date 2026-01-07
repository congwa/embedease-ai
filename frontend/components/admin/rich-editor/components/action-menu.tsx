"use client";

import { useCallback, useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import { cn } from "@/lib/utils";

export interface ActionMenuItem {
  key: string;
  label: React.ReactNode;
  icon?: React.ReactNode;
  danger?: boolean;
  onClick: () => void;
}

export interface ActionMenuProps {
  show: boolean;
  position: { x: number; y: number };
  items: ActionMenuItem[];
  onClose: () => void;
  minWidth?: number;
}

export function ActionMenu({ show, position, items, onClose, minWidth = 168 }: ActionMenuProps) {
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!show) return;

    const onDocMouseDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        onClose();
      }
    };

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };

    document.addEventListener("mousedown", onDocMouseDown);
    document.addEventListener("keydown", onKeyDown);

    return () => {
      document.removeEventListener("mousedown", onDocMouseDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [show, onClose]);

  const handleItemClick = useCallback(
    (item: ActionMenuItem) => {
      item.onClick();
      onClose();
    },
    [onClose]
  );

  if (!show) return null;

  const node = (
    <div
      ref={ref}
      className="fixed z-[2000] overflow-hidden rounded-md border border-zinc-200 bg-white shadow-lg dark:border-zinc-700 dark:bg-zinc-800"
      style={{
        left: position.x,
        top: position.y,
        minWidth,
      }}
    >
      <div className="py-1">
        {items.map((item) => (
          <button
            key={item.key}
            type="button"
            onClick={() => handleItemClick(item)}
            className={cn(
              "flex w-full items-center gap-2 px-3 py-1.5 text-left text-sm transition-colors",
              "hover:bg-zinc-100 dark:hover:bg-zinc-700",
              item.danger && "text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20"
            )}
          >
            {item.icon && <span className="flex-shrink-0">{item.icon}</span>}
            <span>{item.label}</span>
          </button>
        ))}
      </div>
    </div>
  );

  if (typeof document === "undefined") return null;
  return createPortal(node, document.body);
}

export default ActionMenu;
