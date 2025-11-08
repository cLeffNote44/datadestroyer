// API response types

export interface User {
  id: number
  username: string
  email: string
  first_name: string
  last_name: string
}

export interface AuthResponse {
  access: string
  refresh: string
  user: User
}

// Analytics types
export interface AnalyticsSnapshot {
  id: string
  user: number
  snapshot_date: string
  document_count: number
  message_count: number
  post_count: number
  storage_bytes: number
  privacy_score: number
  security_score: number
  total_violations: number
  critical_violations: number
  pending_violations: number
  risk_score: number
  discovered_assets: number
  classified_pii_count: number
  classified_phi_count: number
}

export interface PrivacyInsight {
  id: string
  user: number
  insight_type: 'alert' | 'recommendation' | 'tip'
  severity: 'low' | 'medium' | 'high' | 'critical'
  title: string
  message: string
  actionable: boolean
  acknowledged: boolean
  created_at: string
}

export interface DataUsageMetric {
  id: string
  user: number
  metric_type: string
  metric_name: string
  value: number
  timestamp: string
}

export interface RetentionTimeline {
  id: string
  user: number
  content_type: string
  scheduled_deletion_date: string
  item_count: number
  total_size_bytes: number
}

// Moderation types
export interface PolicyViolation {
  id: string
  scan: string
  pattern: string
  pattern_name: string
  severity: 'low' | 'medium' | 'high' | 'critical'
  matched_text: string
  context: string
  position_start: number
  position_end: number
  resolution_status: 'pending' | 'acknowledged' | 'resolved' | 'false_positive'
  resolution_notes: string
  acknowledged_at: string | null
  resolved_at: string | null
  created_at: string
}

export interface ContentScan {
  id: string
  content_type: string
  object_id: string
  scanned_text: string
  risk_score: number
  violations_count: number
  has_critical_violations: boolean
  is_quarantined: boolean
  scan_date: string
  violations: PolicyViolation[]
}

export interface ModerationDashboard {
  total_scans: number
  total_violations: number
  pending_violations: number
  critical_violations: number
  average_risk_score: number
  quarantined_items: number
  recent_scans: ContentScan[]
  violation_by_severity: {
    low: number
    medium: number
    high: number
    critical: number
  }
}

// Discovery types
export interface DataAsset {
  id: string
  asset_type: string
  name: string
  description: string
  location: string
  owner: string
  size_bytes: number
  discovered_at: string
  last_scanned: string
  classification_results: ClassificationResult[]
}

export interface ClassificationResult {
  id: string
  asset: string
  classification_type: 'PII' | 'PHI' | 'Financial' | 'IP' | 'Confidential'
  confidence_score: number
  details: Record<string, any>
  classified_at: string
}

export interface DiscoveryDashboard {
  total_assets: number
  classified_assets: number
  pii_count: number
  phi_count: number
  financial_count: number
  recent_discoveries: DataAsset[]
  classification_breakdown: {
    PII: number
    PHI: number
    Financial: number
    IP: number
    Confidential: number
  }
}

export interface GovernanceDashboard {
  compliance_score: number
  gdpr_compliant: boolean
  hipaa_compliant: boolean
  pci_dss_compliant: boolean
  soc2_compliant: boolean
  policy_violations: number
  retention_violations: number
  access_violations: number
  recommendations: Array<{
    type: string
    message: string
    severity: string
  }>
}

// Document types
export interface Document {
  id: string
  name: string
  file: string
  file_size: number
  file_type: string
  category: string | null
  description: string
  is_encrypted: boolean
  encryption_type: string
  file_hash: string
  password_protected: boolean
  retention_date: string | null
  is_quarantined: boolean
  uploaded_at: string
  updated_at: string
}

// Pagination
export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}
