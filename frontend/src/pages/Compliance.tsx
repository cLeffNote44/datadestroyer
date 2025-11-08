import { useQuery } from '@tanstack/react-query'
import { discoveryApi } from '../api/discovery'
import { analyticsApi } from '../api/analytics'
import Card from '../components/common/Card'
import LoadingSpinner from '../components/common/LoadingSpinner'
import {
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
} from '@heroicons/react/24/outline'

export default function Compliance() {
  const { data: governance, isLoading: governanceLoading } = useQuery({
    queryKey: ['discovery', 'governance'],
    queryFn: () => discoveryApi.getGovernanceDashboard(),
  })

  const { data: retentionTimeline, isLoading: retentionLoading } = useQuery({
    queryKey: ['analytics', 'retention'],
    queryFn: () => analyticsApi.getRetentionTimeline(),
  })

  const isLoading = governanceLoading || retentionLoading

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
        <h1 className="text-3xl font-bold text-gray-900">Compliance Reports</h1>
        <p className="text-gray-600 mt-1">
          Monitor compliance status and regulatory requirements
        </p>
      </div>

      {/* Compliance Score */}
      <Card title="Overall Compliance Score">
        <div className="text-center py-6">
          <div className="inline-flex items-center justify-center w-32 h-32 rounded-full bg-gradient-to-br from-primary-500 to-primary-700 mb-4">
            <span className="text-5xl font-bold text-white">
              {Math.round(governance?.compliance_score || 0)}
            </span>
          </div>
          <p className="text-lg font-medium text-gray-900">Compliance Score</p>
          <p className="text-sm text-gray-600">Based on regulatory requirements</p>
        </div>
      </Card>

      {/* Regulatory Compliance */}
      <Card title="Regulatory Compliance" subtitle="Status for major regulations">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <ComplianceStatusCard
            name="GDPR"
            description="General Data Protection Regulation"
            compliant={governance?.gdpr_compliant || false}
          />
          <ComplianceStatusCard
            name="HIPAA"
            description="Health Insurance Portability"
            compliant={governance?.hipaa_compliant || false}
          />
          <ComplianceStatusCard
            name="PCI-DSS"
            description="Payment Card Industry Data Security"
            compliant={governance?.pci_dss_compliant || false}
          />
          <ComplianceStatusCard
            name="SOC 2"
            description="Service Organization Control"
            compliant={governance?.soc2_compliant || false}
          />
        </div>
      </Card>

      {/* Violations Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <div className="text-center">
            <XCircleIcon className="w-10 h-10 mx-auto text-red-600 mb-2" />
            <p className="text-3xl font-bold text-gray-900">
              {governance?.policy_violations || 0}
            </p>
            <p className="text-sm text-gray-600 mt-1">Policy Violations</p>
          </div>
        </Card>

        <Card>
          <div className="text-center">
            <ClockIcon className="w-10 h-10 mx-auto text-orange-600 mb-2" />
            <p className="text-3xl font-bold text-gray-900">
              {governance?.retention_violations || 0}
            </p>
            <p className="text-sm text-gray-600 mt-1">Retention Violations</p>
          </div>
        </Card>

        <Card>
          <div className="text-center">
            <XCircleIcon className="w-10 h-10 mx-auto text-yellow-600 mb-2" />
            <p className="text-3xl font-bold text-gray-900">
              {governance?.access_violations || 0}
            </p>
            <p className="text-sm text-gray-600 mt-1">Access Violations</p>
          </div>
        </Card>
      </div>

      {/* Retention Timeline */}
      {retentionTimeline?.results && retentionTimeline.results.length > 0 && (
        <Card title="Retention Timeline" subtitle="Upcoming scheduled deletions">
          <div className="space-y-3">
            {retentionTimeline.results.map((item) => (
              <div
                key={item.id}
                className="flex items-center justify-between p-4 bg-gray-50 rounded-lg border border-gray-200"
              >
                <div>
                  <p className="font-medium text-gray-900 capitalize">
                    {item.content_type.replace('_', ' ')}
                  </p>
                  <p className="text-sm text-gray-600 mt-1">
                    {item.item_count} items • {formatBytes(item.total_size_bytes)}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-medium text-gray-900">
                    {new Date(item.scheduled_deletion_date).toLocaleDateString()}
                  </p>
                  <p className="text-xs text-gray-500">Deletion date</p>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Recommendations */}
      {governance?.recommendations && governance.recommendations.length > 0 && (
        <Card title="Compliance Recommendations" subtitle="Actions to improve compliance">
          <div className="space-y-3">
            {governance.recommendations.map((rec, index) => (
              <div
                key={index}
                className={`p-4 rounded-lg border ${getSeverityClass(rec.severity)}`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h4 className="font-medium text-gray-900 capitalize">{rec.type}</h4>
                    <p className="text-sm text-gray-700 mt-1">{rec.message}</p>
                  </div>
                  <span className="text-xs font-medium px-3 py-1 rounded-full bg-white/60 capitalize">
                    {rec.severity}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  )
}

function ComplianceStatusCard({
  name,
  description,
  compliant,
}: {
  name: string
  description: string
  compliant: boolean
}) {
  return (
    <div className={`p-6 rounded-lg border-2 ${compliant ? 'bg-green-50 border-green-300' : 'bg-red-50 border-red-300'}`}>
      <div className="flex items-center justify-between mb-3">
        {compliant ? (
          <CheckCircleIcon className="w-8 h-8 text-green-600" />
        ) : (
          <XCircleIcon className="w-8 h-8 text-red-600" />
        )}
      </div>
      <h3 className="text-lg font-bold text-gray-900">{name}</h3>
      <p className="text-xs text-gray-600 mt-1">{description}</p>
      <div className="mt-4">
        <span
          className={`inline-block px-3 py-1 rounded-full text-xs font-medium ${
            compliant
              ? 'bg-green-200 text-green-800'
              : 'bg-red-200 text-red-800'
          }`}
        >
          {compliant ? 'Compliant' : 'Non-compliant'}
        </span>
      </div>
    </div>
  )
}

function getSeverityClass(severity: string): string {
  const classes = {
    critical: 'bg-red-50 border-red-300',
    high: 'bg-orange-50 border-orange-300',
    medium: 'bg-yellow-50 border-yellow-300',
    low: 'bg-blue-50 border-blue-300',
  }
  return classes[severity as keyof typeof classes] || classes.low
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
}
