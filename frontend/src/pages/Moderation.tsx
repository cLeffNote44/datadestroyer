import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { moderationApi } from '../api/moderation'
import { useUIStore } from '../stores/uiStore'
import Card from '../components/common/Card'
import LoadingSpinner from '../components/common/LoadingSpinner'
import { ExclamationTriangleIcon, CheckCircleIcon } from '@heroicons/react/24/outline'

export default function Moderation() {
  const [selectedFilter, setSelectedFilter] = useState<string>('all')
  const queryClient = useQueryClient()
  const addNotification = useUIStore((state) => state.addNotification)

  const { data: violations, isLoading } = useQuery({
    queryKey: ['moderation', 'violations', selectedFilter],
    queryFn: () =>
      moderationApi.getViolations({
        resolution_status: selectedFilter === 'all' ? undefined : selectedFilter,
        ordering: '-created_at',
      }),
  })

  const acknowledgeMutation = useMutation({
    mutationFn: (id: string) => moderationApi.acknowledgeViolation(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['moderation'] })
      addNotification({
        type: 'success',
        title: 'Violation Acknowledged',
        message: 'The violation has been acknowledged successfully',
      })
    },
  })

  const resolveMutation = useMutation({
    mutationFn: (id: string) => moderationApi.resolveViolation(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['moderation'] })
      addNotification({
        type: 'success',
        title: 'Violation Resolved',
        message: 'The violation has been marked as resolved',
      })
    },
  })

  const markFalsePositiveMutation = useMutation({
    mutationFn: (id: string) => moderationApi.markFalsePositive(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['moderation'] })
      addNotification({
        type: 'success',
        title: 'Marked as False Positive',
        message: 'The violation has been marked as a false positive',
      })
    },
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Moderation Center</h1>
        <p className="text-gray-600 mt-1">Review and manage policy violations</p>
      </div>

      {/* Filters */}
      <div className="flex space-x-2">
        {['all', 'pending', 'acknowledged', 'resolved', 'false_positive'].map((filter) => (
          <button
            key={filter}
            onClick={() => setSelectedFilter(filter)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              selectedFilter === filter
                ? 'bg-primary-600 text-white'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            {filter.replace('_', ' ').charAt(0).toUpperCase() + filter.slice(1).replace('_', ' ')}
          </button>
        ))}
      </div>

      {/* Violations List */}
      <Card title="Policy Violations" subtitle={`${violations?.count || 0} violations found`}>
        {violations?.results && violations.results.length > 0 ? (
          <div className="space-y-4">
            {violations.results.map((violation) => (
              <div
                key={violation.id}
                className={`border rounded-lg p-4 ${
                  violation.severity === 'critical'
                    ? 'border-red-300 bg-red-50'
                    : violation.severity === 'high'
                    ? 'border-orange-300 bg-orange-50'
                    : violation.severity === 'medium'
                    ? 'border-yellow-300 bg-yellow-50'
                    : 'border-blue-300 bg-blue-50'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-2">
                      <ExclamationTriangleIcon
                        className={`w-5 h-5 ${
                          violation.severity === 'critical'
                            ? 'text-red-600'
                            : violation.severity === 'high'
                            ? 'text-orange-600'
                            : violation.severity === 'medium'
                            ? 'text-yellow-600'
                            : 'text-blue-600'
                        }`}
                      />
                      <h4 className="font-medium text-gray-900">{violation.pattern_name}</h4>
                      <span
                        className={`px-2 py-1 text-xs font-medium rounded ${
                          violation.severity === 'critical'
                            ? 'bg-red-200 text-red-800'
                            : violation.severity === 'high'
                            ? 'bg-orange-200 text-orange-800'
                            : violation.severity === 'medium'
                            ? 'bg-yellow-200 text-yellow-800'
                            : 'bg-blue-200 text-blue-800'
                        }`}
                      >
                        {violation.severity}
                      </span>
                    </div>

                    <p className="text-sm text-gray-700 mt-2">
                      <span className="font-medium">Matched: </span>
                      <code className="bg-gray-900 text-gray-100 px-2 py-1 rounded text-xs">
                        {violation.matched_text}
                      </code>
                    </p>

                    <p className="text-sm text-gray-600 mt-1">
                      <span className="font-medium">Context: </span>
                      {violation.context}
                    </p>

                    <p className="text-xs text-gray-500 mt-2">
                      Status: <span className="capitalize">{violation.resolution_status.replace('_', ' ')}</span> •
                      Created {new Date(violation.created_at).toLocaleDateString()}
                    </p>
                  </div>

                  {violation.resolution_status === 'pending' && (
                    <div className="flex flex-col space-y-2 ml-4">
                      <button
                        onClick={() => acknowledgeMutation.mutate(violation.id)}
                        className="px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700"
                      >
                        Acknowledge
                      </button>
                      <button
                        onClick={() => resolveMutation.mutate(violation.id)}
                        className="px-3 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700"
                      >
                        Resolve
                      </button>
                      <button
                        onClick={() => markFalsePositiveMutation.mutate(violation.id)}
                        className="px-3 py-1 text-xs bg-gray-600 text-white rounded hover:bg-gray-700"
                      >
                        False Positive
                      </button>
                    </div>
                  )}

                  {violation.resolution_status === 'resolved' && (
                    <CheckCircleIcon className="w-6 h-6 text-green-600 ml-4" />
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-12 text-gray-500">
            <ExclamationTriangleIcon className="w-12 h-12 mx-auto mb-2 text-gray-400" />
            <p>No violations found</p>
            <p className="text-sm">All clear! No policy violations detected.</p>
          </div>
        )}
      </Card>
    </div>
  )
}
