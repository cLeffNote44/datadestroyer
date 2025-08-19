"""
Analytics Integration for Discovery System

This module provides integration between the discovery system and the analytics dashboard,
ensuring that discovery metrics are properly tracked and reported in user analytics.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict

from django.contrib.auth import get_user_model
from django.db.models import Count, Avg, Q, Sum
from django.utils import timezone

from analytics.models import AnalyticsSnapshot, PrivacyInsight
from .models import (
    DataAsset, ClassificationResult, DataDiscoveryInsight, DataLineage,
    DiscoveryJob, SensitivityLevel, DataClassification
)

User = get_user_model()
logger = logging.getLogger(__name__)


class DiscoveryAnalyticsIntegrator:
    """Handles integration between discovery system and analytics"""
    
    def __init__(self):
        self.user_cache = {}
    
    def update_user_discovery_metrics(self, user: User, snapshot: AnalyticsSnapshot) -> Dict[str, Any]:
        """
        Update discovery-related metrics for a user's analytics snapshot
        
        Args:
            user: User to calculate metrics for
            snapshot: Analytics snapshot to update
            
        Returns:
            Dictionary of calculated metrics
        """
        try:
            # Get user's data assets
            user_assets = self._get_user_data_assets(user)
            
            # Calculate basic discovery metrics
            total_assets = user_assets.count()
            classified_assets = user_assets.filter(
                classification_results__isnull=False
            ).distinct().count()
            
            # Count sensitive assets (high/critical sensitivity)
            sensitive_assets = user_assets.filter(
                sensitivity_level__in=[SensitivityLevel.HIGH, SensitivityLevel.CRITICAL]
            ).count()
            
            # Get active discovery insights for this user
            active_insights = DataDiscoveryInsight.objects.filter(
                related_assets__in=user_assets,
                is_resolved=False
            ).distinct().count()
            
            # Calculate average classification confidence
            avg_confidence = ClassificationResult.objects.filter(
                data_asset__in=user_assets
            ).aggregate(avg_conf=Avg('confidence_score'))['avg_conf'] or 0.0
            
            # Count data lineage relationships
            lineage_count = DataLineage.objects.filter(
                Q(source_asset__in=user_assets) | Q(target_asset__in=user_assets)
            ).count()
            
            # Calculate discovery coverage score
            coverage_score = self._calculate_discovery_coverage(user, user_assets)
            
            # Update the snapshot
            metrics = {
                'total_data_assets': total_assets,
                'classified_assets_count': classified_assets,
                'sensitive_assets_count': sensitive_assets,
                'discovery_insights_count': active_insights,
                'avg_classification_confidence': avg_confidence,
                'data_lineage_relationships': lineage_count,
                'discovery_coverage_score': coverage_score
            }
            
            # Update snapshot fields
            for field, value in metrics.items():
                setattr(snapshot, field, value)
            
            logger.debug(f"Updated discovery metrics for user {user.username}: {metrics}")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error updating discovery metrics for user {user.username}: {e}")
            return {}
    
    def _get_user_data_assets(self, user: User):
        """Get data assets associated with a user"""
        # This is a simplified approach - in practice you might want to filter by:
        # - Assets created by the user
        # - Assets the user has access to
        # - Assets in the user's organizational scope
        
        # For now, we'll get assets that reference objects owned by this user
        from django.contrib.contenttypes.models import ContentType
        
        # Get content types for models that have an 'owner' or similar field
        user_assets = DataAsset.objects.none()
        
        try:
            # Try to find assets linked to user's content
            # This is a heuristic approach - you may need to customize based on your data model
            
            # Look for documents owned by user
            try:
                from documents.models import Document
                doc_ct = ContentType.objects.get_for_model(Document)
                user_docs = Document.objects.filter(owner=user)
                doc_assets = DataAsset.objects.filter(
                    content_type=doc_ct,
                    object_id__in=user_docs.values_list('id', flat=True)
                )
                user_assets = user_assets.union(doc_assets)
            except:
                pass
            
            # Look for messages from user
            try:
                from messaging.models import Message
                msg_ct = ContentType.objects.get_for_model(Message)
                user_messages = Message.objects.filter(sender=user)
                msg_assets = DataAsset.objects.filter(
                    content_type=msg_ct,
                    object_id__in=user_messages.values_list('id', flat=True)
                )
                user_assets = user_assets.union(msg_assets)
            except:
                pass
            
            # Look for forum posts by user
            try:
                from forum.models import Post
                post_ct = ContentType.objects.get_for_model(Post)
                user_posts = Post.objects.filter(author=user)
                post_assets = DataAsset.objects.filter(
                    content_type=post_ct,
                    object_id__in=user_posts.values_list('id', flat=True)
                )
                user_assets = user_assets.union(post_assets)
            except:
                pass
            
        except Exception as e:
            logger.warning(f"Error getting user assets for {user.username}: {e}")
        
        return user_assets.filter(is_active=True)
    
    def _calculate_discovery_coverage(self, user: User, user_assets) -> int:
        """
        Calculate discovery coverage score (0-100) based on how well
        the user's data is discovered and classified
        """
        try:
            if not user_assets.exists():
                return 100  # Perfect score if no assets (nothing to discover)
            
            total_assets = user_assets.count()
            classified_assets = user_assets.filter(
                classification_results__isnull=False
            ).distinct().count()
            
            # Base coverage from classification ratio
            classification_ratio = classified_assets / total_assets if total_assets > 0 else 0
            base_score = int(classification_ratio * 70)  # Up to 70 points
            
            # Bonus points for high-confidence classifications
            high_confidence_assets = user_assets.filter(
                classification_results__confidence_score__gte=0.8
            ).distinct().count()
            
            confidence_bonus = int((high_confidence_assets / total_assets) * 20) if total_assets > 0 else 0
            
            # Bonus points for data lineage tracking
            assets_with_lineage = user_assets.filter(
                Q(upstream_lineages__isnull=False) | Q(downstream_lineages__isnull=False)
            ).distinct().count()
            
            lineage_bonus = int((assets_with_lineage / total_assets) * 10) if total_assets > 0 else 0
            
            total_score = base_score + confidence_bonus + lineage_bonus
            
            return min(100, max(0, total_score))
            
        except Exception as e:
            logger.error(f"Error calculating discovery coverage for {user.username}: {e}")
            return 0
    
    def generate_discovery_insights_for_user(self, user: User) -> List[PrivacyInsight]:
        """
        Generate privacy insights based on discovery system data
        """
        insights = []
        
        try:
            user_assets = self._get_user_data_assets(user)
            
            # Insight 1: Unclassified sensitive data
            unclassified_assets = user_assets.filter(
                classification_results__isnull=True,
                primary_classification__in=[
                    DataClassification.PII,
                    DataClassification.PHI,
                    DataClassification.FINANCIAL,
                    DataClassification.RESTRICTED
                ]
            ).count()
            
            if unclassified_assets > 5:
                insight = PrivacyInsight.objects.create(
                    user=user,
                    insight_type='recommendation',
                    severity='medium',
                    title=f'Classify {unclassified_assets} Sensitive Data Assets',
                    description=(
                        f'You have {unclassified_assets} potentially sensitive data assets '
                        f'that need proper classification. Running a discovery scan can help '
                        f'identify and classify this data automatically.'
                    ),
                    action_text='Run Discovery Scan',
                    action_url='/api/discovery/dashboard/',
                    context_data={
                        'source': 'discovery_system',
                        'unclassified_count': unclassified_assets,
                        'recommendation_type': 'classification'
                    }
                )
                insights.append(insight)
            
            # Insight 2: High concentration of sensitive data
            total_assets = user_assets.count()
            sensitive_assets = user_assets.filter(
                sensitivity_level__in=[SensitivityLevel.HIGH, SensitivityLevel.CRITICAL]
            ).count()
            
            if total_assets > 0:
                sensitive_ratio = sensitive_assets / total_assets
                if sensitive_ratio > 0.4:  # More than 40% sensitive
                    insight = PrivacyInsight.objects.create(
                        user=user,
                        insight_type='alert',
                        severity='high',
                        title=f'High Concentration of Sensitive Data ({sensitive_ratio:.0%})',
                        description=(
                            f'A significant portion of your data ({sensitive_ratio:.0%}) is '
                            f'classified as sensitive. Consider reviewing access controls, '
                            f'encryption, and data handling policies.'
                        ),
                        action_text='Review Data Security',
                        context_data={
                            'source': 'discovery_system',
                            'sensitive_ratio': sensitive_ratio,
                            'sensitive_count': sensitive_assets,
                            'total_count': total_assets
                        }
                    )
                    insights.append(insight)
            
            # Insight 3: Low classification confidence
            low_confidence_results = ClassificationResult.objects.filter(
                data_asset__in=user_assets,
                confidence_score__lt=0.6
            ).count()
            
            if low_confidence_results > 10:
                insight = PrivacyInsight.objects.create(
                    user=user,
                    insight_type='recommendation',
                    severity='low',
                    title=f'Review {low_confidence_results} Low-Confidence Classifications',
                    description=(
                        f'Some of your data classifications have low confidence scores. '
                        f'Manual review can help improve classification accuracy and '
                        f'ensure proper data handling.'
                    ),
                    action_text='Review Classifications',
                    context_data={
                        'source': 'discovery_system',
                        'low_confidence_count': low_confidence_results,
                        'recommendation_type': 'validation'
                    }
                )
                insights.append(insight)
            
            logger.info(f"Generated {len(insights)} discovery insights for user {user.username}")
            
        except Exception as e:
            logger.error(f"Error generating discovery insights for user {user.username}: {e}")
        
        return insights
    
    def sync_discovery_insights_with_analytics(self, user: User) -> int:
        """
        Sync discovery insights with analytics privacy insights
        """
        try:
            # Clean up old discovery insights
            old_insights = PrivacyInsight.objects.filter(
                user=user,
                context_data__source='discovery_system',
                is_dismissed=False
            )
            
            # Mark old insights as expired if they're more than 7 days old
            week_ago = timezone.now() - timedelta(days=7)
            expired_count = old_insights.filter(
                created_at__lt=week_ago
            ).update(
                is_dismissed=True,
                dismissed_at=timezone.now()
            )
            
            # Generate new insights
            new_insights = self.generate_discovery_insights_for_user(user)
            
            logger.info(
                f"Discovery insights sync for {user.username}: "
                f"{expired_count} expired, {len(new_insights)} new"
            )
            
            return len(new_insights)
            
        except Exception as e:
            logger.error(f"Error syncing discovery insights for user {user.username}: {e}")
            return 0
    
    def get_system_wide_discovery_metrics(self) -> Dict[str, Any]:
        """Get system-wide discovery metrics for dashboard"""
        try:
            # Total assets across system
            total_assets = DataAsset.objects.filter(is_active=True).count()
            
            # Classification metrics
            classified_assets = DataAsset.objects.filter(
                is_active=True,
                classification_results__isnull=False
            ).distinct().count()
            
            # Sensitivity distribution
            sensitivity_distribution = dict(
                DataAsset.objects.filter(is_active=True)
                .values('sensitivity_level')
                .annotate(count=Count('id'))
                .values_list('sensitivity_level', 'count')
            )
            
            # Classification distribution
            classification_distribution = dict(
                DataAsset.objects.filter(is_active=True)
                .values('primary_classification')
                .annotate(count=Count('id'))
                .values_list('primary_classification', 'count')
            )
            
            # Recent discovery activity
            recent_jobs = DiscoveryJob.objects.filter(
                created_at__gte=timezone.now() - timedelta(days=7),
                status='completed'
            ).count()
            
            # Active insights
            active_insights = DataDiscoveryInsight.objects.filter(
                is_resolved=False
            ).count()
            
            return {
                'total_assets': total_assets,
                'classified_assets': classified_assets,
                'classification_coverage': (classified_assets / total_assets * 100) if total_assets > 0 else 0,
                'sensitivity_distribution': sensitivity_distribution,
                'classification_distribution': classification_distribution,
                'recent_discovery_jobs': recent_jobs,
                'active_insights': active_insights,
                'total_lineage_relationships': DataLineage.objects.count()
            }
            
        except Exception as e:
            logger.error(f"Error getting system-wide discovery metrics: {e}")
            return {}


# Global instance
discovery_analytics_integrator = DiscoveryAnalyticsIntegrator()
