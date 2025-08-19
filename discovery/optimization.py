"""
Performance Optimization Utilities for Data Discovery System

This module provides performance optimization tools, caching strategies,
and system tuning utilities for the data discovery and classification system.
"""

import logging
import time
import hashlib
from functools import wraps
from typing import Dict, Any, Optional, List, Callable
from django.core.cache import cache
from django.db import connection, connections
from django.db.models import QuerySet, Prefetch
from django.utils import timezone
from datetime import timedelta
import threading

from .models import (
    DataAsset, ClassificationResult, ClassificationRule, 
    DataDiscoveryInsight, RealTimeMonitor
)

logger = logging.getLogger(__name__)


class PerformanceOptimizer:
    """Main performance optimization coordinator"""
    
    def __init__(self):
        self.cache_prefix = 'discovery_cache'
        self.query_cache = {}
        self.optimization_stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'query_optimizations': 0,
            'batch_operations': 0
        }
    
    def optimize_classification_queries(self):
        """Optimize database queries for classification operations"""
        
        # Create database indexes for common queries
        with connection.cursor() as cursor:
            try:
                # Index on classification results for confidence and type
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_classification_confidence_type 
                    ON discovery_classificationresult (confidence_score, classification_type)
                """)
                
                # Index on data assets for active status and content type
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_dataasset_active_content 
                    ON discovery_dataasset (is_active, content_type_id)
                """)
                
                # Index on monitoring events for monitor and timestamp
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_monitoring_events_monitor_time 
                    ON discovery_monitoringevent (monitor_id, created_at DESC)
                """)
                
                # Composite index for insights by type and resolution status
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_insights_type_resolved 
                    ON discovery_datadiscoveryinsight (insight_type, is_resolved, created_at DESC)
                """)
                
                self.optimization_stats['query_optimizations'] += 4
                logger.info("Database indexes created for performance optimization")
                
            except Exception as e:
                logger.warning(f"Could not create some database indexes: {e}")
    
    def get_cached_classification_rules(self) -> List[ClassificationRule]:
        """Get classification rules with caching"""
        cache_key = f"{self.cache_prefix}_classification_rules"
        
        rules = cache.get(cache_key)
        if rules is not None:
            self.optimization_stats['cache_hits'] += 1
            return rules
        
        # Cache miss - fetch from database with optimizations
        rules = list(
            ClassificationRule.objects
            .filter(is_active=True)
            .select_related()
            .order_by('-confidence_weight')
        )
        
        # Cache for 15 minutes
        cache.set(cache_key, rules, 900)
        self.optimization_stats['cache_misses'] += 1
        
        return rules
    
    def batch_update_assets(self, asset_updates: List[Dict[str, Any]]) -> int:
        """Perform batch updates on data assets"""
        if not asset_updates:
            return 0
        
        updated_count = 0
        
        # Group updates by operation type for efficiency
        metadata_updates = []
        classification_updates = []
        
        for update in asset_updates:
            asset_id = update.get('asset_id')
            if not asset_id:
                continue
                
            if 'metadata' in update:
                metadata_updates.append(update)
            if 'classification' in update:
                classification_updates.append(update)
        
        # Batch metadata updates
        if metadata_updates:
            asset_ids = [u['asset_id'] for u in metadata_updates]
            assets = DataAsset.objects.filter(id__in=asset_ids).select_for_update()
            
            for asset in assets:
                # Find corresponding update
                update = next((u for u in metadata_updates if u['asset_id'] == asset.id), None)
                if update:
                    if asset.metadata is None:
                        asset.metadata = {}
                    asset.metadata.update(update['metadata'])
                    updated_count += 1
            
            DataAsset.objects.bulk_update(assets, ['metadata'], batch_size=100)
            self.optimization_stats['batch_operations'] += 1
        
        logger.info(f"Batch updated {updated_count} assets")
        return updated_count
    
    def cleanup_old_data(self, days_to_keep: int = 90):
        """Clean up old data to maintain performance"""
        cutoff_date = timezone.now() - timedelta(days=days_to_keep)
        
        cleanup_stats = {
            'monitoring_events': 0,
            'resolved_insights': 0,
            'inactive_assets': 0
        }
        
        # Clean up old monitoring events
        old_events = self.models.MonitoringEvent.objects.filter(
            created_at__lt=cutoff_date
        )
        cleanup_stats['monitoring_events'] = old_events.count()
        old_events.delete()
        
        # Clean up resolved insights older than retention period
        old_insights = self.models.DataDiscoveryInsight.objects.filter(
            created_at__lt=cutoff_date,
            is_resolved=True
        )
        cleanup_stats['resolved_insights'] = old_insights.count()
        old_insights.delete()
        
        # Mark old inactive assets for archival
        old_assets = DataAsset.objects.filter(
            last_scanned__lt=cutoff_date,
            is_active=False
        )
        cleanup_stats['inactive_assets'] = old_assets.count()
        old_assets.update(metadata=self.models.F('metadata').update({'archived': True}))
        
        logger.info(f"Cleanup completed: {cleanup_stats}")
        return cleanup_stats


def cache_result(timeout: int = 300, key_prefix: str = 'discovery'):
    """Decorator to cache function results"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            cache_key_data = f"{key_prefix}_{func.__name__}_{str(args)}_{str(sorted(kwargs.items()))}"
            cache_key = hashlib.md5(cache_key_data.encode()).hexdigest()
            
            # Try to get from cache
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, timeout)
            
            return result
        return wrapper
    return decorator


def optimize_queryset(func: Callable) -> Callable:
    """Decorator to optimize Django querysets"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Track query count before
        queries_before = len(connection.queries)
        
        result = func(*args, **kwargs)
        
        # Track query count after
        queries_after = len(connection.queries)
        query_count = queries_after - queries_before
        
        if query_count > 10:  # Log if too many queries
            logger.warning(f"Function {func.__name__} executed {query_count} database queries")
        
        return result
    return wrapper


class ClassificationEngineOptimizer:
    """Optimization specifically for the classification engine"""
    
    def __init__(self):
        self.rule_cache = {}
        self.pattern_cache = {}
        self.last_cache_update = None
        self.cache_lock = threading.Lock()
    
    @cache_result(timeout=600, key_prefix='classification')
    def get_optimized_rules_by_type(self, classification_type: str) -> List[ClassificationRule]:
        """Get classification rules optimized by type"""
        return list(
            ClassificationRule.objects
            .filter(is_active=True, classification_type=classification_type)
            .order_by('-confidence_weight')
        )
    
    def precompile_regex_patterns(self):
        """Pre-compile regex patterns for better performance"""
        import re
        
        with self.cache_lock:
            self.pattern_cache.clear()
            
            rules = ClassificationRule.objects.filter(
                is_active=True,
                rule_type='regex'
            )
            
            for rule in rules:
                try:
                    compiled_pattern = re.compile(rule.pattern, re.IGNORECASE)
                    self.pattern_cache[rule.id] = {
                        'pattern': compiled_pattern,
                        'rule': rule,
                        'compiled_at': timezone.now()
                    }
                except re.error as e:
                    logger.warning(f"Invalid regex pattern in rule {rule.id}: {e}")
            
            self.last_cache_update = timezone.now()
            logger.info(f"Pre-compiled {len(self.pattern_cache)} regex patterns")
    
    def get_compiled_pattern(self, rule_id: int):
        """Get pre-compiled regex pattern"""
        with self.cache_lock:
            # Refresh cache if older than 10 minutes
            if (self.last_cache_update is None or 
                timezone.now() - self.last_cache_update > timedelta(minutes=10)):
                self.precompile_regex_patterns()
            
            return self.pattern_cache.get(rule_id)
    
    def batch_classify_content(self, content_batches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Classify multiple content items in batch for better performance"""
        results = []
        
        # Pre-load all active rules
        rules = list(ClassificationRule.objects.filter(is_active=True))
        
        # Group rules by type for efficient processing
        rules_by_type = {}
        for rule in rules:
            if rule.classification_type not in rules_by_type:
                rules_by_type[rule.classification_type] = []
            rules_by_type[rule.classification_type].append(rule)
        
        for batch_item in content_batches:
            content = batch_item.get('content', '')
            context = batch_item.get('context', {})
            
            # Classify using pre-loaded rules
            classification_results = []
            
            for classification_type, type_rules in rules_by_type.items():
                matches = self._apply_rules_batch(content, type_rules)
                
                if matches:
                    confidence = self._calculate_confidence_batch(matches)
                    if confidence > 0.5:  # Minimum threshold
                        classification_results.append({
                            'classification_type': classification_type,
                            'confidence_score': confidence,
                            'rule_matches': [m['rule_name'] for m in matches],
                            'content_id': batch_item.get('content_id')
                        })
            
            results.append({
                'content_id': batch_item.get('content_id'),
                'classifications': classification_results
            })
        
        return results
    
    def _apply_rules_batch(self, content: str, rules: List[ClassificationRule]) -> List[Dict]:
        """Apply rules in batch mode"""
        matches = []
        
        for rule in rules:
            if rule.rule_type == 'regex':
                compiled_pattern = self.get_compiled_pattern(rule.id)
                if compiled_pattern:
                    pattern_matches = compiled_pattern['pattern'].findall(content)
                    if pattern_matches:
                        matches.append({
                            'rule_name': rule.name,
                            'rule_weight': rule.confidence_weight,
                            'matches': pattern_matches
                        })
            elif rule.rule_type == 'keyword':
                # Simple keyword matching
                keywords = rule.pattern.split(',')
                found_keywords = [kw.strip() for kw in keywords if kw.strip().lower() in content.lower()]
                if found_keywords:
                    matches.append({
                        'rule_name': rule.name,
                        'rule_weight': rule.confidence_weight,
                        'matches': found_keywords
                    })
        
        return matches
    
    def _calculate_confidence_batch(self, matches: List[Dict]) -> float:
        """Calculate confidence score for batch processing"""
        if not matches:
            return 0.0
        
        # Weight-based confidence calculation
        total_weight = sum(match['rule_weight'] for match in matches)
        match_count_factor = min(len(matches) / 3.0, 1.0)  # Max benefit from 3 matches
        
        base_confidence = min(total_weight, 1.0)
        adjusted_confidence = base_confidence * (0.7 + 0.3 * match_count_factor)
        
        return min(adjusted_confidence, 1.0)


class RealTimeOptimizer:
    """Optimization for real-time monitoring system"""
    
    def __init__(self):
        self.monitor_cache = {}
        self.processing_queue = []
        self.batch_size = 50
        self.batch_timeout = 5.0  # seconds
        self.last_batch_time = time.time()
    
    def optimize_monitoring_performance(self):
        """Apply optimizations to real-time monitoring"""
        
        # Cache active monitors
        self._cache_active_monitors()
        
        # Optimize signal processing
        self._optimize_signal_processing()
        
        # Setup batch processing
        self._setup_batch_processing()
    
    def _cache_active_monitors(self):
        """Cache active monitors for faster access"""
        active_monitors = list(
            RealTimeMonitor.objects
            .filter(is_active=True)
            .prefetch_related('monitoringevent_set')
        )
        
        self.monitor_cache = {
            monitor.id: monitor for monitor in active_monitors
        }
        
        logger.info(f"Cached {len(active_monitors)} active monitors")
    
    def _optimize_signal_processing(self):
        """Optimize Django signal processing"""
        # Configure signal processing for better performance
        from django.db import transaction
        
        # Use database transactions for signal processing
        transaction.set_autocommit(False)
    
    def _setup_batch_processing(self):
        """Setup batch processing for monitoring events"""
        def process_batch():
            if not self.processing_queue:
                return
            
            batch = self.processing_queue[:self.batch_size]
            self.processing_queue = self.processing_queue[self.batch_size:]
            
            # Process batch of events
            self._process_event_batch(batch)
            
            self.last_batch_time = time.time()
        
        # Setup periodic batch processing
        import threading
        def batch_processor():
            while True:
                time.sleep(1.0)  # Check every second
                
                current_time = time.time()
                should_process = (
                    len(self.processing_queue) >= self.batch_size or
                    (self.processing_queue and 
                     current_time - self.last_batch_time > self.batch_timeout)
                )
                
                if should_process:
                    try:
                        process_batch()
                    except Exception as e:
                        logger.error(f"Batch processing error: {e}")
        
        batch_thread = threading.Thread(target=batch_processor, daemon=True)
        batch_thread.start()
    
    def add_to_processing_queue(self, event_data: Dict[str, Any]):
        """Add event to processing queue for batch processing"""
        self.processing_queue.append(event_data)
    
    def _process_event_batch(self, batch: List[Dict[str, Any]]):
        """Process a batch of monitoring events efficiently"""
        from .models import MonitoringEvent
        
        # Create events in batch
        events_to_create = []
        
        for event_data in batch:
            event = MonitoringEvent(
                monitor_id=event_data.get('monitor_id'),
                event_type=event_data.get('event_type'),
                event_data=event_data.get('data', {}),
                created_at=timezone.now()
            )
            events_to_create.append(event)
        
        # Bulk create for better performance
        MonitoringEvent.objects.bulk_create(events_to_create, batch_size=50)
        
        logger.debug(f"Processed batch of {len(batch)} monitoring events")


class DatabaseOptimizer:
    """Database-specific optimizations"""
    
    @staticmethod
    def analyze_query_performance():
        """Analyze and report on query performance"""
        from django.db import connection
        
        # Get slow queries
        with connection.cursor() as cursor:
            # PostgreSQL specific query to find slow queries
            if 'postgresql' in connection.vendor:
                cursor.execute("""
                    SELECT query, mean_time, calls, total_time
                    FROM pg_stat_statements 
                    WHERE mean_time > 100  -- queries slower than 100ms
                    ORDER BY mean_time DESC 
                    LIMIT 10
                """)
                
                slow_queries = cursor.fetchall()
                
                if slow_queries:
                    logger.warning("Found slow database queries:")
                    for query, mean_time, calls, total_time in slow_queries:
                        logger.warning(f"Query: {query[:100]}... Mean: {mean_time}ms Calls: {calls}")
                
            # General query analysis
            total_queries = len(connection.queries)
            if total_queries > 50:
                logger.warning(f"High number of queries in this request: {total_queries}")
    
    @staticmethod
    def optimize_database_settings():
        """Apply database optimization settings"""
        from django.db import connection
        
        with connection.cursor() as cursor:
            if 'postgresql' in connection.vendor:
                # PostgreSQL optimizations
                try:
                    cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_stat_statements")
                    cursor.execute("SET shared_preload_libraries = 'pg_stat_statements'")
                    logger.info("PostgreSQL query monitoring enabled")
                except Exception as e:
                    logger.debug(f"Could not enable PostgreSQL optimizations: {e}")
            
            elif 'mysql' in connection.vendor:
                # MySQL optimizations
                try:
                    cursor.execute("SET SESSION query_cache_type = ON")
                    cursor.execute("SET SESSION query_cache_size = 67108864")  # 64MB
                    logger.info("MySQL query cache optimizations applied")
                except Exception as e:
                    logger.debug(f"Could not apply MySQL optimizations: {e}")


def optimize_discovery_system():
    """Main function to apply all optimizations to the discovery system"""
    logger.info("Starting discovery system optimization")
    
    try:
        # Initialize optimizers
        perf_optimizer = PerformanceOptimizer()
        classification_optimizer = ClassificationEngineOptimizer()
        realtime_optimizer = RealTimeOptimizer()
        
        # Apply database optimizations
        perf_optimizer.optimize_classification_queries()
        DatabaseOptimizer.optimize_database_settings()
        
        # Optimize classification engine
        classification_optimizer.precompile_regex_patterns()
        
        # Optimize real-time monitoring
        realtime_optimizer.optimize_monitoring_performance()
        
        # Clean up old data
        perf_optimizer.cleanup_old_data()
        
        logger.info("Discovery system optimization completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error during discovery system optimization: {e}")
        return False


# Performance monitoring decorator
def monitor_performance(func: Callable) -> Callable:
    """Decorator to monitor function performance"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        start_queries = len(connection.queries)
        
        try:
            result = func(*args, **kwargs)
            
            end_time = time.time()
            end_queries = len(connection.queries)
            
            execution_time = end_time - start_time
            query_count = end_queries - start_queries
            
            # Log performance metrics
            if execution_time > 1.0 or query_count > 10:
                logger.info(
                    f"Performance: {func.__name__} took {execution_time:.3f}s "
                    f"with {query_count} queries"
                )
            
            return result
            
        except Exception as e:
            end_time = time.time()
            execution_time = end_time - start_time
            logger.error(f"Error in {func.__name__} after {execution_time:.3f}s: {e}")
            raise
            
    return wrapper


if __name__ == '__main__':
    # Run optimization when called directly
    success = optimize_discovery_system()
    if success:
        print("Discovery system optimization completed successfully")
    else:
        print("Discovery system optimization failed - check logs for details")
