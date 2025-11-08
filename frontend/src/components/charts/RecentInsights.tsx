import {
  ExclamationTriangleIcon,
  LightBulbIcon,
  InformationCircleIcon,
} from '@heroicons/react/24/outline'
import { PrivacyInsight } from '../../types/api'

interface RecentInsightsProps {
  insights: PrivacyInsight[]
}

const insightIcons = {
  alert: ExclamationTriangleIcon,
  recommendation: LightBulbIcon,
  tip: InformationCircleIcon,
}

const severityColors = {
  critical: 'bg-red-50 border-red-200 text-red-800',
  high: 'bg-orange-50 border-orange-200 text-orange-800',
  medium: 'bg-yellow-50 border-yellow-200 text-yellow-800',
  low: 'bg-blue-50 border-blue-200 text-blue-800',
}

export default function RecentInsights({ insights }: RecentInsightsProps) {
  if (insights.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <LightBulbIcon className="w-12 h-12 mx-auto mb-2 text-gray-400" />
        <p>No insights available</p>
        <p className="text-sm">Check back later for privacy recommendations</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {insights.map((insight) => {
        const Icon = insightIcons[insight.insight_type]
        const colorClass = severityColors[insight.severity]

        return (
          <div
            key={insight.id}
            className={`${colorClass} border rounded-lg p-4 flex items-start space-x-3`}
          >
            <Icon className="w-5 h-5 flex-shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
              <h4 className="font-medium text-sm">{insight.title}</h4>
              <p className="text-sm mt-1 opacity-90">{insight.message}</p>
              <div className="flex items-center space-x-2 mt-2 text-xs opacity-75">
                <span className="capitalize">{insight.insight_type}</span>
                <span>•</span>
                <span>{new Date(insight.created_at).toLocaleDateString()}</span>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
