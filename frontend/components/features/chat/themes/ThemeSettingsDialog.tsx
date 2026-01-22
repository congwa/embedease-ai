"use client";

import { useState } from "react";
import { Check, Moon, Sun, Monitor, Palette } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useChatTheme, type ColorMode } from "./chat-theme-provider";
import type { ChatThemeId } from "./theme-registry";

interface ThemePreviewProps {
  themeId: ChatThemeId;
  name: string;
  description: string;
  previewColors: {
    primary: string;
    background: string;
    accent: string;
  };
  isSelected: boolean;
  onClick: () => void;
}

function ThemePreview({
  name,
  description,
  previewColors,
  isSelected,
  onClick,
}: ThemePreviewProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "relative flex flex-col items-center gap-2 rounded-lg border-2 p-3 transition-all",
        isSelected
          ? "border-blue-500 bg-blue-50 dark:bg-blue-950/30"
          : "border-zinc-200 hover:border-zinc-300 dark:border-zinc-700 dark:hover:border-zinc-600"
      )}
    >
      {/* 预览色块 */}
      <div
        className="flex h-16 w-full overflow-hidden rounded-md"
        style={{ backgroundColor: previewColors.background }}
      >
        <div
          className="w-1/3 h-full"
          style={{ backgroundColor: previewColors.primary }}
        />
        <div className="w-1/3 h-full flex items-center justify-center">
          <div
            className="w-4 h-4 rounded-full"
            style={{ backgroundColor: previewColors.accent }}
          />
        </div>
        <div
          className="w-1/3 h-full opacity-50"
          style={{ backgroundColor: previewColors.primary }}
        />
      </div>

      {/* 主题名称 */}
      <div className="text-center">
        <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
          {name}
        </p>
        <p className="text-xs text-zinc-500 dark:text-zinc-400 line-clamp-1">
          {description}
        </p>
      </div>

      {/* 选中标记 */}
      {isSelected && (
        <div className="absolute -top-1.5 -right-1.5 flex h-5 w-5 items-center justify-center rounded-full bg-blue-500 text-white">
          <Check className="h-3 w-3" />
        </div>
      )}
    </button>
  );
}

interface ColorModeButtonProps {
  mode: ColorMode;
  label: string;
  icon: React.ReactNode;
  isSelected: boolean;
  onClick: () => void;
}

function ColorModeButton({
  label,
  icon,
  isSelected,
  onClick,
}: ColorModeButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex items-center gap-2 rounded-lg border-2 px-4 py-2.5 transition-all",
        isSelected
          ? "border-blue-500 bg-blue-50 dark:bg-blue-950/30"
          : "border-zinc-200 hover:border-zinc-300 dark:border-zinc-700 dark:hover:border-zinc-600"
      )}
    >
      {icon}
      <span className="text-sm font-medium">{label}</span>
      {isSelected && <Check className="h-4 w-4 text-blue-500 ml-auto" />}
    </button>
  );
}

interface ThemeSettingsDialogProps {
  trigger?: React.ReactNode;
}

export function ThemeSettingsDialog({ trigger }: ThemeSettingsDialogProps) {
  const [open, setOpen] = useState(false);
  const {
    themeId,
    setTheme,
    availableThemes,
    colorMode,
    setColorMode,
  } = useChatTheme();

  // 只显示新的三套主题
  const displayThemes = availableThemes.filter((t) =>
    ["techbiz", "warmshop", "luxemin"].includes(t.id)
  );

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger || (
          <Button variant="ghost" size="icon" title="主题设置">
            <Palette className="h-5 w-5" />
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Palette className="h-5 w-5" />
            主题设置
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* 主题选择 */}
          <div className="space-y-3">
            <h4 className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
              选择主题风格
            </h4>
            <div className="grid grid-cols-3 gap-3">
              {displayThemes.map((theme) => (
                <ThemePreview
                  key={theme.id}
                  themeId={theme.id}
                  name={theme.name}
                  description={theme.description}
                  previewColors={theme.previewColors}
                  isSelected={themeId === theme.id}
                  onClick={() => setTheme(theme.id)}
                />
              ))}
            </div>
          </div>

          {/* 分隔线 */}
          <div className="border-t border-zinc-200 dark:border-zinc-700" />

          {/* 颜色模式 */}
          <div className="space-y-3">
            <h4 className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
              外观模式
            </h4>
            <div className="flex gap-2">
              <ColorModeButton
                mode="light"
                label="浅色"
                icon={<Sun className="h-4 w-4" />}
                isSelected={colorMode === "light"}
                onClick={() => setColorMode("light")}
              />
              <ColorModeButton
                mode="dark"
                label="深色"
                icon={<Moon className="h-4 w-4" />}
                isSelected={colorMode === "dark"}
                onClick={() => setColorMode("dark")}
              />
              <ColorModeButton
                mode="system"
                label="跟随系统"
                icon={<Monitor className="h-4 w-4" />}
                isSelected={colorMode === "system"}
                onClick={() => setColorMode("system")}
              />
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
