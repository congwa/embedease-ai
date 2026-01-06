/**
 * 功能守卫组件
 * 
 * 用于包裹需要特定功能启用才能访问的页面或组件。
 * 如果功能未启用，显示友好的提示信息。
 */

import { ReactNode } from 'react'
import { AlertCircle } from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { useRouter } from 'next/navigation'
import { SystemFeatures, getFeatureMessage, isFeatureEnabled } from '@/hooks/use-features'

interface FeatureGuardProps {
  children: ReactNode
  features: SystemFeatures
  requiredFeature: keyof SystemFeatures
  fallback?: ReactNode
  redirectTo?: string
}

export function FeatureGuard({
  children,
  features,
  requiredFeature,
  fallback,
  redirectTo = '/admin',
}: FeatureGuardProps) {
  const router = useRouter()
  const enabled = isFeatureEnabled(features, requiredFeature)

  if (enabled) {
    return <>{children}</>
  }

  if (fallback) {
    return <>{fallback}</>
  }

  const message = getFeatureMessage(features, requiredFeature)

  return (
    <div className="flex items-center justify-center min-h-[400px] p-8">
      <div className="max-w-md w-full">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>功能未启用</AlertTitle>
          <AlertDescription className="mt-2">
            <p className="mb-4">{message}</p>
            <p className="text-sm text-muted-foreground mb-4">
              请联系系统管理员在环境配置中启用此功能。
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => router.push(redirectTo)}
            >
              返回管理后台
            </Button>
          </AlertDescription>
        </Alert>
      </div>
    </div>
  )
}

/**
 * 功能禁用提示组件（轻量级）
 */
export function FeatureDisabledHint({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-dashed border-muted-foreground/25 bg-muted/50 p-8 text-center">
      <AlertCircle className="mx-auto h-12 w-12 text-muted-foreground/50 mb-4" />
      <h3 className="text-lg font-medium mb-2">功能未启用</h3>
      <p className="text-sm text-muted-foreground max-w-md mx-auto">
        {message}
      </p>
    </div>
  )
}
