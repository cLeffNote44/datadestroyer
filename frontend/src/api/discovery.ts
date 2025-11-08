import apiClient from './client'
import { DiscoveryDashboard, GovernanceDashboard } from '../types/api'

export const discoveryApi = {
  // Get discovery dashboard
  getDashboard: async (): Promise<DiscoveryDashboard> => {
    const response = await apiClient.get<DiscoveryDashboard>('/discovery/dashboard/')
    return response.data
  },

  // Get governance dashboard
  getGovernanceDashboard: async (): Promise<GovernanceDashboard> => {
    const response = await apiClient.get<GovernanceDashboard>('/discovery/governance-dashboard/')
    return response.data
  },
}

export default discoveryApi
