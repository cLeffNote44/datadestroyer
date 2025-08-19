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
