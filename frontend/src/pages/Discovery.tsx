import { useQuery } from '@tanstack/react-query'
import { discoveryApi } from '../api/discovery'
import Card from '../components/common/Card'
import LoadingSpinner from '../components/common/LoadingSpinner'
import {
  CheckCircleIcon,
  XCircleIcon,
  MagnifyingGlassIcon,
} from '@heroicons/react/24/outline'

export default function Discovery() {
  const { data: dashboard, isLoading: dashboardLoading } = useQuery({
    queryKey: ['discovery', 'dashboard'],
    queryFn: () => discoveryApi.getDashboard(),
  })

  const { data: governance, isLoading: governanceLoading } = useQuery({
    queryKey: ['discovery', 'governance'],
    queryFn: () => discoveryApi.getGovernanceDashboard(),
  })

  const isLoading = dashboardLoading || governanceLoading

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
        <h1 className="text-3xl font-bold text-gray-900">Data Discovery</h1>
        <p className="text-gray-600 mt-1">
          Automatically discover and classify sensitive data across your systems
        </p>
      </div>

      {/* Stats Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card>
          <div className="text-center">
            <MagnifyingGlassIcon className="w-8 h-8 mx-auto text-primary-600 mb-2" />
            <p className="text-2xl font-bold text-gray-900">{dashboard?.total_assets || 0}</p>
            <p className="text-sm text-gray-600">Total Assets</p>
          </div>
        </Card>

        <Card>
          <div className="text-center">
            <div className="w-8 h-8 mx-auto bg-blue-100 rounded-full flex items-center justify-center mb-2">
              <span className="text-lg font-bold text-blue-600">PII</span>
            </div>
            <p className="text-2xl font-bold text-gray-900">{dashboard?.pii_count || 0}</p>
            <p className="text-sm text-gray-600">Personal Information</p>
          </div>
        </Card>

        <Card>
          <div className="text-center">
            <div className="w-8 h-8 mx-auto bg-red-100 rounded-full flex items-center justify-center mb-2">
              <span className="text-lg font-bold text-red-600">PHI</span>
            </div>
            <p className="text-2xl font-bold text-gray-900">{dashboard?.phi_count || 0}</p>
            <p className="text-sm text-gray-600">Health Information</p>
          </div>
        </Card>

        <Card>
          <div className="text-center">
            <div className="w-8 h-8 mx-auto bg-green-100 rounded-full flex items-center justify-center mb-2">
              <span className="text-lg font-bold text-green-600">$</span>
            </div>
            <p className="text-2xl font-bold text-gray-900">{dashboard?.financial_count || 0}</p>
            <p className="text-sm text-gray-600">Financial Data</p>
          </div>
        </Card>
      </div>

      {/* Classification Breakdown */}
      <Card title="Classification Breakdown" subtitle="Types of sensitive data discovered">
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          {Object.entries(dashboard?.classification_breakdown || {}).map(([type, count]) => (
            <div key={type} className="text-center p-4 bg-gray-50 rounded-lg">
              <p className="text-2xl font-bold text-gray-900">{count}</p>
              <p className="text-sm text-gray-600 mt-1">{type}</p>
            </div>
          ))}
        </div>
      </Card>

      {/* Compliance Status */}
      <Card title="Compliance Status" subtitle="Regulatory compliance checks">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <ComplianceCard
            name="GDPR"
            compliant={governance?.gdpr_compliant || false}
          />
          <ComplianceCard
            name="HIPAA"
            compliant={governance?.hipaa_compliant || false}
          />
          <ComplianceCard
            name="PCI-DSS"
            compliant={governance?.pci_dss_compliant || false}
          />
          <ComplianceCard
            name="SOC 2"
            compliant={governance?.soc2_compliant || false}
          />
        </div>
      </Card>

      {/* Governance Recommendations */}
      {governance?.recommendations && governance.recommendations.length > 0 && (
        <Card title="Governance Recommendations" subtitle="Actions to improve compliance">
          <div className="space-y-3">
            {governance.recommendations.map((rec, index) => (
              <div
                key={index}
                className={`p-4 rounded-lg border ${
                  rec.severity === 'critical'
                    ? 'bg-red-50 border-red-200'
                    : rec.severity === 'high'
                    ? 'bg-orange-50 border-orange-200'
                    : 'bg-yellow-50 border-yellow-200'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-medium text-gray-900 capitalize">{rec.type}</p>
                    <p className="text-sm text-gray-700 mt-1">{rec.message}</p>
                  </div>
                  <span className="text-xs font-medium px-2 py-1 rounded bg-white/50 capitalize">
                    {rec.severity}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Recent Discoveries */}
      {dashboard?.recent_discoveries && dashboard.recent_discoveries.length > 0 && (
        <Card title="Recent Discoveries" subtitle="Latest discovered data assets">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Asset Name
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Type
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Location
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Discovered
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {dashboard.recent_discoveries.map((asset) => (
                  <tr key={asset.id}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {asset.name}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {asset.asset_type}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {asset.location}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {new Date(asset.discovered_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  )
}

function ComplianceCard({ name, compliant }: { name: string; compliant: boolean }) {
  return (
    <div className={`p-4 rounded-lg border-2 ${compliant ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
      <div className="flex items-center justify-between">
        <h4 className="font-medium text-gray-900">{name}</h4>
        {compliant ? (
          <CheckCircleIcon className="w-6 h-6 text-green-600" />
        ) : (
          <XCircleIcon className="w-6 h-6 text-red-600" />
        )}
      </div>
      <p className={`text-sm mt-2 ${compliant ? 'text-green-700' : 'text-red-700'}`}>
        {compliant ? 'Compliant' : 'Non-compliant'}
      </p>
    </div>
  )
}
