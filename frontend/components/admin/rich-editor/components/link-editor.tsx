"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Trash2 } from "lucide-react";

interface LinkEditorProps {
  visible: boolean;
  position: { x: number; y: number } | null;
  link: { href: string; text: string };
  onSave: (href: string, text: string) => void;
  onRemove: () => void;
  onCancel: () => void;
  showRemove?: boolean;
}

export function LinkEditor({
  visible,
  position,
  link,
  onSave,
  onRemove,
  onCancel,
  showRemove = true,
}: LinkEditorProps) {
  const [href, setHref] = useState<string>(link.href || "");
  const [text, setText] = useState<string>(link.text || "");
  const containerRef = useRef<HTMLDivElement>(null);
  const hrefInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (visible) {
      setHref(link.href || "");
      setText(link.text || "");
    }
  }, [visible, link.href, link.text]);

  useEffect(() => {
    if (visible && hrefInputRef.current) {
      setTimeout(() => {
        hrefInputRef.current?.focus();
      }, 100);
    }
  }, [visible]);

  useEffect(() => {
    if (!visible) return;

    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as HTMLElement;
      if (
        containerRef.current?.contains(target) ||
        target.closest("a[href]") ||
        target.closest("[data-link-editor]")
      ) {
        return;
      }
      onCancel();
    };

    setTimeout(() => {
      document.addEventListener("mousedown", handleClickOutside);
    }, 100);

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [visible, onCancel]);

  const handleSave = useCallback(() => {
    const trimmedHref = href.trim();
    const trimmedText = text.trim();
    if (trimmedHref && trimmedText) {
      onSave(trimmedHref, trimmedText);
    }
  }, [href, text, onSave]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        handleSave();
      } else if (e.key === "Escape") {
        e.preventDefault();
        onCancel();
      }
    },
    [handleSave, onCancel]
  );

  if (!visible || !position) return null;

  return (
    <div
      ref={containerRef}
      data-link-editor
      onKeyDown={handleKeyDown}
      className="fixed z-[1000] w-80 max-w-[90vw] rounded-lg border border-zinc-200 bg-white p-3 shadow-lg dark:border-zinc-700 dark:bg-zinc-800"
      style={{
        left: position.x,
        top: position.y + 25,
      }}
    >
      <div className="mb-3">
        <Label className="mb-1 block text-xs font-semibold">链接文本</Label>
        <Input
          ref={hrefInputRef}
          value={text}
          placeholder="输入链接文本"
          onChange={(e) => setText(e.target.value)}
          className="h-8"
        />
      </div>

      <div className="mb-3">
        <Label className="mb-1 block text-xs font-semibold">链接地址</Label>
        <Input
          value={href}
          placeholder="https://example.com"
          onChange={(e) => setHref(e.target.value)}
          className="h-8"
        />
      </div>

      <div className="flex items-center justify-between">
        <div>
          {showRemove && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={onRemove}
              className="h-7 px-2 text-red-500 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/20"
            >
              <Trash2 className="mr-1 h-3.5 w-3.5" />
              移除链接
            </Button>
          )}
        </div>
        <div className="flex gap-2">
          <Button type="button" variant="outline" size="sm" onClick={onCancel} className="h-7">
            取消
          </Button>
          <Button
            type="button"
            size="sm"
            onClick={handleSave}
            disabled={!href.trim() || !text.trim()}
            className="h-7"
          >
            保存
          </Button>
        </div>
      </div>
    </div>
  );
}

export default LinkEditor;
