"""
Serializers for the discovery system REST API
"""

from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType

from .models import (
    DataAsset, ClassificationRule, DiscoveryJob, DataLineage,
    ClassificationResult, DataDiscoveryInsight, RealTimeMonitor,
    MonitoringEvent
)


class DataAssetSerializer(serializers.ModelSerializer):
    """Serializer for DataAsset model"""
    content_type_name = serializers.CharField(source='content_type.model', read_only=True)
    discovered_by_username = serializers.CharField(source='discovered_by.username', read_only=True)
    classification_display = serializers.CharField(source='get_primary_classification_display', read_only=True)
    sensitivity_display = serializers.CharField(source='get_sensitivity_level_display', read_only=True)
    classification_score = serializers.SerializerMethodField()
    
    class Meta:
        model = DataAsset
        fields = [
            'id', 'name', 'description', 'content_type', 'content_type_name',
            'object_id', 'primary_classification', 'classification_display',
            'secondary_classifications', 'sensitivity_level', 'sensitivity_display',
            'discovered_at', 'last_scanned', 'discovered_by', 'discovered_by_username',
            'size_bytes', 'file_path', 'database_table', 'retention_policy',
            'compliance_tags', 'access_level', 'metadata', 'is_active',
            'classification_score'
        ]
        read_only_fields = ['id', 'discovered_at', 'last_scanned']
    
    def get_classification_score(self, obj):
        """Get the classification risk score"""
        return obj.get_classification_score()


class ClassificationRuleSerializer(serializers.ModelSerializer):
    """Serializer for ClassificationRule model"""
    rule_type_display = serializers.CharField(source='get_rule_type_display', read_only=True)
    target_classification_display = serializers.CharField(source='get_target_classification_display', read_only=True)
    target_sensitivity_display = serializers.CharField(source='get_target_sensitivity_display', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    accuracy_metrics = serializers.SerializerMethodField()
    
    class Meta:
        model = ClassificationRule
        fields = [
            'id', 'name', 'description', 'rule_type', 'rule_type_display',
            'pattern', 'confidence_threshold', 'target_classification',
            'target_classification_display', 'target_sensitivity',
            'target_sensitivity_display', 'priority', 'is_active',
            'created_at', 'updated_at', 'created_by', 'created_by_username',
            'true_positives', 'false_positives', 'false_negatives',
            'accuracy_metrics'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_accuracy_metrics(self, obj):
        """Get accuracy metrics for the rule"""
        return obj.get_accuracy_metrics()


class ClassificationRuleCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating ClassificationRule"""
    
    class Meta:
        model = ClassificationRule
        fields = [
            'name', 'description', 'rule_type', 'pattern',
            'confidence_threshold', 'target_classification',
            'target_sensitivity', 'priority', 'is_active'
        ]


class DiscoveryJobSerializer(serializers.ModelSerializer):
    """Serializer for DiscoveryJob model"""
    job_type_display = serializers.CharField(source='get_job_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    duration = serializers.SerializerMethodField()
    discovery_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = DiscoveryJob
        fields = [
            'id', 'name', 'description', 'job_type', 'job_type_display',
            'target_apps', 'target_models', 'target_paths', 'schedule_cron',
            'is_scheduled', 'status', 'status_display', 'created_at',
            'started_at', 'completed_at', 'created_by', 'created_by_username',
            'assets_discovered', 'assets_classified', 'errors_encountered',
            'configuration', 'results_summary', 'error_log',
            'duration', 'discovery_rate'
        ]
        read_only_fields = [
            'id', 'created_at', 'started_at', 'completed_at',
            'assets_discovered', 'assets_classified', 'errors_encountered',
            'results_summary', 'error_log'
        ]
    
    def get_duration(self, obj):
        """Get job duration in seconds"""
        return obj.get_duration()
    
    def get_discovery_rate(self, obj):
        """Get assets discovered per minute"""
        return obj.get_discovery_rate()


class DiscoveryJobCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating DiscoveryJob"""
    
    class Meta:
        model = DiscoveryJob
        fields = [
            'name', 'description', 'job_type', 'target_apps',
            'target_models', 'target_paths', 'schedule_cron',
            'is_scheduled', 'configuration'
        ]


class DataLineageSerializer(serializers.ModelSerializer):
    """Serializer for DataLineage model"""
    source_asset_name = serializers.CharField(source='source_asset.name', read_only=True)
    target_asset_name = serializers.CharField(source='target_asset.name', read_only=True)
    relationship_type_display = serializers.CharField(source='get_relationship_type_display', read_only=True)
    
    class Meta:
        model = DataLineage
        fields = [
            'id', 'source_asset', 'source_asset_name', 'target_asset',
            'target_asset_name', 'relationship_type', 'relationship_type_display',
            'transformation_logic', 'created_at', 'last_verified',
            'confidence_score', 'impact_score'
        ]
        read_only_fields = ['id', 'created_at', 'last_verified']


class ClassificationResultSerializer(serializers.ModelSerializer):
    """Serializer for ClassificationResult model"""
    data_asset_name = serializers.CharField(source='data_asset.name', read_only=True)
    rule_name = serializers.CharField(source='classification_rule.name', read_only=True)
    predicted_classification_display = serializers.CharField(source='get_predicted_classification_display', read_only=True)
    predicted_sensitivity_display = serializers.CharField(source='get_predicted_sensitivity_display', read_only=True)
    confidence_level_display = serializers.CharField(source='get_confidence_level_display', read_only=True)
    validated_by_username = serializers.CharField(source='validated_by.username', read_only=True)
    
    class Meta:
        model = ClassificationResult
        fields = [
            'id', 'data_asset', 'data_asset_name', 'classification_rule',
            'rule_name', 'discovery_job', 'predicted_classification',
            'predicted_classification_display', 'predicted_sensitivity',
            'predicted_sensitivity_display', 'confidence_score',
            'confidence_level', 'confidence_level_display',
            'matched_patterns', 'context_information', 'is_validated',
            'is_correct', 'validated_by', 'validated_by_username',
            'validated_at', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class DataDiscoveryInsightSerializer(serializers.ModelSerializer):
    """Serializer for DataDiscoveryInsight model"""
    insight_type_display = serializers.CharField(source='get_insight_type_display', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    resolved_by_username = serializers.CharField(source='resolved_by.username', read_only=True)
    related_assets_count = serializers.SerializerMethodField()
    
    class Meta:
        model = DataDiscoveryInsight
        fields = [
            'id', 'title', 'description', 'insight_type', 'insight_type_display',
            'severity', 'severity_display', 'insight_data', 'recommendations',
            'created_at', 'is_resolved', 'resolved_at', 'resolved_by',
            'resolved_by_username', 'related_assets_count'
        ]
        read_only_fields = ['id', 'created_at', 'resolved_at', 'resolved_by']
    
    def get_related_assets_count(self, obj):
        """Get count of related assets"""
        return obj.related_assets.count()


class RealTimeMonitorSerializer(serializers.ModelSerializer):
    """Serializer for RealTimeMonitor model"""
    monitor_type_display = serializers.CharField(source='get_monitor_type_display', read_only=True)
    alert_threshold_display = serializers.CharField(source='get_alert_threshold_display', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = RealTimeMonitor
        fields = [
            'id', 'name', 'description', 'monitor_type', 'monitor_type_display',
            'target_specification', 'auto_classify', 'alert_on_sensitive',
            'alert_threshold', 'alert_threshold_display', 'notification_email',
            'is_active', 'created_at', 'created_by', 'created_by_username',
            'items_monitored', 'alerts_generated', 'last_activity'
        ]
        read_only_fields = [
            'id', 'created_at', 'items_monitored', 'alerts_generated',
            'last_activity'
        ]


class RealTimeMonitorCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating RealTimeMonitor"""
    
    class Meta:
        model = RealTimeMonitor
        fields = [
            'name', 'description', 'monitor_type', 'target_specification',
            'auto_classify', 'alert_on_sensitive', 'alert_threshold',
            'notification_email', 'is_active'
        ]


class MonitoringEventSerializer(serializers.ModelSerializer):
    """Serializer for MonitoringEvent model"""
    monitor_name = serializers.CharField(source='monitor.name', read_only=True)
    data_asset_name = serializers.CharField(source='data_asset.name', read_only=True)
    
    class Meta:
        model = MonitoringEvent
        fields = [
            'id', 'monitor', 'monitor_name', 'event_type', 'event_data',
            'data_asset', 'data_asset_name', 'was_classified',
            'triggered_alert', 'created_at', 'processed_at'
        ]
        read_only_fields = ['id', 'created_at', 'processed_at']
