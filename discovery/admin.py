from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count

from .models import (
    DataAsset, ClassificationRule, DiscoveryJob, DataLineage,
    ClassificationResult, DataDiscoveryInsight, RealTimeMonitor,
    MonitoringEvent
)


@admin.register(DataAsset)
class DataAssetAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'content_type', 'primary_classification', 'sensitivity_level',
        'discovered_at', 'last_scanned', 'is_active'
    ]
    list_filter = [
        'primary_classification', 'sensitivity_level', 'is_active',
        'discovered_at', 'last_scanned', 'content_type'
    ]
    search_fields = ['name', 'description']
    readonly_fields = [
        'discovered_at', 'last_scanned', 'content_type', 'object_id',
        'classification_score_display'
    ]
    
    def classification_score_display(self, obj):
        """Display classification risk score"""
        score = obj.get_classification_score()
        if score >= 0.8:
            color = 'red'
        elif score >= 0.6:
            color = 'orange' 
        else:
            color = 'green'
        return format_html(
            '<span style="color: {};">{:.2%}</span>',
            color, score
        )
    classification_score_display.short_description = 'Risk Score'


@admin.register(ClassificationRule)
class ClassificationRuleAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'rule_type', 'target_classification', 'target_sensitivity',
        'priority', 'is_active'
    ]
    list_filter = [
        'rule_type', 'target_classification', 'target_sensitivity',
        'is_active', 'created_at'
    ]
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(DiscoveryJob)
class DiscoveryJobAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'job_type', 'status', 'created_at', 'assets_discovered'
    ]
    list_filter = ['status', 'job_type', 'is_scheduled', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'started_at', 'completed_at']


@admin.register(DataLineage)
class DataLineageAdmin(admin.ModelAdmin):
    list_display = [
        'source_asset', 'target_asset', 'relationship_type',
        'confidence_score', 'created_at'
    ]
    list_filter = ['relationship_type', 'confidence_score', 'created_at']
    readonly_fields = ['created_at', 'last_verified']


@admin.register(ClassificationResult)
class ClassificationResultAdmin(admin.ModelAdmin):
    list_display = [
        'data_asset', 'classification_rule', 'predicted_classification',
        'confidence_score', 'is_validated'
    ]
    list_filter = [
        'predicted_classification', 'confidence_level',
        'is_validated', 'created_at'
    ]
    readonly_fields = ['created_at']


@admin.register(DataDiscoveryInsight)
class DataDiscoveryInsightAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'insight_type', 'severity', 'is_resolved', 'created_at'
    ]
    list_filter = ['insight_type', 'severity', 'is_resolved', 'created_at']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at']


@admin.register(RealTimeMonitor)
class RealTimeMonitorAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'monitor_type', 'is_active', 'items_monitored',
        'alerts_generated'
    ]
    list_filter = ['monitor_type', 'is_active', 'alert_threshold', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'items_monitored', 'alerts_generated']


@admin.register(MonitoringEvent)
class MonitoringEventAdmin(admin.ModelAdmin):
    list_display = [
        'monitor', 'event_type', 'was_classified',
        'triggered_alert', 'created_at'
    ]
    list_filter = ['event_type', 'was_classified', 'triggered_alert', 'created_at']
    readonly_fields = ['created_at', 'processed_at']
