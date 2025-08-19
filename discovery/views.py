from django.shortcuts import render
from django.db.models import Count, Avg, Q, F, Sum
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from datetime import datetime, timedelta

from rest_framework import generics, viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from .models import (
    DataAsset, ClassificationRule, DiscoveryJob, DataLineage,
    ClassificationResult, DataDiscoveryInsight, RealTimeMonitor,
    MonitoringEvent, DataClassification, SensitivityLevel
)
from .scanner import data_discovery_scanner
from .classification_engine import classification_engine
from .governance import GovernanceOrchestrator


class DiscoveryDashboardView(generics.GenericAPIView):
    """Dashboard view with discovery system overview"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get discovery dashboard data"""
        # Get time ranges
        now = timezone.now()
        last_24h = now - timedelta(hours=24)
        last_7d = now - timedelta(days=7)
        last_30d = now - timedelta(days=30)
        
        # Asset statistics
        total_assets = DataAsset.objects.filter(is_active=True).count()
        recent_assets = DataAsset.objects.filter(
            is_active=True,
            discovered_at__gte=last_24h
        ).count()
        
        # Classification statistics
        classification_stats = dict(
            DataAsset.objects.filter(is_active=True)
            .values('primary_classification')
            .annotate(count=Count('id'))
            .values_list('primary_classification', 'count')
        )
        
        sensitivity_stats = dict(
            DataAsset.objects.filter(is_active=True)
            .values('sensitivity_level')
            .annotate(count=Count('id'))
            .values_list('sensitivity_level', 'count')
        )
        
        # Discovery job statistics
        recent_jobs = DiscoveryJob.objects.filter(
            created_at__gte=last_7d
        ).count()
        
        successful_jobs = DiscoveryJob.objects.filter(
            created_at__gte=last_7d,
            status='completed'
        ).count()
        
        # Real-time monitoring statistics
        active_monitors = RealTimeMonitor.objects.filter(is_active=True).count()
        recent_events = MonitoringEvent.objects.filter(
            created_at__gte=last_24h
        ).count()
        
        recent_alerts = MonitoringEvent.objects.filter(
            created_at__gte=last_24h,
            triggered_alert=True
        ).count()
        
        # Recent insights
        recent_insights = DataDiscoveryInsight.objects.filter(
            created_at__gte=last_7d,
            is_resolved=False
        ).order_by('-created_at')[:10]
        
        # Top classifications by volume
        top_classifications = list(
            DataAsset.objects.filter(is_active=True)
            .exclude(primary_classification='internal')
            .values('primary_classification')
            .annotate(count=Count('id'))
            .order_by('-count')[:5]
        )
        
        return Response({
            'summary': {
                'total_assets': total_assets,
                'recent_assets_24h': recent_assets,
                'discovery_jobs_7d': recent_jobs,
                'successful_jobs_7d': successful_jobs,
                'active_monitors': active_monitors,
                'recent_events_24h': recent_events,
                'recent_alerts_24h': recent_alerts
            },
            'classification_distribution': classification_stats,
            'sensitivity_distribution': sensitivity_stats,
            'top_classifications': top_classifications,
            'system_health': {
                'classification_engine_status': 'active',
                'monitoring_status': 'active' if active_monitors > 0 else 'inactive',
                'last_scan_time': DiscoveryJob.objects.filter(
                    status='completed'
                ).order_by('-completed_at').first().completed_at if DiscoveryJob.objects.filter(
                    status='completed'
                ).exists() else None
            }
        })


class GovernanceDashboardView(generics.GenericAPIView):
    """Governance and compliance metrics dashboard"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get governance dashboard data"""
        framework = request.GET.get('framework')
        
        # Initialize governance orchestrator
        orchestrator = GovernanceOrchestrator()
        
        # Get assets with governance policies applied
        assets_with_governance = DataAsset.objects.filter(
            metadata__applied_policies__isnull=False
        ).distinct().count()
        
        total_assets = DataAsset.objects.filter(is_active=True).count()
        governance_coverage = assets_with_governance / total_assets if total_assets > 0 else 0
        
        # Get policy distribution
        policy_distribution = {}
        assets_with_policies = DataAsset.objects.filter(
            is_active=True,
            metadata__applied_policies__isnull=False
        )
        
        for asset in assets_with_policies:
            if asset.metadata and 'applied_policies' in asset.metadata:
                for policy in asset.metadata['applied_policies']:
                    policy_distribution[policy] = policy_distribution.get(policy, 0) + 1
        
        # Get retention metrics
        assets_with_retention = DataAsset.objects.filter(
            is_active=True,
            metadata__retention_date__isnull=False
        ).count()
        retention_coverage = assets_with_retention / total_assets if total_assets > 0 else 0
        
        # Get assets due for retention
        assets_due_for_retention = len(orchestrator.retention_engine.get_assets_for_retention())
        
        # Get classification type coverage
        classification_types = ClassificationResult.objects.values_list(
            'classification_type', flat=True
        ).distinct()
        
        type_coverage = {}
        for cls_type in classification_types:
            assets_with_type = DataAsset.objects.filter(
                is_active=True,
                classificationresult__classification_type=cls_type
            ).distinct().count()
            assets_with_governance_by_type = DataAsset.objects.filter(
                is_active=True,
                classificationresult__classification_type=cls_type,
                metadata__applied_policies__isnull=False
            ).distinct().count()
            
            coverage = assets_with_governance_by_type / assets_with_type if assets_with_type > 0 else 0
            type_coverage[cls_type] = {
                'total_assets': assets_with_type,
                'governed_assets': assets_with_governance_by_type,
                'coverage': coverage
            }
        
        # Generate compliance report summary
        try:
            compliance_report = orchestrator.generate_compliance_report(framework=framework)
        except Exception as e:
            # Fallback compliance data
            compliance_report = {
                'summary': {
                    'compliance_score': 0.0,
                    'compliant_assets': 0,
                    'non_compliant_assets': 0
                },
                'framework_results': {},
                'top_violations': [],
                'recommendations': []
            }
        
        # Get access control recommendations by priority
        access_recommendations = {}
        high_priority_assets = 0
        medium_priority_assets = 0
        low_priority_assets = 0
        
        for asset in DataAsset.objects.filter(
            is_active=True,
            metadata__access_recommendations__isnull=False
        ):
            if (asset.metadata and 
                'access_recommendations' in asset.metadata and 
                'priority' in asset.metadata['access_recommendations']):
                
                priority = asset.metadata['access_recommendations']['priority']
                access_recommendations[priority] = access_recommendations.get(priority, 0) + 1
                
                if priority in ['critical', 'high']:
                    high_priority_assets += 1
                elif priority == 'medium':
                    medium_priority_assets += 1
                else:
                    low_priority_assets += 1
        
        return Response({
            'governance_overview': {
                'total_assets': total_assets,
                'assets_with_governance': assets_with_governance,
                'governance_coverage': governance_coverage,
                'assets_with_retention': assets_with_retention,
                'retention_coverage': retention_coverage,
                'assets_due_for_retention': assets_due_for_retention
            },
            'policy_distribution': policy_distribution,
            'classification_governance': type_coverage,
            'access_control': {
                'recommendations_by_priority': access_recommendations,
                'high_priority_assets': high_priority_assets,
                'medium_priority_assets': medium_priority_assets,
                'low_priority_assets': low_priority_assets
            },
            'compliance': {
                'overall_score': compliance_report['summary']['compliance_score'],
                'compliant_assets': compliance_report['summary']['compliant_assets'],
                'non_compliant_assets': compliance_report['summary']['non_compliant_assets'],
                'framework_scores': {name: data.get('compliance_percentage', 0) 
                                   for name, data in compliance_report['framework_results'].items()},
                'top_violations': compliance_report['top_violations'][:5] if compliance_report['top_violations'] else [],
                'recommendations': compliance_report['recommendations'][:3] if compliance_report['recommendations'] else []
            },
            'timestamp': timezone.now().isoformat()
        })
