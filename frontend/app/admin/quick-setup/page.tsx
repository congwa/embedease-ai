"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  CheckCircle,
  Circle,
  ChevronLeft,
  ChevronRight,
  RotateCcw,
  Loader2,
  AlertCircle,
  SkipForward,
} from "lucide-react";
import { PageHeader } from "@/components/admin";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";
import {
  getSetupState,
  resetSetupState,
  completeStep,
  skipStep,
  gotoStep,
  getAgentTypes,
  type QuickSetupState,
  type SetupStep,
  type AgentTypeConfig,
} from "@/lib/api/quick-setup";

import { WelcomeStep } from "./steps/welcome-step";
import { ModeStep } from "./steps/mode-step";
import { SystemStep } from "./steps/system-step";
import { ModelsStep } from "./steps/models-step";
import { AgentTypeStep } from "./steps/agent-type-step";
import { KnowledgeStep } from "./steps/knowledge-step";
import { GreetingStep } from "./steps/greeting-step";
import { ChannelStep } from "./steps/channel-step";
import { SummaryStep } from "./steps/summary-step";
import { SupervisorStep } from "./steps/supervisor-step";

const STEP_COMPONENTS: Record<string, React.ComponentType<StepProps>> = {
  welcome: WelcomeStep,
  mode: ModeStep,
  system: SystemStep,
  models: ModelsStep,
  "agent-type": AgentTypeStep,
  knowledge: KnowledgeStep,
  greeting: GreetingStep,
  channel: ChannelStep,
  summary: SummaryStep,
  supervisor: SupervisorStep,
};

export interface StepProps {
  step: SetupStep;
  state: QuickSetupState;
  agentTypes: AgentTypeConfig[];
  onComplete: (data?: Record<string, unknown>) => Promise<void>;
  onSkip: () => Promise<void>;
  onGoto: (index: number) => Promise<void>;
  isLoading: boolean;
}

function StepIndicator({
  step,
  isActive,
  onClick,
}: {
  step: SetupStep;
  isActive: boolean;
  onClick: () => void;
}) {
  const getIcon = () => {
    if (step.status === "completed") {
      return <CheckCircle className="h-5 w-5 text-green-500" />;
    }
    if (step.status === "skipped") {
      return <SkipForward className="h-5 w-5 text-zinc-400" />;
    }
    return (
      <Circle
        className={cn(
          "h-5 w-5",
          isActive ? "text-blue-500 fill-blue-500" : "text-zinc-300"
        )}
      />
    );
  };

  return (
    <button
      onClick={onClick}
      className={cn(
        "flex items-center gap-2 px-3 py-2 rounded-lg text-left w-full transition-colors",
        isActive
          ? "bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-300"
          : "hover:bg-zinc-50 dark:hover:bg-zinc-800"
      )}
    >
      {getIcon()}
      <div className="flex-1 min-w-0">
        <div
          className={cn(
            "text-sm font-medium truncate",
            step.status === "skipped" && "text-zinc-400"
          )}
        >
          {step.title}
        </div>
      </div>
    </button>
  );
}

export default function QuickSetupPage() {
  const router = useRouter();
  const [state, setState] = useState<QuickSetupState | null>(null);
  const [agentTypes, setAgentTypes] = useState<AgentTypeConfig[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isActioning, setIsActioning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const [stateData, typesData] = await Promise.all([
        getSetupState(),
        getAgentTypes(),
      ]);
      setState(stateData);
      setAgentTypes(typesData);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleComplete = async (data?: Record<string, unknown>) => {
    if (!state) return;
    try {
      setIsActioning(true);
      const newState = await completeStep(state.current_step, data);
      setState(newState);
    } catch (e) {
      setError(e instanceof Error ? e.message : "操作失败");
    } finally {
      setIsActioning(false);
    }
  };

  const handleSkip = async () => {
    if (!state) return;
    try {
      setIsActioning(true);
      const newState = await skipStep(state.current_step);
      setState(newState);
    } catch (e) {
      setError(e instanceof Error ? e.message : "操作失败");
    } finally {
      setIsActioning(false);
    }
  };

  const handleGoto = async (index: number) => {
    try {
      setIsActioning(true);
      const newState = await gotoStep(index);
      setState(newState);
    } catch (e) {
      setError(e instanceof Error ? e.message : "操作失败");
    } finally {
      setIsActioning(false);
    }
  };

  const handleReset = async () => {
    try {
      setIsActioning(true);
      const newState = await resetSetupState();
      setState(newState);
    } catch (e) {
      setError(e instanceof Error ? e.message : "重置失败");
    } finally {
      setIsActioning(false);
    }
  };

  const handlePrev = () => {
    if (state && state.current_step > 0) {
      handleGoto(state.current_step - 1);
    }
  };

  const handleNext = () => {
    if (state && state.current_step < state.steps.length - 1) {
      handleGoto(state.current_step + 1);
    }
  };

  if (isLoading) {
    return (
      <div className="flex h-[60vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-zinc-400" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-4">
        <PageHeader title="Quick Setup" description="快捷配置中心" />
        <div className="rounded-lg bg-red-50 p-4 text-red-600 dark:bg-red-900/20 dark:text-red-400 flex items-center gap-2">
          <AlertCircle className="h-5 w-5" />
          {error}
        </div>
        <Button onClick={loadData}>重试</Button>
      </div>
    );
  }

  if (!state) return null;

  const currentStep = state.steps[state.current_step];
  const StepComponent = STEP_COMPONENTS[currentStep.key];
  const completedCount = state.steps.filter((s) => s.status === "completed").length;
  const progress = (completedCount / state.steps.length) * 100;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <PageHeader
          title="Quick Setup"
          description="快捷配置中心 - 一站式完成系统配置"
        />
        <Button variant="outline" size="sm" onClick={handleReset}>
          <RotateCcw className="mr-2 h-4 w-4" />
          重新开始
        </Button>
      </div>

      {/* Progress */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-sm">
          <span className="text-zinc-500">
            步骤 {state.current_step + 1} / {state.steps.length}
          </span>
          <span className="text-zinc-500">
            已完成 {completedCount} / {state.steps.length}
          </span>
        </div>
        <Progress value={progress} className="h-2" />
      </div>

      {/* Main Content */}
      <div className="grid gap-6 lg:grid-cols-[240px_1fr]">
        {/* Step Sidebar */}
        <div className="hidden lg:block space-y-1">
          {state.steps.map((step) => (
            <StepIndicator
              key={step.index}
              step={step}
              isActive={step.index === state.current_step}
              onClick={() => handleGoto(step.index)}
            />
          ))}
        </div>

        {/* Step Content */}
        <div className="min-h-[400px]">
          {StepComponent ? (
            <StepComponent
              step={currentStep}
              state={state}
              agentTypes={agentTypes}
              onComplete={handleComplete}
              onSkip={handleSkip}
              onGoto={handleGoto}
              isLoading={isActioning}
            />
          ) : (
            <div className="flex h-full items-center justify-center text-zinc-400">
              步骤组件未找到: {currentStep.key}
            </div>
          )}
        </div>
      </div>

      {/* Navigation Buttons */}
      <div className="flex items-center justify-between border-t pt-4">
        <Button
          variant="outline"
          onClick={handlePrev}
          disabled={state.current_step === 0 || isActioning}
        >
          <ChevronLeft className="mr-2 h-4 w-4" />
          上一步
        </Button>
        <div className="flex items-center gap-2">
          {state.current_step < state.steps.length - 1 && (
            <Button
              variant="ghost"
              onClick={handleSkip}
              disabled={isActioning}
            >
              跳过
            </Button>
          )}
          {state.current_step < state.steps.length - 1 ? (
            <Button onClick={handleNext} disabled={isActioning}>
              下一步
              <ChevronRight className="ml-2 h-4 w-4" />
            </Button>
          ) : (
            <Button
              onClick={() => router.push("/admin")}
              disabled={isActioning}
            >
              完成配置
              <CheckCircle className="ml-2 h-4 w-4" />
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
