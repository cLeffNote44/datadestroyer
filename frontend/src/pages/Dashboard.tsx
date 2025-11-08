import { useQuery } from '@tanstack/react-query'
import {
  DocumentTextIcon,
  ExclamationTriangleIcon,
  MagnifyingGlassIcon,
  ShieldCheckIcon,
} from '@heroicons/react/24/outline'
import { analyticsApi } from '../api/analytics'
import { moderationApi } from '../api/moderation'
import { discoveryApi } from '../api/discovery'
import StatCard from '../components/common/StatCard'
import Card from '../components/common/Card'
import LoadingSpinner from '../components/common/LoadingSpinner'
import PrivacyScoreGauge from '../components/charts/PrivacyScoreGauge'
import RecentInsights from '../components/charts/RecentInsights'

export default function Dashboard() {
  // Fetch dashboard data
  const { data: snapshot, isLoading: snapshotLoading } = useQuery({
    queryKey: ['analytics', 'snapshot'],
    queryFn: () => analyticsApi.getLatestSnapshot(),
  })

  const { data: moderationData, isLoading: moderationLoading } = useQuery({
    queryKey: ['moderation', 'dashboard'],
    queryFn: () => moderationApi.getDashboard(),
  })

  const { data: discoveryData, isLoading: discoveryLoading } = useQuery({
    queryKey: ['discovery', 'dashboard'],
    queryFn: () => discoveryApi.getDashboard(),
  })

  const { data: insights } = useQuery({
    queryKey: ['analytics', 'insights'],
    queryFn: () => analyticsApi.getInsights({ ordering: '-created_at', limit: 5 }),
  })

  const isLoading = snapshotLoading || moderationLoading || discoveryLoading

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
        <h1 className="text-3xl font-bold text-gray-900">Privacy Dashboard</h1>
        <p className="text-gray-600 mt-1">Overview of your data governance and privacy status</p>
      </div>

      {/* Privacy Score */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-1" title="Privacy Score">
          <PrivacyScoreGauge score={snapshot?.privacy_score || 0} />
          <p className="text-sm text-gray-600 text-center mt-4">
            Based on violations, data classification, and compliance
          </p>
        </Card>

        <Card className="lg:col-span-2" title="Recent Insights">
          <RecentInsights insights={insights?.results || []} />
        </Card>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Total Documents"
          value={snapshot?.document_count || 0}
          icon={DocumentTextIcon}
        />

        <StatCard
          title="Policy Violations"
          value={moderationData?.pending_violations || 0}
          icon={ExclamationTriangleIcon}
          trend={moderationData?.pending_violations > 0 ? 'down' : undefined}
        />

        <StatCard
          title="Discovered Assets"
          value={discoveryData?.total_assets || 0}
          icon={MagnifyingGlassIcon}
        />

        <StatCard
          title="Security Score"
          value={snapshot?.security_score || 0}
          icon={ShieldCheckIcon}
        />
      </div>

      {/* Data Classification Overview */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="Data Classification" subtitle="Discovered sensitive data types">
          <div className="space-y-4">
            <ClassificationBar
              label="PII (Personal Information)"
              count={discoveryData?.pii_count || 0}
              total={discoveryData?.total_assets || 1}
              color="blue"
            />
            <ClassificationBar
              label="PHI (Protected Health Info)"
              count={discoveryData?.phi_count || 0}
              total={discoveryData?.total_assets || 1}
              color="red"
            />
            <ClassificationBar
              label="Financial Data"
              count={discoveryData?.financial_count || 0}
              total={discoveryData?.total_assets || 1}
              color="green"
            />
          </div>
        </Card>

        <Card title="Violation Severity" subtitle="Breakdown by severity level">
          <div className="space-y-4">
            <SeverityBar
              label="Critical"
              count={moderationData?.violation_by_severity?.critical || 0}
              color="red"
            />
            <SeverityBar
              label="High"
              count={moderationData?.violation_by_severity?.high || 0}
              color="orange"
            />
            <SeverityBar
              label="Medium"
              count={moderationData?.violation_by_severity?.medium || 0}
              color="yellow"
            />
            <SeverityBar
              label="Low"
              count={moderationData?.violation_by_severity?.low || 0}
              color="blue"
            />
          </div>
        </Card>
      </div>

      {/* Storage & Activity */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card title="Storage Usage">
          <div className="text-center">
            <p className="text-3xl font-bold text-gray-900">
              {formatBytes(snapshot?.storage_bytes || 0)}
            </p>
            <p className="text-sm text-gray-600 mt-1">Total storage used</p>
          </div>
        </Card>

        <Card title="Messages">
          <div className="text-center">
            <p className="text-3xl font-bold text-gray-900">{snapshot?.message_count || 0}</p>
            <p className="text-sm text-gray-600 mt-1">Total messages</p>
          </div>
        </Card>

        <Card title="Forum Posts">
          <div className="text-center">
            <p className="text-3xl font-bold text-gray-900">{snapshot?.post_count || 0}</p>
            <p className="text-sm text-gray-600 mt-1">Total posts</p>
          </div>
        </Card>
      </div>
    </div>
  )
}

// Helper Components
function ClassificationBar({
  label,
  count,
  total,
  color,
}: {
  label: string
  count: number
  total: number
  color: string
}) {
  const percentage = (count / total) * 100

  const colorClasses = {
    blue: 'bg-blue-500',
    red: 'bg-red-500',
    green: 'bg-green-500',
  }

  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-gray-700">{label}</span>
        <span className="text-gray-900 font-medium">{count}</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div
          className={`${colorClasses[color as keyof typeof colorClasses]} h-2 rounded-full transition-all duration-300`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  )
}

function SeverityBar({ label, count, color }: { label: string; count: number; color: string }) {
  const colorClasses = {
    red: 'bg-red-500',
    orange: 'bg-orange-500',
    yellow: 'bg-yellow-500',
    blue: 'bg-blue-500',
  }

  return (
    <div className="flex items-center space-x-3">
      <div className="flex-1">
        <div className="flex justify-between text-sm mb-1">
          <span className="text-gray-700">{label}</span>
          <span className="text-gray-900 font-medium">{count}</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className={`${colorClasses[color as keyof typeof colorClasses]} h-2 rounded-full`}
            style={{ width: count > 0 ? '100%' : '0%' }}
          />
        </div>
      </div>
    </div>
  )
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
}
