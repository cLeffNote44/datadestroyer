import apiClient from './client'
import {
  ContentScan,
  PolicyViolation,
  ModerationDashboard,
  PaginatedResponse,
} from '../types/api'

export const moderationApi = {
  // Get content scans
  getScans: async (params?: Record<string, any>): Promise<PaginatedResponse<ContentScan>> => {
    const response = await apiClient.get<PaginatedResponse<ContentScan>>('/moderation/scans/', {
      params,
    })
    return response.data
  },

  // Get policy violations
  getViolations: async (
    params?: Record<string, any>
  ): Promise<PaginatedResponse<PolicyViolation>> => {
    const response = await apiClient.get<PaginatedResponse<PolicyViolation>>(
      '/moderation/violations/',
      { params }
    )
    return response.data
  },

  // Acknowledge violation
  acknowledgeViolation: async (id: string, notes?: string): Promise<PolicyViolation> => {
    const response = await apiClient.post<PolicyViolation>(
      `/moderation/violations/${id}/acknowledge/`,
      {
        resolution_notes: notes,
      }
    )
    return response.data
  },

  // Mark as false positive
  markFalsePositive: async (id: string, notes?: string): Promise<PolicyViolation> => {
    const response = await apiClient.post<PolicyViolation>(
      `/moderation/violations/${id}/false_positive/`,
      {
        resolution_notes: notes,
      }
    )
    return response.data
  },

  // Resolve violation
  resolveViolation: async (id: string, notes?: string): Promise<PolicyViolation> => {
    const response = await apiClient.post<PolicyViolation>(
      `/moderation/violations/${id}/resolve/`,
      {
        resolution_notes: notes,
      }
    )
    return response.data
  },

  // Get dashboard
  getDashboard: async (): Promise<ModerationDashboard> => {
    const response = await apiClient.get<ModerationDashboard>('/moderation/dashboard/')
    return response.data
  },

  // Scan content
  scanContent: async (text: string, contentType: string, objectId: string): Promise<ContentScan> => {
    const response = await apiClient.post<ContentScan>('/moderation/scan/', {
      text,
      content_type: contentType,
      object_id: objectId,
    })
    return response.data
  },
}

export default moderationApi
