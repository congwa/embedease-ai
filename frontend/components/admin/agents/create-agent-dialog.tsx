"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Bot, Network, ShoppingBag, HelpCircle, BookOpen, Wrench } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { cn } from "@/lib/utils";
import { createAgent } from "@/lib/api/agents";

const AGENT_TYPES = [
  {
    id: "product",
    name: "商品推荐",
    description: "智能商品搜索与推荐",
    icon: ShoppingBag,
    color: "text-blue-500",
    bgColor: "bg-blue-50 dark:bg-blue-950/30",
  },
  {
    id: "faq",
    name: "FAQ 问答",
    description: "基于预设问答对回复",
    icon: HelpCircle,
    color: "text-green-500",
    bgColor: "bg-green-50 dark:bg-green-950/30",
  },
  {
    id: "kb",
    name: "知识库",
    description: "文档检索与问答",
    icon: BookOpen,
    color: "text-purple-500",
    bgColor: "bg-purple-50 dark:bg-purple-950/30",
  },
  {
    id: "custom",
    name: "自定义",
    description: "完全自定义配置",
    icon: Wrench,
    color: "text-zinc-500",
    bgColor: "bg-zinc-50 dark:bg-zinc-800",
  },
  {
    id: "supervisor",
    name: "智能调度器",
    description: "多 Agent 编排，自动路由",
    icon: Network,
    color: "text-orange-500",
    bgColor: "bg-orange-50 dark:bg-orange-950/30",
    isSupervisor: true,
  },
];

interface CreateAgentDialogProps {
  trigger?: React.ReactNode;
  onCreated?: (agentId: string) => void;
}

export function CreateAgentDialog({ trigger, onCreated }: CreateAgentDialogProps) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState<"type" | "details">("type");
  const [selectedType, setSelectedType] = useState<string>("product");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedTypeInfo = AGENT_TYPES.find((t) => t.id === selectedType);

  const handleCreate = async () => {
    if (!name.trim()) {
      setError("请输入 Agent 名称");
      return;
    }

    setIsCreating(true);
    setError(null);

    try {
      const isSupervisor = selectedType === "supervisor";
      const agent = await createAgent({
        name: name.trim(),
        description: description.trim() || null,
        type: isSupervisor ? "custom" : (selectedType as "product" | "faq" | "kb" | "custom"),
        is_supervisor: isSupervisor,
        status: "enabled",
      });

      setOpen(false);
      resetForm();

      if (onCreated) {
        onCreated(agent.id);
      } else {
        router.push(`/admin/agents/${agent.id}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "创建失败");
    } finally {
      setIsCreating(false);
    }
  };

  const resetForm = () => {
    setStep("type");
    setSelectedType("product");
    setName("");
    setDescription("");
    setError(null);
  };

  const handleOpenChange = (newOpen: boolean) => {
    setOpen(newOpen);
    if (!newOpen) {
      resetForm();
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        {trigger || (
          <Button size="sm">
            <Bot className="mr-2 h-4 w-4" />
            新建 Agent
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>
            {step === "type" ? "选择 Agent 类型" : "填写基本信息"}
          </DialogTitle>
          <DialogDescription>
            {step === "type"
              ? "选择适合您业务场景的 Agent 类型"
              : `创建一个${selectedTypeInfo?.name} Agent`}
          </DialogDescription>
        </DialogHeader>

        {step === "type" ? (
          <div className="py-4">
            <RadioGroup
              value={selectedType}
              onValueChange={setSelectedType}
              className="grid grid-cols-1 gap-3"
            >
              {AGENT_TYPES.map((type) => {
                const Icon = type.icon;
                return (
                  <Label
                    key={type.id}
                    htmlFor={type.id}
                    className={cn(
                      "flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors",
                      selectedType === type.id
                        ? "border-primary bg-primary/5"
                        : "border-zinc-200 hover:border-zinc-300 dark:border-zinc-800"
                    )}
                  >
                    <RadioGroupItem value={type.id} id={type.id} className="sr-only" />
                    <div className={cn("p-2 rounded-lg", type.bgColor)}>
                      <Icon className={cn("h-5 w-5", type.color)} />
                    </div>
                    <div className="flex-1">
                      <div className="font-medium text-sm">{type.name}</div>
                      <div className="text-xs text-zinc-500">{type.description}</div>
                    </div>
                    {type.isSupervisor && (
                      <span className="text-xs bg-orange-100 text-orange-700 px-2 py-0.5 rounded dark:bg-orange-900 dark:text-orange-300">
                        多 Agent
                      </span>
                    )}
                  </Label>
                );
              })}
            </RadioGroup>
          </div>
        ) : (
          <div className="py-4 space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">名称 *</Label>
              <Input
                id="name"
                placeholder="例如：商品推荐助手"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">描述</Label>
              <Textarea
                id="description"
                placeholder="简要描述这个 Agent 的用途"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={3}
              />
            </div>
            {error && (
              <p className="text-sm text-red-500">{error}</p>
            )}
          </div>
        )}

        <DialogFooter>
          {step === "type" ? (
            <Button onClick={() => setStep("details")}>
              下一步
            </Button>
          ) : (
            <div className="flex gap-2 w-full">
              <Button variant="outline" onClick={() => setStep("type")}>
                上一步
              </Button>
              <Button onClick={handleCreate} disabled={isCreating} className="flex-1">
                {isCreating ? "创建中..." : "创建 Agent"}
              </Button>
            </div>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
