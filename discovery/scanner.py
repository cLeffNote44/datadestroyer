"""
Data Discovery Scanner

This module provides comprehensive data discovery capabilities:
- Model scanning to discover data across Django applications
- Content analysis and classification
- Lineage detection and relationship mapping
- Real-time monitoring integration
"""

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.db import models

from .classification_engine import ContentContext, classification_engine
from .models import (
    DataAsset,
    DataClassification,
    DataDiscoveryInsight,
    DataLineage,
    DiscoveryJob,
    DiscoveryStatus,
    SensitivityLevel,
)

logger = logging.getLogger(__name__)


@dataclass
class DiscoveryResult:
    """Result of a discovery scan"""

    assets_discovered: int = 0
    assets_classified: int = 0
    lineage_relationships: int = 0
    insights_generated: int = 0
    errors_encountered: int = 0
    processing_time: float = 0.0
    error_details: List[str] = None

    def __post_init__(self):
        if self.error_details is None:
            self.error_details = []


class DataDiscoveryScanner:
    """Comprehensive data discovery and classification scanner"""

    def __init__(self):
        self.exclude_apps = {
            "admin",
            "auth",
            "contenttypes",
            "sessions",
            "messages",
            "staticfiles",
            "migrations",
            "axes",
            "auditlog",
        }
        self.exclude_models = {
            "logentry",
            "permission",
            "group",
            "contenttype",
            "session",
            "migrationrecorder",
            "accesslog",
            "accessattempt",
        }
        self.text_field_types = ["CharField", "TextField", "EmailField", "URLField", "SlugField"]
        self.sensitive_field_patterns = [
            r".*password.*",
            r".*secret.*",
            r".*key.*",
            r".*token.*",
            r".*ssn.*",
            r".*social.*",
            r".*credit.*",
            r".*card.*",
            r".*phone.*",
            r".*email.*",
            r".*address.*",
            r".*name.*",
        ]

    def run_full_discovery(
        self,
        discovery_job: Optional[DiscoveryJob] = None,
        target_apps: Optional[List[str]] = None,
        target_models: Optional[List[str]] = None,
        include_lineage: bool = True,
        include_insights: bool = True,
    ) -> DiscoveryResult:
        """
        Run a comprehensive discovery scan across the system

        Args:
            discovery_job: Optional DiscoveryJob instance to track progress
            target_apps: Specific apps to scan (None = all apps)
            target_models: Specific models to scan (None = all models)
            include_lineage: Whether to detect data lineage relationships
            include_insights: Whether to generate insights from discoveries

        Returns:
            DiscoveryResult with scan statistics and results
        """
        start_time = time.time()
        result = DiscoveryResult()

        try:
            if discovery_job:
                discovery_job.status = DiscoveryStatus.RUNNING
                discovery_job.started_at = datetime.now()
                discovery_job.save()

            logger.info("Starting full data discovery scan")

            # Phase 1: Discover data assets
            logger.info("Phase 1: Discovering data assets")
            asset_result = self._discover_data_assets(target_apps, target_models)
            result.assets_discovered = asset_result["discovered"]
            result.errors_encountered += asset_result["errors"]
            result.error_details.extend(asset_result["error_details"])

            # Phase 2: Classify discovered assets
            logger.info("Phase 2: Classifying discovered assets")
            classification_result = self._classify_assets(discovery_job)
            result.assets_classified = classification_result["classified"]
            result.errors_encountered += classification_result["errors"]
            result.error_details.extend(classification_result["error_details"])

            # Phase 3: Detect data lineage (if enabled)
            if include_lineage:
                logger.info("Phase 3: Detecting data lineage relationships")
                lineage_result = self._detect_lineage_relationships()
                result.lineage_relationships = lineage_result["relationships"]
                result.errors_encountered += lineage_result["errors"]
                result.error_details.extend(lineage_result["error_details"])

            # Phase 4: Generate insights (if enabled)
            if include_insights:
                logger.info("Phase 4: Generating discovery insights")
                insight_result = self._generate_discovery_insights(discovery_job)
                result.insights_generated = insight_result["insights"]
                result.errors_encountered += insight_result["errors"]
                result.error_details.extend(insight_result["error_details"])

            result.processing_time = time.time() - start_time

            # Update discovery job
            if discovery_job:
                discovery_job.status = DiscoveryStatus.COMPLETED
                discovery_job.completed_at = datetime.now()
                discovery_job.assets_discovered = result.assets_discovered
                discovery_job.assets_classified = result.assets_classified
                discovery_job.errors_encountered = result.errors_encountered
                discovery_job.results_summary = {
                    "processing_time": result.processing_time,
                    "lineage_relationships": result.lineage_relationships,
                    "insights_generated": result.insights_generated,
                    "phases_completed": 4 if include_insights else 3 if include_lineage else 2,
                }
                if result.error_details:
                    discovery_job.error_log = "\n".join(result.error_details)
                discovery_job.save()

            logger.info(
                f"Discovery scan completed: {result.assets_discovered} assets discovered, "
                f"{result.assets_classified} classified, {result.errors_encountered} errors"
            )

        except Exception as e:
            result.errors_encountered += 1
            result.error_details.append(f"Fatal error during discovery: {str(e)}")
            logger.error(f"Fatal error during discovery scan: {e}", exc_info=True)

            if discovery_job:
                discovery_job.status = DiscoveryStatus.FAILED
                discovery_job.completed_at = datetime.now()
                discovery_job.errors_encountered = result.errors_encountered
                discovery_job.error_log = "\n".join(result.error_details)
                discovery_job.save()

        return result

    def _discover_data_assets(
        self, target_apps: Optional[List[str]] = None, target_models: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Discover data assets across Django applications"""
        discovered = 0
        errors = 0
        error_details = []

        try:
            # Get all Django models to scan
            models_to_scan = self._get_models_to_scan(target_apps, target_models)

            for model_class in models_to_scan:
                try:
                    app_name = model_class._meta.app_label
                    model_name = model_class._meta.model_name

                    logger.debug(f"Scanning model: {app_name}.{model_name}")

                    # Get content type for this model
                    content_type = ContentType.objects.get_for_model(model_class)

                    # Scan each instance of the model
                    queryset = model_class.objects.all()

                    # Batch process to avoid memory issues
                    batch_size = 100
                    total_objects = queryset.count()

                    for offset in range(0, total_objects, batch_size):
                        batch = queryset[offset : offset + batch_size]

                        for obj in batch:
                            try:
                                asset_discovered = self._discover_model_instance(
                                    obj, content_type, app_name, model_name
                                )
                                if asset_discovered:
                                    discovered += 1

                            except Exception as e:
                                errors += 1
                                error_details.append(
                                    f"Error discovering {model_name} instance {obj.pk}: {str(e)}"
                                )
                                logger.warning(
                                    f"Error discovering {model_name} instance {obj.pk}: {e}"
                                )

                except Exception as e:
                    errors += 1
                    error_details.append(f"Error scanning model {model_class}: {str(e)}")
                    logger.error(f"Error scanning model {model_class}: {e}")

        except Exception as e:
            errors += 1
            error_details.append(f"Error during asset discovery: {str(e)}")
            logger.error(f"Error during asset discovery: {e}")

        return {"discovered": discovered, "errors": errors, "error_details": error_details}

    def _discover_model_instance(
        self, obj: models.Model, content_type: ContentType, app_name: str, model_name: str
    ) -> bool:
        """Discover a single model instance as a data asset"""
        try:
            # Check if asset already exists
            existing_asset = DataAsset.objects.filter(
                content_type=content_type, object_id=obj.pk
            ).first()

            if existing_asset:
                # Update last scanned time
                existing_asset.last_scanned = datetime.now()
                existing_asset.save(update_fields=["last_scanned"])
                return False  # Not newly discovered

            # Create new data asset
            asset_name = self._generate_asset_name(obj, model_name)
            asset_description = self._generate_asset_description(obj, model_name)

            # Analyze content for initial classification hints
            content_analysis = self._analyze_model_content(obj)

            asset = DataAsset.objects.create(
                name=asset_name,
                description=asset_description,
                content_type=content_type,
                object_id=obj.pk,
                discovered_at=datetime.now(),
                primary_classification=self._suggest_initial_classification(
                    content_analysis, model_name
                ),
                sensitivity_level=self._suggest_initial_sensitivity(content_analysis, model_name),
                size_bytes=self._estimate_object_size(obj),
                database_table=obj._meta.db_table,
                metadata={
                    "app_name": app_name,
                    "model_name": model_name,
                    "field_count": len(obj._meta.fields),
                    "content_analysis": content_analysis,
                },
            )

            logger.debug(f"Discovered new asset: {asset_name}")
            return True

        except Exception as e:
            logger.error(f"Error discovering model instance {obj}: {e}")
            raise

    def _classify_assets(self, discovery_job: Optional[DiscoveryJob] = None) -> Dict[str, Any]:
        """Classify discovered data assets using the classification engine"""
        classified = 0
        errors = 0
        error_details = []

        try:
            # Get unclassified or recently updated assets
            cutoff_time = datetime.now() - timedelta(hours=1)  # Re-classify recent assets

            assets_to_classify = DataAsset.objects.filter(
                models.Q(classification_results__isnull=True)
                | models.Q(last_scanned__gte=cutoff_time)
            ).distinct()

            for asset in assets_to_classify:
                try:
                    classification_count = self._classify_single_asset(asset, discovery_job)
                    if classification_count > 0:
                        classified += 1

                except Exception as e:
                    errors += 1
                    error_details.append(f"Error classifying asset {asset.name}: {str(e)}")
                    logger.warning(f"Error classifying asset {asset.name}: {e}")

        except Exception as e:
            errors += 1
            error_details.append(f"Error during asset classification: {str(e)}")
            logger.error(f"Error during asset classification: {e}")

        return {"classified": classified, "errors": errors, "error_details": error_details}

    def _classify_single_asset(
        self, asset: DataAsset, discovery_job: Optional[DiscoveryJob] = None
    ) -> int:
        """Classify a single data asset"""
        try:
            # Get the actual object
            obj = asset.content_object
            if not obj:
                return 0

            # Extract text content for classification
            content_text = self._extract_text_content(obj)

            if not content_text or not content_text.strip():
                return 0

            # Create content context
            context = ContentContext(
                content_type=str(asset.content_type),
                model_name=asset.metadata.get("model_name"),
                app_name=asset.metadata.get("app_name"),
                size_bytes=asset.size_bytes,
            )

            # Classify using the classification engine
            classification_results = classification_engine.classify_and_store_results(
                content=content_text, data_asset=asset, discovery_job=discovery_job, context=context
            )

            # Update asset with best classification if found
            if classification_results:
                best_result = max(classification_results, key=lambda r: r.confidence_score)
                if best_result.confidence_score > 0.6:  # Only update if confident
                    asset.primary_classification = best_result.predicted_classification
                    asset.sensitivity_level = best_result.predicted_sensitivity
                    asset.save(update_fields=["primary_classification", "sensitivity_level"])

            return len(classification_results)

        except Exception as e:
            logger.error(f"Error classifying asset {asset}: {e}")
            raise

    def _detect_lineage_relationships(self) -> Dict[str, Any]:
        """Detect data lineage relationships between assets"""
        relationships = 0
        errors = 0
        error_details = []

        try:
            # This is a simplified lineage detection
            # In a full implementation, this would analyze:
            # - Foreign key relationships
            # - Data transformation pipelines
            # - File copying/movement operations
            # - API data flows

            assets = DataAsset.objects.select_related("content_type").all()

            for asset in assets:
                try:
                    lineage_count = self._detect_asset_relationships(asset)
                    relationships += lineage_count

                except Exception as e:
                    errors += 1
                    error_details.append(f"Error detecting lineage for {asset.name}: {str(e)}")
                    logger.warning(f"Error detecting lineage for {asset.name}: {e}")

        except Exception as e:
            errors += 1
            error_details.append(f"Error during lineage detection: {str(e)}")
            logger.error(f"Error during lineage detection: {e}")

        return {"relationships": relationships, "errors": errors, "error_details": error_details}

    def _detect_asset_relationships(self, asset: DataAsset) -> int:
        """Detect relationships for a single asset"""
        relationships_created = 0

        try:
            obj = asset.content_object
            if not obj:
                return 0

            # Analyze foreign key relationships
            for field in obj._meta.fields:
                if field.is_relation and field.many_to_one:
                    try:
                        related_obj = getattr(obj, field.name)
                        if related_obj:
                            # Find corresponding asset
                            related_content_type = ContentType.objects.get_for_model(related_obj)
                            related_asset = DataAsset.objects.filter(
                                content_type=related_content_type, object_id=related_obj.pk
                            ).first()

                            if related_asset:
                                # Create lineage relationship
                                lineage, created = DataLineage.objects.get_or_create(
                                    source_asset=related_asset,
                                    target_asset=asset,
                                    defaults={
                                        "relationship_type": "reference",
                                        "transformation_logic": f"Foreign key reference via {field.name}",
                                        "confidence_score": 1.0,
                                        "impact_score": 0.3,
                                    },
                                )

                                if created:
                                    relationships_created += 1

                    except Exception as e:
                        logger.debug(f"Error analyzing field {field.name}: {e}")

        except Exception as e:
            logger.error(f"Error detecting relationships for {asset}: {e}")

        return relationships_created

    def _generate_discovery_insights(
        self, discovery_job: Optional[DiscoveryJob] = None
    ) -> Dict[str, Any]:
        """Generate insights from discovery results"""
        insights = 0
        errors = 0
        error_details = []

        try:
            # Generate various types of insights
            insights += self._generate_classification_insights()
            insights += self._generate_compliance_insights()
            insights += self._generate_security_insights()
            insights += self._generate_governance_insights()

        except Exception as e:
            errors += 1
            error_details.append(f"Error generating insights: {str(e)}")
            logger.error(f"Error generating discovery insights: {e}")

        return {"insights": insights, "errors": errors, "error_details": error_details}

    def _generate_classification_insights(self) -> int:
        """Generate insights about data classification patterns"""
        insights_created = 0

        try:
            # Find unclassified assets
            unclassified_count = DataAsset.objects.filter(
                primary_classification=DataClassification.INTERNAL
            ).count()

            if unclassified_count > 10:
                insight = DataDiscoveryInsight.objects.create(
                    title="High Volume of Unclassified Data",
                    description=f"Found {unclassified_count} data assets that may need proper classification. "
                    f"Consider running additional classification rules or manual review.",
                    insight_type="classification",
                    severity="medium",
                    insight_data={
                        "unclassified_count": unclassified_count,
                        "recommendation": "enhanced_classification",
                    },
                    recommendations=[
                        "Review and enhance classification rules",
                        "Implement context-aware classification",
                        "Conduct manual classification review",
                    ],
                )

                # Associate with unclassified assets (limit to avoid performance issues)
                unclassified_assets = DataAsset.objects.filter(
                    primary_classification=DataClassification.INTERNAL
                )[:50]
                insight.related_assets.set(unclassified_assets)

                insights_created += 1

            # Find high-sensitivity data concentrations
            sensitive_assets = DataAsset.objects.filter(
                sensitivity_level__in=[SensitivityLevel.HIGH, SensitivityLevel.CRITICAL]
            ).count()

            if sensitive_assets > 0:
                total_assets = DataAsset.objects.count()
                sensitive_ratio = sensitive_assets / total_assets if total_assets > 0 else 0

                if sensitive_ratio > 0.3:  # More than 30% sensitive
                    insight = DataDiscoveryInsight.objects.create(
                        title="High Concentration of Sensitive Data",
                        description=f"Found {sensitive_assets} sensitive data assets ({sensitive_ratio:.1%} of total). "
                        f"Consider implementing additional security measures.",
                        insight_type="security",
                        severity="high",
                        insight_data={
                            "sensitive_count": sensitive_assets,
                            "total_count": total_assets,
                            "sensitive_ratio": sensitive_ratio,
                        },
                        recommendations=[
                            "Implement data encryption for sensitive assets",
                            "Review access controls for sensitive data",
                            "Consider data masking for non-production environments",
                        ],
                    )

                    insights_created += 1

        except Exception as e:
            logger.error(f"Error generating classification insights: {e}")

        return insights_created

    def _generate_compliance_insights(self) -> int:
        """Generate compliance-related insights"""
        # Placeholder for compliance insight generation
        return 0

    def _generate_security_insights(self) -> int:
        """Generate security-related insights"""
        # Placeholder for security insight generation
        return 0

    def _generate_governance_insights(self) -> int:
        """Generate governance-related insights"""
        # Placeholder for governance insight generation
        return 0

    # Helper methods

    def _get_models_to_scan(
        self, target_apps: Optional[List[str]] = None, target_models: Optional[List[str]] = None
    ) -> List[models.Model]:
        """Get list of Django models to scan"""
        models_to_scan = []

        for app_config in apps.get_app_configs():
            app_name = app_config.label

            # Skip excluded apps
            if app_name in self.exclude_apps:
                continue

            # Filter by target apps if specified
            if target_apps and app_name not in target_apps:
                continue

            for model_class in app_config.get_models():
                model_name = model_class._meta.model_name

                # Skip excluded models
                if model_name in self.exclude_models:
                    continue

                # Filter by target models if specified
                if target_models and model_name not in target_models:
                    continue

                models_to_scan.append(model_class)

        return models_to_scan

    def _generate_asset_name(self, obj: models.Model, model_name: str) -> str:
        """Generate a human-readable name for a data asset"""
        # Try to use common name fields
        for field_name in ["name", "title", "subject", "description"]:
            if hasattr(obj, field_name):
                value = getattr(obj, field_name)
                if value and len(str(value).strip()) > 0:
                    return f"{model_name.title()}: {str(value)[:50]}"

        # Fallback to model name and ID
        return f"{model_name.title()} #{obj.pk}"

    def _generate_asset_description(self, obj: models.Model, model_name: str) -> str:
        """Generate a description for a data asset"""
        # Try to extract descriptive text
        description_parts = []

        for field in obj._meta.fields:
            if field.get_internal_type() in self.text_field_types:
                try:
                    value = getattr(obj, field.name)
                    if value and len(str(value).strip()) > 10:
                        description_parts.append(f"{field.verbose_name}: {str(value)[:100]}")
                except:
                    pass

        if description_parts:
            return "; ".join(description_parts[:3])  # Limit to 3 fields

        return f"Data asset from {model_name} model"

    def _analyze_model_content(self, obj: models.Model) -> Dict[str, Any]:
        """Analyze model content to suggest classification"""
        analysis = {
            "text_fields": 0,
            "sensitive_field_names": [],
            "content_length": 0,
            "field_types": {},
        }

        for field in obj._meta.fields:
            field_type = field.get_internal_type()
            analysis["field_types"][field_type] = analysis["field_types"].get(field_type, 0) + 1

            if field_type in self.text_field_types:
                analysis["text_fields"] += 1

                # Check for sensitive field names
                import re

                for pattern in self.sensitive_field_patterns:
                    if re.match(pattern, field.name, re.IGNORECASE):
                        analysis["sensitive_field_names"].append(field.name)
                        break

                # Get content length
                try:
                    value = getattr(obj, field.name)
                    if value:
                        analysis["content_length"] += len(str(value))
                except:
                    pass

        return analysis

    def _suggest_initial_classification(
        self, content_analysis: Dict[str, Any], model_name: str
    ) -> str:
        """Suggest initial classification based on content analysis"""
        # Check for sensitive field names
        sensitive_fields = content_analysis.get("sensitive_field_names", [])

        if any(
            "password" in field.lower() or "secret" in field.lower() for field in sensitive_fields
        ):
            return DataClassification.RESTRICTED

        if any(
            "ssn" in field.lower() or "social" in field.lower() or "credit" in field.lower()
            for field in sensitive_fields
        ):
            return DataClassification.PII

        if any(
            "email" in field.lower() or "phone" in field.lower() or "address" in field.lower()
            for field in sensitive_fields
        ):
            return DataClassification.PII

        # Check model name patterns
        if "medical" in model_name.lower() or "health" in model_name.lower():
            return DataClassification.PHI

        if "financial" in model_name.lower() or "payment" in model_name.lower():
            return DataClassification.FINANCIAL

        return DataClassification.INTERNAL

    def _suggest_initial_sensitivity(
        self, content_analysis: Dict[str, Any], model_name: str
    ) -> str:
        """Suggest initial sensitivity level"""
        sensitive_fields = content_analysis.get("sensitive_field_names", [])

        if any(
            "password" in field.lower() or "secret" in field.lower() for field in sensitive_fields
        ):
            return SensitivityLevel.CRITICAL

        if sensitive_fields:
            return SensitivityLevel.HIGH

        return SensitivityLevel.MEDIUM

    def _estimate_object_size(self, obj: models.Model) -> Optional[int]:
        """Estimate the size of a model object in bytes"""
        try:
            # Simple estimation based on field content
            total_size = 0

            for field in obj._meta.fields:
                try:
                    value = getattr(obj, field.name)
                    if value is not None:
                        if isinstance(value, str):
                            total_size += len(value.encode("utf-8"))
                        elif isinstance(value, (int, float)):
                            total_size += 8  # Approximate size
                        elif isinstance(value, bool):
                            total_size += 1
                        else:
                            total_size += len(str(value).encode("utf-8"))
                except:
                    pass

            return total_size if total_size > 0 else None

        except Exception as e:
            logger.debug(f"Error estimating object size for {obj}: {e}")
            return None

    def _extract_text_content(self, obj: models.Model) -> str:
        """Extract text content from a model object for classification"""
        content_parts = []

        for field in obj._meta.fields:
            if field.get_internal_type() in self.text_field_types:
                try:
                    value = getattr(obj, field.name)
                    if value and len(str(value).strip()) > 0:
                        content_parts.append(str(value))
                except:
                    pass

        return " ".join(content_parts)


# Global scanner instance
data_discovery_scanner = DataDiscoveryScanner()
