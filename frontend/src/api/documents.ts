import apiClient from './client'
import { Document, PaginatedResponse } from '../types/api'

export const documentsApi = {
  // Get documents
  getDocuments: async (params?: Record<string, any>): Promise<PaginatedResponse<Document>> => {
    const response = await apiClient.get<PaginatedResponse<Document>>('/documents/', {
      params,
    })
    return response.data
  },

  // Get single document
  getDocument: async (id: string): Promise<Document> => {
    const response = await apiClient.get<Document>(`/documents/${id}/`)
    return response.data
  },

  // Upload document
  uploadDocument: async (formData: FormData): Promise<Document> => {
    const response = await apiClient.post<Document>('/documents/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },

  // Delete document
  deleteDocument: async (id: string): Promise<void> => {
    await apiClient.delete(`/documents/${id}/`)
  },

  // Update document
  updateDocument: async (id: string, data: Partial<Document>): Promise<Document> => {
    const response = await apiClient.patch<Document>(`/documents/${id}/`, data)
    return response.data
  },
}

export default documentsApi
