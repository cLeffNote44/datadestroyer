"""
Real-time Data Discovery Signals

This module implements real-time monitoring for data changes using Django signals.
It automatically discovers and classifies new data as it's created or modified.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from django.db.models.signals import post_save, post_delete, pre_delete
from django.contrib.contenttypes.models import ContentType
from django.dispatch import receiver
from django.db import transaction
from django.conf import settings
from django.apps import apps

from .models import (
    DataAsset, RealTimeMonitor, MonitoringEvent, DataDiscoveryInsight,
    DiscoveryJob, DataClassification, SensitivityLevel, ClassificationResult
)
from .scanner import data_discovery_scanner
from .classification_engine import classification_engine, ContentContext

logger = logging.getLogger(__name__)


class RealTimeDiscoverySignals:
    """Handles real-time data discovery through Django signals"""
    
    def __init__(self):
        self.enabled_monitors = {}
        self.processed_objects = set()  # Cache to avoid duplicate processing
        self._load_active_monitors()
    
    def _load_active_monitors(self):
        """Load active real-time monitors from database"""
        try:
            monitors = RealTimeMonitor.objects.filter(is_active=True)
            self.enabled_monitors = {}
            
            for monitor in monitors:
                if monitor.monitor_type == 'model_changes':
                    target_spec = monitor.target_specification
                    
                    # Parse target specification
                    if 'apps' in target_spec:
                        for app_name in target_spec['apps']:
                            if app_name not in self.enabled_monitors:
                                self.enabled_monitors[app_name] = []
                            self.enabled_monitors[app_name].append(monitor)
                    
                    if 'models' in target_spec:
                        for model_spec in target_spec['models']:
                            app_label = model_spec.get('app')
                            if app_label and app_label not in self.enabled_monitors:
                                self.enabled_monitors[app_label] = []
                            if app_label:
                                self.enabled_monitors[app_label].append(monitor)
            
            logger.info(f"Loaded {len(self.enabled_monitors)} real-time monitoring configurations")
            
        except Exception as e:
            logger.error(f"Error loading real-time monitors: {e}")
            self.enabled_monitors = {}
    
    def should_monitor_model(self, model_class) -> bool:
        """Check if a model should be monitored based on active monitors"""
        app_label = model_class._meta.app_label
        model_name = model_class._meta.model_name
        
        # Skip system models
        if app_label in ['admin', 'auth', 'contenttypes', 'sessions', 'axes']:
            return False
        
        # Skip our own discovery models to avoid recursion
        if app_label == 'discovery':
            return False
        
        # Check if app is monitored
        if app_label in self.enabled_monitors:
            return True
        
        # Check if this specific model is monitored
        for monitors in self.enabled_monitors.values():
            for monitor in monitors:
                target_spec = monitor.target_specification
                if 'models' in target_spec:
                    for model_spec in target_spec['models']:
                        if (model_spec.get('app') == app_label and 
                            model_spec.get('model') == model_name):
                            return True
        
        return False
    
    def get_applicable_monitors(self, model_class) -> list:
        """Get monitors applicable to a specific model"""
        app_label = model_class._meta.app_label
        model_name = model_class._meta.model_name
        applicable_monitors = []
        
        # Get monitors for the app
        if app_label in self.enabled_monitors:
            applicable_monitors.extend(self.enabled_monitors[app_label])
        
        # Get monitors for specific models
        for monitors in self.enabled_monitors.values():
            for monitor in monitors:
                target_spec = monitor.target_specification
                if 'models' in target_spec:
                    for model_spec in target_spec['models']:
                        if (model_spec.get('app') == app_label and 
                            model_spec.get('model') == model_name):
                            if monitor not in applicable_monitors:
                                applicable_monitors.append(monitor)
        
        return applicable_monitors
    
    @transaction.atomic
    def handle_model_created(self, sender, instance, created, **kwargs):
        """Handle model instance creation"""
        if not created or not self.should_monitor_model(sender):
            return
        
        # Avoid duplicate processing
        instance_key = f"{sender._meta.label}:{instance.pk}"
        if instance_key in self.processed_objects:
            return
        
        try:
            self.processed_objects.add(instance_key)
            
            # Get applicable monitors
            monitors = self.get_applicable_monitors(sender)
            
            for monitor in monitors:
                try:
                    self._process_model_change(
                        monitor=monitor,
                        instance=instance,
                        event_type='created',
                        sender=sender
                    )
                except Exception as e:
                    logger.error(f"Error processing model change for monitor {monitor.name}: {e}")
            
        except Exception as e:
            logger.error(f"Error handling model creation for {sender}: {e}")
        finally:
            # Clean up processed objects cache periodically
            if len(self.processed_objects) > 1000:
                self.processed_objects.clear()
    
    @transaction.atomic
    def handle_model_updated(self, sender, instance, created, **kwargs):
        """Handle model instance updates"""
        if created or not self.should_monitor_model(sender):
            return
        
        # Avoid duplicate processing
        instance_key = f"{sender._meta.label}:{instance.pk}:updated"
        if instance_key in self.processed_objects:
            return
        
        try:
            self.processed_objects.add(instance_key)
            
            # Get applicable monitors
            monitors = self.get_applicable_monitors(sender)
            
            for monitor in monitors:
                try:
                    self._process_model_change(
                        monitor=monitor,
                        instance=instance,
                        event_type='updated',
                        sender=sender
                    )
                except Exception as e:
                    logger.error(f"Error processing model update for monitor {monitor.name}: {e}")
            
        except Exception as e:
            logger.error(f"Error handling model update for {sender}: {e}")
    
    def _process_model_change(self, monitor, instance, event_type, sender):
        """Process a model change event"""
        try:
            # Create monitoring event
            event = MonitoringEvent.objects.create(
                monitor=monitor,
                event_type=f"model_{event_type}",
                event_data={
                    'app_label': sender._meta.app_label,
                    'model_name': sender._meta.model_name,
                    'object_id': str(instance.pk),
                    'timestamp': datetime.now().isoformat()
                }
            )
            
            # Update monitor activity tracking
            monitor.items_monitored += 1
            monitor.last_activity = datetime.now()
            
            # Check if we should discover/classify this object
            if monitor.auto_classify:
                data_asset = self._discover_or_update_asset(instance, sender)
                
                if data_asset:
                    event.data_asset = data_asset
                    event.was_classified = True
                    
                    # Check if classification triggered any alerts
                    if self._check_alert_conditions(data_asset, monitor):
                        event.triggered_alert = True
                        monitor.alerts_generated += 1
                        self._send_alert(monitor, data_asset, event_type)
            
            event.processed_at = datetime.now()
            event.save()
            monitor.save()
            
        except Exception as e:
            logger.error(f"Error processing model change: {e}")
            raise
    
    def _discover_or_update_asset(self, instance, sender) -> Optional['DataAsset']:
        """Discover or update a data asset for the given instance"""
        try:
            content_type = ContentType.objects.get_for_model(sender)
            
            # Check if asset already exists
            asset = DataAsset.objects.filter(
                content_type=content_type,
                object_id=instance.pk
            ).first()
            
            if asset:
                # Update existing asset
                asset.last_scanned = datetime.now()
                asset.save(update_fields=['last_scanned'])
                
                # Re-classify if needed
                if hasattr(instance, 'updated_at') or hasattr(instance, 'modified'):
                    self._classify_asset_content(asset, instance)
                
                return asset
            
            else:
                # Create new asset using the scanner
                app_name = sender._meta.app_label
                model_name = sender._meta.model_name
                
                asset_discovered = data_discovery_scanner._discover_model_instance(
                    instance, content_type, app_name, model_name
                )
                
                if asset_discovered:
                    # Get the newly created asset
                    asset = DataAsset.objects.filter(
                        content_type=content_type,
                        object_id=instance.pk
                    ).first()
                    
                    if asset:
                        # Classify the new asset
                        self._classify_asset_content(asset, instance)
                        return asset
            
        except Exception as e:
            logger.error(f"Error discovering/updating asset for {instance}: {e}")
        
        return None
    
    def _classify_asset_content(self, asset, instance):
        """Classify content of a data asset"""
        try:
            # Extract text content
            content_text = data_discovery_scanner._extract_text_content(instance)
            
            if not content_text or not content_text.strip():
                return
            
            # Create context
            context = ContentContext(
                content_type=str(asset.content_type),
                model_name=asset.metadata.get('model_name'),
                app_name=asset.metadata.get('app_name'),
                size_bytes=asset.size_bytes
            )
            
            # Classify using the classification engine
            classification_results = classification_engine.classify_and_store_results(
                content=content_text,
                data_asset=asset,
                context=context
            )
            
            # Update asset with best classification if found
            if classification_results:
                best_result = max(classification_results, key=lambda r: r.confidence_score)
                if best_result.confidence_score > 0.6:
                    asset.primary_classification = best_result.predicted_classification
                    asset.sensitivity_level = best_result.predicted_sensitivity
                    asset.save(update_fields=['primary_classification', 'sensitivity_level'])
            
        except Exception as e:
            logger.error(f"Error classifying asset content: {e}")
    
    def _check_alert_conditions(self, asset, monitor) -> bool:
        """Check if the asset classification should trigger an alert"""
        try:
            # Check if alerts are enabled
            if not monitor.alert_on_sensitive:
                return False
            
            # Check sensitivity threshold
            sensitivity_levels = {
                'low': 1,
                'medium': 2, 
                'high': 3,
                'critical': 4
            }
            
            asset_level = sensitivity_levels.get(asset.sensitivity_level, 2)
            threshold_level = sensitivity_levels.get(monitor.alert_threshold, 3)
            
            if asset_level >= threshold_level:
                return True
            
            # Check for specific classifications that should always alert
            high_risk_classifications = [
                DataClassification.PII,
                DataClassification.PHI,
                DataClassification.FINANCIAL,
                DataClassification.RESTRICTED
            ]
            
            if asset.primary_classification in high_risk_classifications:
                return True
            
        except Exception as e:
            logger.error(f"Error checking alert conditions: {e}")
        
        return False
    
    def _send_alert(self, monitor, asset, event_type):
        """Send alert for sensitive data discovery"""
        try:
            # Generate insight for the alert
            insight = DataDiscoveryInsight.objects.create(
                title=f"Sensitive Data Discovered: {asset.name}",
                description=f"Real-time monitoring detected {asset.get_primary_classification_display()} "
                           f"data with {asset.get_sensitivity_level_display()} sensitivity level.",
                insight_type="security",
                severity="high" if asset.sensitivity_level in ['high', 'critical'] else "medium",
                insight_data={
                    'monitor_name': monitor.name,
                    'event_type': event_type,
                    'classification': asset.primary_classification,
                    'sensitivity': asset.sensitivity_level,
                    'confidence_data': classification_engine.get_classification_summary(asset)
                },
                recommendations=[
                    "Review the detected sensitive data",
                    "Ensure proper access controls are in place", 
                    "Consider data masking if appropriate",
                    "Verify compliance with data protection policies"
                ]
            )
            
            # Associate with the asset
            insight.related_assets.add(asset)
            
            # TODO: Send notifications to configured users/emails
            # This would integrate with a notification system
            
            logger.info(f"Alert generated for sensitive data: {asset.name}")
            
        except Exception as e:
            logger.error(f"Error sending alert: {e}")
    
    def refresh_monitors(self):
        """Refresh the monitor configuration from database"""
        self._load_active_monitors()


# Global instance
real_time_signals = RealTimeDiscoverySignals()


# Signal receivers that use the global instance
@receiver(post_save)
def handle_model_save(sender, instance, created, **kwargs):
    """Handle all model save events"""
    if created:
        real_time_signals.handle_model_created(sender, instance, created, **kwargs)
    else:
        real_time_signals.handle_model_updated(sender, instance, created, **kwargs)


@receiver(post_delete)
def handle_model_delete(sender, instance, **kwargs):
    """Handle model deletion - remove corresponding data asset"""
    try:
        if real_time_signals.should_monitor_model(sender):
            content_type = ContentType.objects.get_for_model(sender)
            
            # Find and deactivate the corresponding data asset
            assets = DataAsset.objects.filter(
                content_type=content_type,
                object_id=instance.pk
            )
            
            for asset in assets:
                asset.is_active = False
                asset.save(update_fields=['is_active'])
                
                logger.debug(f"Deactivated data asset for deleted object: {asset.name}")
                
    except Exception as e:
        logger.error(f"Error handling model deletion: {e}")


def create_default_monitors():
    """Create default real-time monitors for key data types"""
    try:
        # Monitor for user profile changes
        monitor, created = RealTimeMonitor.objects.get_or_create(
            name="User Profile Monitor",
            defaults={
                'description': 'Monitor changes to user profiles and personal information',
                'monitor_type': 'model_changes',
                'target_specification': {
                    'models': [
                        {'app': 'profiles', 'model': 'profile'},
                        {'app': 'accounts', 'model': 'user'}
                    ]
                },
                'auto_classify': True,
                'alert_on_sensitive': True,
                'alert_threshold': SensitivityLevel.HIGH,
                'is_active': True
            }
        )
        
        if created:
            logger.info("Created default User Profile Monitor")
        
        # Monitor for document uploads
        monitor, created = RealTimeMonitor.objects.get_or_create(
            name="Document Upload Monitor",
            defaults={
                'description': 'Monitor document uploads for sensitive content',
                'monitor_type': 'model_changes',
                'target_specification': {
                    'models': [
                        {'app': 'documents', 'model': 'document'}
                    ]
                },
                'auto_classify': True,
                'alert_on_sensitive': True,
                'alert_threshold': SensitivityLevel.HIGH,
                'is_active': True
            }
        )
        
        if created:
            logger.info("Created default Document Upload Monitor")
        
        # Monitor for messaging data
        monitor, created = RealTimeMonitor.objects.get_or_create(
            name="Messaging Content Monitor", 
            defaults={
                'description': 'Monitor messaging content for sensitive information',
                'monitor_type': 'model_changes',
                'target_specification': {
                    'models': [
                        {'app': 'messaging', 'model': 'message'}
                    ]
                },
                'auto_classify': True,
                'alert_on_sensitive': True,
                'alert_threshold': SensitivityLevel.MEDIUM,
                'is_active': True
            }
        )
        
        if created:
            logger.info("Created default Messaging Content Monitor")
            
        # Refresh monitors after creating defaults
        real_time_signals.refresh_monitors()
        
    except Exception as e:
        logger.error(f"Error creating default monitors: {e}")


@receiver(post_save, sender=ClassificationResult)
def handle_classification_result_created(sender, instance, created, **kwargs):
    """Handle new classification results and apply governance automation"""
    if not created:
        return
    
    # Check for high-risk classifications that need immediate attention
    high_risk_types = ['PII', 'PHI', 'CREDENTIALS', 'FINANCIAL']
    
    if instance.classification_type in high_risk_types and instance.confidence_score >= 0.8:
        # Create a high-priority insight
        DataDiscoveryInsight.objects.create(
            asset=instance.data_asset,
            insight_type='security',
            title=f'High-risk {instance.classification_type} data detected',
            description=f'Data classified as {instance.classification_type} with {instance.confidence_score:.1%} confidence',
            severity='high',
            metadata={
                'classification_result_id': instance.id,
                'classification_type': instance.classification_type,
                'confidence_score': instance.confidence_score,
                'auto_detected': True
            }
        )
        
        logger.warning(f'High-risk classification detected: {instance.classification_type} in asset {instance.data_asset.id}')
    
    # Apply governance workflows asynchronously
    try:
        import threading
        from .governance import GovernanceOrchestrator
        
        def apply_governance():
            """Apply governance workflows in background"""
            try:
                orchestrator = GovernanceOrchestrator()
                result = orchestrator.process_classification_result(instance)
                
                logger.info(
                    f'Governance applied to classification {instance.id}: '
                    f"{', '.join(result.get('governance_actions', []))}"
                )
            except Exception as e:
                logger.error(f'Failed to apply governance to classification {instance.id}: {str(e)}')
        
        # Run governance in background thread to avoid blocking
        if instance.confidence_score >= 0.7:  # Only apply governance to medium+ confidence results
            thread = threading.Thread(target=apply_governance)
            thread.daemon = True
            thread.start()
        
    except Exception as e:
        logger.error(f'Error initiating governance workflow: {str(e)}')


def initialize_real_time_monitoring():
    """Initialize the real-time monitoring system"""
    try:
        logger.info("Initializing real-time data discovery monitoring")
        
        # Create default monitors if they don't exist
        create_default_monitors()
        
        # Load active monitors
        real_time_signals.refresh_monitors()
        
        logger.info("Real-time monitoring system initialized successfully")
        
    except Exception as e:
        logger.error(f"Error initializing real-time monitoring: {e}")
