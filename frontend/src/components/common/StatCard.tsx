import { ArrowUpIcon, ArrowDownIcon } from '@heroicons/react/24/solid'

interface StatCardProps {
  title: string
  value: string | number
  change?: number
  icon?: React.ComponentType<{ className?: string }>
  trend?: 'up' | 'down'
  className?: string
}

export default function StatCard({ title, value, change, icon: Icon, trend, className = '' }: StatCardProps) {
  return (
    <div className={`card ${className}`}>
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>

          {change !== undefined && (
            <div
              className={`flex items-center mt-2 text-sm ${
                trend === 'up' ? 'text-green-600' : trend === 'down' ? 'text-red-600' : 'text-gray-600'
              }`}
            >
              {trend === 'up' ? (
                <ArrowUpIcon className="w-4 h-4 mr-1" />
              ) : trend === 'down' ? (
                <ArrowDownIcon className="w-4 h-4 mr-1" />
              ) : null}
              <span>{change > 0 ? '+' : ''}{change}%</span>
              <span className="text-gray-500 ml-1">vs last period</span>
            </div>
          )}
        </div>

        {Icon && (
          <div className="flex-shrink-0 w-12 h-12 bg-primary-100 rounded-lg flex items-center justify-center">
            <Icon className="w-6 h-6 text-primary-600" />
          </div>
        )}
      </div>
    </div>
  )
}
