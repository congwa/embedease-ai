/**
 * Quick Setup 类型定义
 */

import type { SetupStep, QuickSetupState, AgentTypeConfig } from "@/lib/api/quick-setup";

export interface StepProps {
  step: SetupStep;
  state: QuickSetupState;
  agentTypes: AgentTypeConfig[];
  onComplete: (data?: Record<string, unknown>) => Promise<void>;
  onSkip: () => Promise<void>;
  onGoto: (index: number) => Promise<void>;
  isLoading: boolean;
}
