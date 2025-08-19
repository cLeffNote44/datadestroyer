"""
Automated Governance Workflows for Data Discovery System

This module provides automated governance capabilities including:
- Auto-tagging based on classification results
- Policy enforcement based on data types
- Retention schedule automation
- Access control recommendations
- Compliance validation workflows
"""

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.core.mail import send_mail
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import json
import logging

from .models import (
    DataAsset, ClassificationResult, ClassificationRule, DataLineage,
    DiscoveryJob, DataDiscoveryInsight, RealTimeMonitor, MonitoringEvent
)


logger = logging.getLogger(__name__)


class GovernancePolicy:
    """Represents a governance policy with rules and actions"""
    
    def __init__(self, name: str, classification_types: List[str], 
                 confidence_threshold: float = 0.8):
        self.name = name
        self.classification_types = classification_types
        self.confidence_threshold = confidence_threshold
        self.actions = []
        self.tags = []
        self.retention_days = None
        self.access_level = None
        self.compliance_requirements = []
    
    def add_tag(self, tag: str):
        """Add tag to be applied when policy matches"""
        self.tags.append(tag)
        return self
    
    def set_retention(self, days: int):
        """Set retention period in days"""
        self.retention_days = days
        return self
    
    def set_access_level(self, level: str):
        """Set required access level (public, internal, confidential, restricted)"""
        self.access_level = level
        return self
    
    def add_compliance_requirement(self, requirement: str):
        """Add compliance requirement (e.g., GDPR, HIPAA, PCI-DSS)"""
        self.compliance_requirements.append(requirement)
        return self
    
    def matches(self, classification_result: ClassificationResult) -> bool:
        """Check if classification result matches this policy"""
        if classification_result.confidence_score < self.confidence_threshold:
            return False
        
        return classification_result.classification_type in self.classification_types


class AutoTaggingEngine:
    """Automatically tags data assets based on classification results"""
    
    def __init__(self):
        self.tag_mappings = {
            'PII': ['sensitive', 'personal-data', 'privacy-sensitive'],
            'PHI': ['medical', 'healthcare', 'hipaa-protected'],
            'FINANCIAL': ['financial', 'payment-data', 'pci-scope'],
            'INTELLECTUAL_PROPERTY': ['proprietary', 'confidential', 'trade-secret'],
            'CONFIDENTIAL': ['confidential', 'internal-only'],
            'PUBLIC': ['public', 'unrestricted'],
            'CREDENTIALS': ['security-critical', 'access-control', 'secret'],
            'BIOMETRIC': ['biometric', 'identity-data', 'highly-sensitive']
        }
    
    def generate_tags(self, classification_result: ClassificationResult) -> List[str]:
        """Generate appropriate tags for a classification result"""
        tags = []
        
        # Base tags from classification type
        base_tags = self.tag_mappings.get(classification_result.classification_type, [])
        tags.extend(base_tags)
        
        # Confidence-based tags
        if classification_result.confidence_score >= 0.95:
            tags.append('high-confidence')
        elif classification_result.confidence_score >= 0.8:
            tags.append('medium-confidence')
        else:
            tags.append('low-confidence')
        
        # Source-based tags
        if hasattr(classification_result.data_asset, 'source_type'):
            tags.append(f"source-{classification_result.data_asset.source_type}")
        
        # Data size tags
        if classification_result.data_asset.data_size:
            if classification_result.data_asset.data_size > 1024 * 1024:  # > 1MB
                tags.append('large-dataset')
            else:
                tags.append('small-dataset')
        
        return list(set(tags))  # Remove duplicates
    
    def apply_tags(self, data_asset: DataAsset, tags: List[str]):
        """Apply tags to a data asset"""
        existing_tags = data_asset.metadata.get('tags', []) if data_asset.metadata else []
        new_tags = list(set(existing_tags + tags))
        
        if not data_asset.metadata:
            data_asset.metadata = {}
        
        data_asset.metadata['tags'] = new_tags
        data_asset.metadata['auto_tagged_at'] = timezone.now().isoformat()
        data_asset.save()
        
        logger.info(f"Applied tags {tags} to asset {data_asset.id}")


class PolicyEnforcementEngine:
    """Enforces governance policies based on data classification"""
    
    def __init__(self):
        self.policies = self._load_default_policies()
    
    def _load_default_policies(self) -> List[GovernancePolicy]:
        """Load default governance policies"""
        policies = []
        
        # PII Protection Policy
        pii_policy = (GovernancePolicy("PII Protection", ["PII"], 0.8)
                     .add_tag("gdpr-scope")
                     .set_retention(2555)  # 7 years
                     .set_access_level("confidential")
                     .add_compliance_requirement("GDPR"))
        policies.append(pii_policy)
        
        # Healthcare Data Policy
        phi_policy = (GovernancePolicy("PHI Protection", ["PHI"], 0.9)
                     .add_tag("hipaa-protected")
                     .set_retention(3650)  # 10 years
                     .set_access_level("restricted")
                     .add_compliance_requirement("HIPAA"))
        policies.append(phi_policy)
        
        # Financial Data Policy
        fin_policy = (GovernancePolicy("Financial Protection", ["FINANCIAL"], 0.85)
                     .add_tag("pci-scope")
                     .set_retention(2555)  # 7 years
                     .set_access_level("confidential")
                     .add_compliance_requirement("PCI-DSS"))
        policies.append(fin_policy)
        
        # Credentials Policy
        cred_policy = (GovernancePolicy("Credentials Protection", ["CREDENTIALS"], 0.95)
                      .add_tag("security-critical")
                      .set_retention(90)  # Short retention for security
                      .set_access_level("restricted")
                      .add_compliance_requirement("SOC2"))
        policies.append(cred_policy)
        
        # Public Data Policy
        public_policy = (GovernancePolicy("Public Data", ["PUBLIC"], 0.7)
                        .add_tag("public-safe")
                        .set_retention(1825)  # 5 years
                        .set_access_level("public"))
        policies.append(public_policy)
        
        return policies
    
    def enforce_policies(self, classification_result: ClassificationResult):
        """Enforce applicable policies for a classification result"""
        applied_policies = []
        
        for policy in self.policies:
            if policy.matches(classification_result):
                self._apply_policy(classification_result.data_asset, policy)
                applied_policies.append(policy.name)
        
        # Update asset metadata with applied policies
        if not classification_result.data_asset.metadata:
            classification_result.data_asset.metadata = {}
        
        classification_result.data_asset.metadata['applied_policies'] = applied_policies
        classification_result.data_asset.metadata['policy_applied_at'] = timezone.now().isoformat()
        classification_result.data_asset.save()
        
        logger.info(f"Applied policies {applied_policies} to asset {classification_result.data_asset.id}")
    
    def _apply_policy(self, data_asset: DataAsset, policy: GovernancePolicy):
        """Apply a specific policy to a data asset"""
        if not data_asset.metadata:
            data_asset.metadata = {}
        
        # Apply tags
        if policy.tags:
            existing_tags = data_asset.metadata.get('tags', [])
            new_tags = list(set(existing_tags + policy.tags))
            data_asset.metadata['tags'] = new_tags
        
        # Set retention
        if policy.retention_days:
            retention_date = timezone.now() + timedelta(days=policy.retention_days)
            data_asset.metadata['retention_date'] = retention_date.isoformat()
        
        # Set access level
        if policy.access_level:
            data_asset.metadata['required_access_level'] = policy.access_level
        
        # Add compliance requirements
        if policy.compliance_requirements:
            existing_reqs = data_asset.metadata.get('compliance_requirements', [])
            new_reqs = list(set(existing_reqs + policy.compliance_requirements))
            data_asset.metadata['compliance_requirements'] = new_reqs


class RetentionAutomationEngine:
    """Automates data retention based on policies and schedules"""
    
    def __init__(self):
        self.retention_rules = self._load_retention_rules()
    
    def _load_retention_rules(self) -> Dict[str, int]:
        """Load retention rules mapping classification types to days"""
        return {
            'PII': 2555,      # 7 years for GDPR compliance
            'PHI': 3650,      # 10 years for healthcare
            'FINANCIAL': 2555, # 7 years for financial records
            'CREDENTIALS': 90,  # 90 days for security credentials
            'INTELLECTUAL_PROPERTY': 3650,  # 10 years for IP
            'CONFIDENTIAL': 1825,  # 5 years for confidential data
            'PUBLIC': 1825,   # 5 years for public data
            'BIOMETRIC': 3650  # 10 years for biometric data
        }
    
    def schedule_retention(self, data_asset: DataAsset, classification_type: str):
        """Schedule retention for a data asset based on classification"""
        retention_days = self.retention_rules.get(classification_type)
        
        if retention_days:
            retention_date = timezone.now() + timedelta(days=retention_days)
            
            if not data_asset.metadata:
                data_asset.metadata = {}
            
            data_asset.metadata['retention_date'] = retention_date.isoformat()
            data_asset.metadata['retention_scheduled_at'] = timezone.now().isoformat()
            data_asset.metadata['retention_reason'] = f"Auto-scheduled based on {classification_type} classification"
            data_asset.save()
            
            logger.info(f"Scheduled retention for asset {data_asset.id} until {retention_date}")
    
    def get_assets_for_retention(self) -> List[DataAsset]:
        """Get assets that are due for retention"""
        now = timezone.now()
        assets_for_retention = []
        
        for asset in DataAsset.objects.filter(is_active=True):
            if asset.metadata and 'retention_date' in asset.metadata:
                retention_date_str = asset.metadata['retention_date']
                retention_date = datetime.fromisoformat(retention_date_str.replace('Z', '+00:00'))
                
                if retention_date <= now:
                    assets_for_retention.append(asset)
        
        return assets_for_retention
    
    def execute_retention(self, data_asset: DataAsset, dry_run: bool = True) -> Dict[str, Any]:
        """Execute retention for a data asset"""
        result = {
            'asset_id': data_asset.id,
            'action_taken': None,
            'success': False,
            'message': '',
            'timestamp': timezone.now().isoformat()
        }
        
        try:
            if dry_run:
                result['action_taken'] = 'dry_run_validation'
                result['message'] = 'Asset validated for retention'
                result['success'] = True
            else:
                # Mark asset as inactive rather than deleting for audit trail
                data_asset.is_active = False
                data_asset.metadata['retention_executed_at'] = timezone.now().isoformat()
                data_asset.metadata['retention_status'] = 'executed'
                data_asset.save()
                
                result['action_taken'] = 'retention_executed'
                result['message'] = 'Asset marked for retention'
                result['success'] = True
                
                logger.info(f"Executed retention for asset {data_asset.id}")
        
        except Exception as e:
            result['message'] = f"Error during retention: {str(e)}"
            logger.error(f"Retention failed for asset {data_asset.id}: {str(e)}")
        
        return result


class AccessControlRecommendationEngine:
    """Generates access control recommendations based on data classification"""
    
    def __init__(self):
        self.access_matrix = self._build_access_matrix()
    
    def _build_access_matrix(self) -> Dict[str, Dict[str, Any]]:
        """Build access control matrix for different classification types"""
        return {
            'PII': {
                'minimum_access_level': 'confidential',
                'required_roles': ['data-protection-officer', 'privacy-analyst'],
                'audit_required': True,
                'encryption_required': True,
                'network_restrictions': ['internal_only'],
                'approval_workflow': 'privacy_team'
            },
            'PHI': {
                'minimum_access_level': 'restricted',
                'required_roles': ['healthcare-authorized', 'hipaa-trained'],
                'audit_required': True,
                'encryption_required': True,
                'network_restrictions': ['healthcare_network'],
                'approval_workflow': 'healthcare_compliance'
            },
            'FINANCIAL': {
                'minimum_access_level': 'confidential',
                'required_roles': ['finance-team', 'auditor'],
                'audit_required': True,
                'encryption_required': True,
                'network_restrictions': ['finance_network'],
                'approval_workflow': 'finance_approval'
            },
            'CREDENTIALS': {
                'minimum_access_level': 'restricted',
                'required_roles': ['security-admin', 'devops-lead'],
                'audit_required': True,
                'encryption_required': True,
                'network_restrictions': ['admin_network'],
                'approval_workflow': 'security_team'
            },
            'INTELLECTUAL_PROPERTY': {
                'minimum_access_level': 'confidential',
                'required_roles': ['legal-team', 'product-manager'],
                'audit_required': True,
                'encryption_required': True,
                'network_restrictions': ['internal_only'],
                'approval_workflow': 'legal_approval'
            },
            'PUBLIC': {
                'minimum_access_level': 'public',
                'required_roles': [],
                'audit_required': False,
                'encryption_required': False,
                'network_restrictions': [],
                'approval_workflow': None
            }
        }
    
    def generate_recommendations(self, classification_result: ClassificationResult) -> Dict[str, Any]:
        """Generate access control recommendations for classified data"""
        classification_type = classification_result.classification_type
        confidence = classification_result.confidence_score
        
        base_recommendations = self.access_matrix.get(classification_type, {})
        
        recommendations = {
            'asset_id': classification_result.data_asset.id,
            'classification_type': classification_type,
            'confidence_score': confidence,
            'recommendations': base_recommendations.copy(),
            'risk_score': self._calculate_risk_score(classification_result),
            'priority': self._determine_priority(classification_result),
            'generated_at': timezone.now().isoformat()
        }
        
        # Adjust recommendations based on confidence
        if confidence < 0.8:
            recommendations['recommendations']['manual_review_required'] = True
            recommendations['recommendations']['auto_apply'] = False
        else:
            recommendations['recommendations']['auto_apply'] = True
        
        # Add context-specific recommendations
        self._add_contextual_recommendations(recommendations, classification_result)
        
        return recommendations
    
    def _calculate_risk_score(self, classification_result: ClassificationResult) -> float:
        """Calculate risk score based on classification and context"""
        base_risk = {
            'PHI': 0.9,
            'PII': 0.8,
            'CREDENTIALS': 0.95,
            'FINANCIAL': 0.85,
            'INTELLECTUAL_PROPERTY': 0.7,
            'CONFIDENTIAL': 0.6,
            'PUBLIC': 0.1,
            'BIOMETRIC': 0.95
        }.get(classification_result.classification_type, 0.5)
        
        # Adjust based on confidence
        confidence_factor = classification_result.confidence_score
        
        # Adjust based on data size
        size_factor = 1.0
        if classification_result.data_asset.data_size:
            if classification_result.data_asset.data_size > 1024 * 1024:  # Large datasets are riskier
                size_factor = 1.2
        
        # Adjust based on access patterns
        access_factor = 1.0
        if classification_result.data_asset.metadata and 'access_frequency' in classification_result.data_asset.metadata:
            if classification_result.data_asset.metadata['access_frequency'] == 'high':
                access_factor = 1.1
        
        return min(base_risk * confidence_factor * size_factor * access_factor, 1.0)
    
    def _determine_priority(self, classification_result: ClassificationResult) -> str:
        """Determine implementation priority"""
        risk_score = self._calculate_risk_score(classification_result)
        confidence = classification_result.confidence_score
        
        if risk_score >= 0.8 and confidence >= 0.9:
            return 'critical'
        elif risk_score >= 0.6 and confidence >= 0.8:
            return 'high'
        elif risk_score >= 0.4:
            return 'medium'
        else:
            return 'low'
    
    def _add_contextual_recommendations(self, recommendations: Dict[str, Any], 
                                      classification_result: ClassificationResult):
        """Add context-specific recommendations"""
        data_asset = classification_result.data_asset
        
        # Location-based recommendations
        if data_asset.location and 'cloud' in data_asset.location.lower():
            recommendations['recommendations']['cloud_security_review'] = True
            recommendations['recommendations']['data_residency_check'] = True
        
        # Age-based recommendations
        if data_asset.created_at:
            age_days = (timezone.now() - data_asset.created_at).days
            if age_days > 365:
                recommendations['recommendations']['data_review_required'] = True
                recommendations['recommendations']['retention_review'] = True


class ComplianceValidationEngine:
    """Validates compliance with various regulatory frameworks"""
    
    def __init__(self):
        self.frameworks = self._load_compliance_frameworks()
    
    def _load_compliance_frameworks(self) -> Dict[str, Dict[str, Any]]:
        """Load compliance framework definitions"""
        return {
            'GDPR': {
                'applicable_types': ['PII'],
                'requirements': {
                    'right_to_deletion': True,
                    'right_to_rectification': True,
                    'right_to_portability': True,
                    'consent_tracking': True,
                    'purpose_limitation': True,
                    'data_minimization': True,
                    'retention_limits': True,
                    'encryption_at_rest': True,
                    'encryption_in_transit': True,
                    'audit_logging': True
                },
                'retention_limits': {'default': 2555}  # 7 years
            },
            'HIPAA': {
                'applicable_types': ['PHI'],
                'requirements': {
                    'access_control': True,
                    'audit_logging': True,
                    'encryption_at_rest': True,
                    'encryption_in_transit': True,
                    'user_authentication': True,
                    'transmission_security': True,
                    'data_integrity': True,
                    'minimum_necessary': True
                },
                'retention_limits': {'default': 3650}  # 10 years
            },
            'PCI_DSS': {
                'applicable_types': ['FINANCIAL'],
                'requirements': {
                    'network_security': True,
                    'encryption_at_rest': True,
                    'encryption_in_transit': True,
                    'access_control': True,
                    'monitoring': True,
                    'vulnerability_management': True,
                    'regular_testing': True
                },
                'retention_limits': {'default': 1095}  # 3 years
            },
            'SOC2': {
                'applicable_types': ['CREDENTIALS', 'CONFIDENTIAL'],
                'requirements': {
                    'security_policies': True,
                    'access_control': True,
                    'change_management': True,
                    'monitoring': True,
                    'incident_response': True,
                    'risk_assessment': True
                },
                'retention_limits': {'default': 2555}  # 7 years
            }
        }
    
    def validate_compliance(self, data_asset: DataAsset) -> Dict[str, Any]:
        """Validate compliance for a data asset"""
        validation_result = {
            'asset_id': data_asset.id,
            'validations': {},
            'overall_status': 'compliant',
            'violations': [],
            'recommendations': [],
            'validated_at': timezone.now().isoformat()
        }
        
        # Get classification results for this asset
        classifications = ClassificationResult.objects.filter(data_asset=data_asset)
        
        for classification in classifications:
            for framework_name, framework in self.frameworks.items():
                if classification.classification_type in framework['applicable_types']:
                    framework_validation = self._validate_framework_compliance(
                        data_asset, classification, framework_name, framework
                    )
                    validation_result['validations'][framework_name] = framework_validation
                    
                    if not framework_validation['compliant']:
                        validation_result['overall_status'] = 'non_compliant'
                        validation_result['violations'].extend(framework_validation['violations'])
                        validation_result['recommendations'].extend(framework_validation['recommendations'])
        
        return validation_result
    
    def _validate_framework_compliance(self, data_asset: DataAsset, 
                                     classification: ClassificationResult,
                                     framework_name: str, 
                                     framework: Dict[str, Any]) -> Dict[str, Any]:
        """Validate compliance with a specific framework"""
        validation = {
            'framework': framework_name,
            'compliant': True,
            'violations': [],
            'recommendations': [],
            'score': 0.0
        }
        
        requirements = framework['requirements']
        total_requirements = len(requirements)
        met_requirements = 0
        
        asset_metadata = data_asset.metadata or {}
        
        for requirement, required in requirements.items():
            if required:
                is_met = self._check_requirement(data_asset, requirement, asset_metadata)
                if is_met:
                    met_requirements += 1
                else:
                    validation['compliant'] = False
                    validation['violations'].append(f"Missing: {requirement}")
                    validation['recommendations'].append(
                        f"Implement {requirement} for {framework_name} compliance"
                    )
        
        validation['score'] = met_requirements / total_requirements if total_requirements > 0 else 0
        
        return validation
    
    def _check_requirement(self, data_asset: DataAsset, requirement: str, 
                          metadata: Dict[str, Any]) -> bool:
        """Check if a specific requirement is met"""
        requirement_checks = {
            'encryption_at_rest': lambda: metadata.get('encryption_at_rest', False),
            'encryption_in_transit': lambda: metadata.get('encryption_in_transit', False),
            'access_control': lambda: metadata.get('access_control_enabled', False),
            'audit_logging': lambda: metadata.get('audit_logging', False),
            'retention_limits': lambda: 'retention_date' in metadata,
            'user_authentication': lambda: metadata.get('authentication_required', False),
            'data_minimization': lambda: metadata.get('data_minimization_applied', False),
            'consent_tracking': lambda: metadata.get('consent_tracked', False),
            'purpose_limitation': lambda: metadata.get('purpose_documented', False),
            'network_security': lambda: metadata.get('network_security', False),
            'monitoring': lambda: metadata.get('monitoring_enabled', False),
            'vulnerability_management': lambda: metadata.get('vulnerability_scanning', False),
            'security_policies': lambda: metadata.get('security_policies_applied', False),
            'change_management': lambda: metadata.get('change_management', False),
            'incident_response': lambda: metadata.get('incident_response_plan', False),
            'risk_assessment': lambda: metadata.get('risk_assessment_completed', False)
        }
        
        check_function = requirement_checks.get(requirement)
        if check_function:
            return check_function()
        
        # Default to False for unknown requirements
        return False


class GovernanceOrchestrator:
    """Orchestrates all governance workflows"""
    
    def __init__(self):
        self.auto_tagger = AutoTaggingEngine()
        self.policy_enforcer = PolicyEnforcementEngine()
        self.retention_engine = RetentionAutomationEngine()
        self.access_recommender = AccessControlRecommendationEngine()
        self.compliance_validator = ComplianceValidationEngine()
    
    def process_classification_result(self, classification_result: ClassificationResult) -> Dict[str, Any]:
        """Process a classification result through all governance workflows"""
        result = {
            'classification_id': classification_result.id,
            'asset_id': classification_result.data_asset.id,
            'governance_actions': [],
            'status': 'success',
            'processed_at': timezone.now().isoformat()
        }
        
        try:
            with transaction.atomic():
                # Auto-tagging
                tags = self.auto_tagger.generate_tags(classification_result)
                self.auto_tagger.apply_tags(classification_result.data_asset, tags)
                result['governance_actions'].append(f"Applied tags: {', '.join(tags)}")
                
                # Policy enforcement
                self.policy_enforcer.enforce_policies(classification_result)
                result['governance_actions'].append("Applied governance policies")
                
                # Retention scheduling
                self.retention_engine.schedule_retention(
                    classification_result.data_asset, 
                    classification_result.classification_type
                )
                result['governance_actions'].append("Scheduled retention")
                
                # Access control recommendations
                access_recommendations = self.access_recommender.generate_recommendations(classification_result)
                
                # Store recommendations in asset metadata
                if not classification_result.data_asset.metadata:
                    classification_result.data_asset.metadata = {}
                
                classification_result.data_asset.metadata['access_recommendations'] = access_recommendations
                classification_result.data_asset.save()
                result['governance_actions'].append("Generated access recommendations")
                
                # Compliance validation
                compliance_result = self.compliance_validator.validate_compliance(classification_result.data_asset)
                classification_result.data_asset.metadata['compliance_status'] = compliance_result
                classification_result.data_asset.save()
                result['governance_actions'].append("Validated compliance")
                
                # Create governance insight
                self._create_governance_insight(classification_result, result)
                
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
            logger.error(f"Governance processing failed for classification {classification_result.id}: {str(e)}")
        
        return result
    
    def _create_governance_insight(self, classification_result: ClassificationResult, 
                                 governance_result: Dict[str, Any]):
        """Create a governance insight for tracking"""
        insight_data = {
            'type': 'governance_automation',
            'classification_result': classification_result.id,
            'actions_taken': governance_result['governance_actions'],
            'status': governance_result['status']
        }
        
        DataDiscoveryInsight.objects.create(
            asset=classification_result.data_asset,
            insight_type='governance',
            title=f"Automated governance applied to {classification_result.classification_type} data",
            description=f"Applied automated governance actions: {', '.join(governance_result['governance_actions'])}",
            severity='info',
            metadata=insight_data,
            is_resolved=True
        )
    
    def run_retention_sweep(self, dry_run: bool = True) -> Dict[str, Any]:
        """Run retention sweep across all eligible assets"""
        sweep_result = {
            'sweep_id': f"retention_sweep_{timezone.now().strftime('%Y%m%d_%H%M%S')}",
            'dry_run': dry_run,
            'processed_assets': [],
            'total_processed': 0,
            'total_retained': 0,
            'errors': [],
            'started_at': timezone.now().isoformat()
        }
        
        assets_for_retention = self.retention_engine.get_assets_for_retention()
        
        for asset in assets_for_retention:
            try:
                retention_result = self.retention_engine.execute_retention(asset, dry_run)
                sweep_result['processed_assets'].append(retention_result)
                sweep_result['total_processed'] += 1
                
                if retention_result['success'] and not dry_run:
                    sweep_result['total_retained'] += 1
                    
            except Exception as e:
                error_info = {
                    'asset_id': asset.id,
                    'error': str(e),
                    'timestamp': timezone.now().isoformat()
                }
                sweep_result['errors'].append(error_info)
                logger.error(f"Retention sweep error for asset {asset.id}: {str(e)}")
        
        sweep_result['completed_at'] = timezone.now().isoformat()
        
        # Create insight for sweep results
        if sweep_result['total_processed'] > 0:
            DataDiscoveryInsight.objects.create(
                insight_type='governance',
                title=f"Retention sweep {'simulation' if dry_run else 'execution'} completed",
                description=f"Processed {sweep_result['total_processed']} assets, {'would retain' if dry_run else 'retained'} {sweep_result['total_retained']} assets",
                severity='info' if len(sweep_result['errors']) == 0 else 'warning',
                metadata=sweep_result,
                is_resolved=True
            )
        
        return sweep_result
    
    def generate_compliance_report(self, framework: Optional[str] = None) -> Dict[str, Any]:
        """Generate comprehensive compliance report"""
        report = {
            'report_id': f"compliance_report_{timezone.now().strftime('%Y%m%d_%H%M%S')}",
            'framework_filter': framework,
            'generated_at': timezone.now().isoformat(),
            'summary': {
                'total_assets': 0,
                'compliant_assets': 0,
                'non_compliant_assets': 0,
                'compliance_score': 0.0
            },
            'framework_results': {},
            'top_violations': [],
            'recommendations': []
        }
        
        # Get all active assets with classifications
        active_assets = DataAsset.objects.filter(is_active=True)
        classified_assets = [asset for asset in active_assets 
                           if ClassificationResult.objects.filter(data_asset=asset).exists()]
        
        report['summary']['total_assets'] = len(classified_assets)
        
        compliance_scores = []
        violation_counts = {}
        
        for asset in classified_assets:
            asset_compliance = self.compliance_validator.validate_compliance(asset)
            
            if asset_compliance['overall_status'] == 'compliant':
                report['summary']['compliant_assets'] += 1
            else:
                report['summary']['non_compliant_assets'] += 1
            
            # Aggregate framework results
            for fw_name, fw_result in asset_compliance['validations'].items():
                if framework and fw_name != framework:
                    continue
                    
                if fw_name not in report['framework_results']:
                    report['framework_results'][fw_name] = {
                        'total_assets': 0,
                        'compliant_assets': 0,
                        'average_score': 0.0,
                        'common_violations': []
                    }
                
                report['framework_results'][fw_name]['total_assets'] += 1
                if fw_result['compliant']:
                    report['framework_results'][fw_name]['compliant_assets'] += 1
                
                compliance_scores.append(fw_result['score'])
                
                # Count violations
                for violation in fw_result['violations']:
                    violation_counts[violation] = violation_counts.get(violation, 0) + 1
        
        # Calculate overall compliance score
        if compliance_scores:
            report['summary']['compliance_score'] = sum(compliance_scores) / len(compliance_scores)
        
        # Calculate framework averages
        for fw_name, fw_data in report['framework_results'].items():
            if fw_data['total_assets'] > 0:
                fw_data['compliance_percentage'] = (fw_data['compliant_assets'] / fw_data['total_assets']) * 100
        
        # Top violations
        sorted_violations = sorted(violation_counts.items(), key=lambda x: x[1], reverse=True)
        report['top_violations'] = [{'violation': v[0], 'count': v[1]} for v in sorted_violations[:10]]
        
        # Generate recommendations
        report['recommendations'] = self._generate_compliance_recommendations(report)
        
        return report
    
    def _generate_compliance_recommendations(self, report: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on compliance report"""
        recommendations = []
        
        # Overall compliance
        if report['summary']['compliance_score'] < 0.8:
            recommendations.append("Overall compliance score is below 80%. Consider implementing a comprehensive compliance improvement program.")
        
        # Framework-specific recommendations
        for fw_name, fw_data in report['framework_results'].items():
            compliance_pct = fw_data.get('compliance_percentage', 0)
            if compliance_pct < 70:
                recommendations.append(f"{fw_name}: Compliance rate is {compliance_pct:.1f}%. Immediate attention required.")
            elif compliance_pct < 90:
                recommendations.append(f"{fw_name}: Compliance rate is {compliance_pct:.1f}%. Consider targeted improvements.")
        
        # Top violation recommendations
        top_violations = report['top_violations'][:3]
        for violation_data in top_violations:
            violation = violation_data['violation']
            count = violation_data['count']
            recommendations.append(f"Address '{violation}' - affects {count} assets.")
        
        return recommendations
