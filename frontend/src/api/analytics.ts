import apiClient from './client'
import {
  AnalyticsSnapshot,
  DataUsageMetric,
  PrivacyInsight,
  RetentionTimeline,
  PaginatedResponse,
} from '../types/api'

export const analyticsApi = {
  // Get analytics snapshots
  getSnapshots: async (
    params?: Record<string, any>
  ): Promise<PaginatedResponse<AnalyticsSnapshot>> => {
    const response = await apiClient.get<PaginatedResponse<AnalyticsSnapshot>>(
      '/analytics/snapshots/',
      { params }
    )
    return response.data
  },

  // Get latest snapshot
  getLatestSnapshot: async (): Promise<AnalyticsSnapshot | null> => {
    const response = await apiClient.get<PaginatedResponse<AnalyticsSnapshot>>(
      '/analytics/snapshots/',
      {
        params: { ordering: '-snapshot_date', limit: 1 },
      }
    )
    return response.data.results[0] || null
  },

  // Get usage metrics
  getMetrics: async (
    params?: Record<string, any>
  ): Promise<PaginatedResponse<DataUsageMetric>> => {
    const response = await apiClient.get<PaginatedResponse<DataUsageMetric>>(
      '/analytics/metrics/',
      { params }
    )
    return response.data
  },

  // Get privacy insights
  getInsights: async (
    params?: Record<string, any>
  ): Promise<PaginatedResponse<PrivacyInsight>> => {
    const response = await apiClient.get<PaginatedResponse<PrivacyInsight>>(
      '/analytics/insights/',
      { params }
    )
    return response.data
  },

  // Acknowledge insight
  acknowledgeInsight: async (id: string): Promise<PrivacyInsight> => {
    const response = await apiClient.patch<PrivacyInsight>(`/analytics/insights/${id}/`, {
      acknowledged: true,
    })
    return response.data
  },

  // Get retention timeline
  getRetentionTimeline: async (
    params?: Record<string, any>
  ): Promise<PaginatedResponse<RetentionTimeline>> => {
    const response = await apiClient.get<PaginatedResponse<RetentionTimeline>>(
      '/analytics/retention/',
      { params }
    )
    return response.data
  },

  // Get dashboard data
  getDashboard: async (): Promise<any> => {
    const response = await apiClient.get('/analytics/dashboard/')
    return response.data
  },
}

export default analyticsApi
