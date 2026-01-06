/**
 * 系统功能状态管理 Hook
 * 
 * 用于获取和管理系统各功能模块的启用状态，供前端控制导航和页面渲染。
 */

import { useEffect, useState } from 'react'

export interface FeatureStatus {
  enabled: boolean
  status: 'healthy' | 'degraded' | 'unhealthy' | 'disabled' | 'unknown'
  message?: string | null
  last_error?: string | null
}

export interface CrawlerFeature extends FeatureStatus {}

export interface MemoryFeature {
  enabled: boolean
  store_enabled: boolean
  fact_enabled: boolean
  graph_enabled: boolean
}

export interface NotificationFeature {
  wework: FeatureStatus
  webhook: FeatureStatus
}

export interface SystemFeatures {
  crawler: CrawlerFeature
  memory: MemoryFeature
  rerank: FeatureStatus
  notifications: NotificationFeature
}

const DEFAULT_FEATURES: SystemFeatures = {
  crawler: {
    enabled: false,
    status: 'unknown',
    message: null,
    last_error: null,
  },
  memory: {
    enabled: false,
    store_enabled: false,
    fact_enabled: false,
    graph_enabled: false,
  },
  rerank: {
    enabled: false,
    status: 'unknown',
    message: null,
    last_error: null,
  },
  notifications: {
    wework: {
      enabled: false,
      status: 'unknown',
      message: null,
      last_error: null,
    },
    webhook: {
      enabled: false,
      status: 'unknown',
      message: null,
      last_error: null,
    },
  },
}

/**
 * 获取系统功能状态
 */
export function useFeatures() {
  const [features, setFeatures] = useState<SystemFeatures>(DEFAULT_FEATURES)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchFeatures = async () => {
    try {
      setLoading(true)
      setError(null)

      const response = await fetch('/api/v1/system/features')
      
      if (!response.ok) {
        throw new Error(`获取功能状态失败: ${response.statusText}`)
      }

      const data = await response.json()
      setFeatures(data)
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '未知错误'
      setError(errorMessage)
      console.error('获取系统功能状态失败:', err)
      // 失败时保持默认值
      setFeatures(DEFAULT_FEATURES)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchFeatures()
  }, [])

  return {
    features,
    loading,
    error,
    refetch: fetchFeatures,
  }
}

/**
 * 检查功能是否可用
 */
export function isFeatureEnabled(
  features: SystemFeatures,
  feature: keyof SystemFeatures
): boolean {
  const featureData = features[feature]
  
  if (typeof featureData === 'object' && 'enabled' in featureData) {
    return featureData.enabled
  }
  
  return false
}

/**
 * 获取功能不可用时的提示信息
 */
export function getFeatureMessage(
  features: SystemFeatures,
  feature: keyof SystemFeatures
): string {
  const featureData = features[feature]
  
  if (typeof featureData === 'object' && 'message' in featureData) {
    return featureData.message || `${feature} 功能未启用`
  }
  
  return `${feature} 功能未启用`
}
