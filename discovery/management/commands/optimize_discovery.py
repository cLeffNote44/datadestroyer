"""
Management command for optimizing the discovery system performance
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction
import time

from discovery.optimization import optimize_discovery_system, PerformanceOptimizer


class Command(BaseCommand):
    help = 'Optimize the discovery system for better performance'

    def add_arguments(self, parser):
        parser.add_argument(
            '--vacuum-db',
            action='store_true',
            help='Run database vacuum and analyze operations'
        )
        
        parser.add_argument(
            '--rebuild-indexes',
            action='store_true',
            help='Rebuild database indexes for optimal performance'
        )
        
        parser.add_argument(
            '--cleanup-data',
            action='store_true',
            help='Clean up old data to improve performance'
        )
        
        parser.add_argument(
            '--days-to-keep',
            type=int,
            default=90,
            help='Number of days of data to keep during cleanup (default: 90)'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )
        
        parser.add_argument(
            '--benchmark',
            action='store_true',
            help='Run performance benchmarks after optimization'
        )

    def handle(self, *args, **options):
        start_time = time.time()
        
        self.stdout.write(
            self.style.SUCCESS("Starting discovery system optimization...")
        )
        
        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING("Running in DRY-RUN mode - no changes will be made")
            )
        
        optimizer = PerformanceOptimizer()
        optimization_results = {}
        
        try:
            # Run general optimizations
            if not options['dry_run']:
                success = optimize_discovery_system()
                if success:
                    self.stdout.write("✓ General optimizations applied successfully")
                else:
                    self.stdout.write(
                        self.style.ERROR("✗ Some general optimizations failed")
                    )
            else:
                self.stdout.write("Would apply general system optimizations")
            
            # Database vacuum and analyze
            if options['vacuum_db']:
                self._vacuum_database(options['dry_run'])
            
            # Rebuild indexes
            if options['rebuild_indexes']:
                self._rebuild_indexes(options['dry_run'])
            
            # Clean up old data
            if options['cleanup_data']:
                cleanup_stats = self._cleanup_old_data(
                    options['days_to_keep'], 
                    options['dry_run']
                )
                optimization_results['cleanup'] = cleanup_stats
            
            # Run benchmarks
            if options['benchmark'] and not options['dry_run']:
                self._run_benchmarks()
            
            # Show optimization statistics
            self._show_optimization_stats(optimizer, optimization_results)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nOptimization completed successfully in {total_time:.2f} seconds"
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Optimization failed: {str(e)}")
            )
            raise CommandError(f"Optimization failed: {str(e)}")

    def _vacuum_database(self, dry_run=False):
        """Vacuum and analyze database for better performance"""
        from django.db import connection
        
        if dry_run:
            self.stdout.write("Would vacuum and analyze database")
            return
        
        try:
            with connection.cursor() as cursor:
                if 'postgresql' in connection.vendor:
                    # PostgreSQL vacuum and analyze
                    discovery_tables = [
                        'discovery_dataasset',
                        'discovery_classificationresult',
                        'discovery_monitoringevent',
                        'discovery_datadiscoveryinsight',
                        'discovery_classificationrule'
                    ]
                    
                    for table in discovery_tables:
                        self.stdout.write(f"Vacuuming {table}...")
                        cursor.execute(f"VACUUM ANALYZE {table}")
                    
                    self.stdout.write("✓ Database vacuum and analyze completed")
                    
                elif 'mysql' in connection.vendor:
                    # MySQL optimize tables
                    cursor.execute("SHOW TABLES LIKE 'discovery_%'")
                    tables = [row[0] for row in cursor.fetchall()]
                    
                    for table in tables:
                        self.stdout.write(f"Optimizing {table}...")
                        cursor.execute(f"OPTIMIZE TABLE {table}")
                    
                    self.stdout.write("✓ Database optimization completed")
                    
                else:
                    self.stdout.write(
                        self.style.WARNING("Database vacuum not supported for this database type")
                    )
                    
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Database vacuum failed: {str(e)}")
            )

    def _rebuild_indexes(self, dry_run=False):
        """Rebuild database indexes for optimal performance"""
        from django.db import connection
        
        if dry_run:
            self.stdout.write("Would rebuild database indexes")
            return
        
        try:
            optimizer = PerformanceOptimizer()
            optimizer.optimize_classification_queries()
            self.stdout.write("✓ Database indexes rebuilt successfully")
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Index rebuild failed: {str(e)}")
            )

    def _cleanup_old_data(self, days_to_keep=90, dry_run=False):
        """Clean up old data to improve performance"""
        if dry_run:
            # Estimate what would be cleaned up
            cutoff_date = timezone.now() - timezone.timedelta(days=days_to_keep)
            
            from discovery.models import MonitoringEvent, DataDiscoveryInsight, DataAsset
            
            old_events = MonitoringEvent.objects.filter(created_at__lt=cutoff_date).count()
            old_insights = DataDiscoveryInsight.objects.filter(
                created_at__lt=cutoff_date, is_resolved=True
            ).count()
            old_assets = DataAsset.objects.filter(
                last_scanned__lt=cutoff_date, is_active=False
            ).count()
            
            self.stdout.write(f"Would clean up:")
            self.stdout.write(f"  - {old_events} old monitoring events")
            self.stdout.write(f"  - {old_insights} resolved insights")
            self.stdout.write(f"  - {old_assets} inactive assets (mark as archived)")
            
            return {
                'monitoring_events': old_events,
                'resolved_insights': old_insights,
                'inactive_assets': old_assets
            }
        
        try:
            optimizer = PerformanceOptimizer()
            cleanup_stats = optimizer.cleanup_old_data(days_to_keep)
            
            self.stdout.write(f"✓ Data cleanup completed:")
            self.stdout.write(f"  - Cleaned {cleanup_stats['monitoring_events']} old monitoring events")
            self.stdout.write(f"  - Cleaned {cleanup_stats['resolved_insights']} resolved insights")
            self.stdout.write(f"  - Archived {cleanup_stats['inactive_assets']} inactive assets")
            
            return cleanup_stats
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Data cleanup failed: {str(e)}")
            )
            return {}

    def _run_benchmarks(self):
        """Run performance benchmarks after optimization"""
        self.stdout.write("\nRunning performance benchmarks...")
        
        try:
            from discovery.tests.test_runner import PerformanceBenchmarks
            
            # Classification engine benchmark
            classification_results = PerformanceBenchmarks.benchmark_classification_engine(50)
            self.stdout.write(f"Classification Engine:")
            self.stdout.write(f"  - Items per second: {classification_results['items_per_second']:.2f}")
            self.stdout.write(f"  - Avg time per item: {classification_results['avg_time_per_item']:.4f}s")
            
            # Governance orchestrator benchmark
            governance_results = PerformanceBenchmarks.benchmark_governance_orchestrator(25)
            self.stdout.write(f"Governance Orchestrator:")
            self.stdout.write(f"  - Assets per second: {governance_results['assets_per_second']:.2f}")
            self.stdout.write(f"  - Avg time per asset: {governance_results['avg_time_per_asset']:.4f}s")
            
            # API endpoints benchmark
            api_results = PerformanceBenchmarks.benchmark_api_endpoints(5)
            self.stdout.write(f"API Endpoints:")
            for endpoint, metrics in api_results.items():
                self.stdout.write(f"  {endpoint}: {metrics['avg_response_time']:.3f}s avg")
            
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f"Benchmark failed: {str(e)}")
            )

    def _show_optimization_stats(self, optimizer, results):
        """Show optimization statistics"""
        self.stdout.write("\n" + "="*50)
        self.stdout.write("OPTIMIZATION STATISTICS")
        self.stdout.write("="*50)
        
        stats = optimizer.optimization_stats
        self.stdout.write(f"Cache hits: {stats['cache_hits']}")
        self.stdout.write(f"Cache misses: {stats['cache_misses']}")
        self.stdout.write(f"Query optimizations: {stats['query_optimizations']}")
        self.stdout.write(f"Batch operations: {stats['batch_operations']}")
        
        if 'cleanup' in results:
            cleanup = results['cleanup']
            total_cleaned = sum(cleanup.values())
            self.stdout.write(f"Total items cleaned: {total_cleaned}")
        
        # Calculate cache hit ratio
        total_cache_requests = stats['cache_hits'] + stats['cache_misses']
        if total_cache_requests > 0:
            hit_ratio = stats['cache_hits'] / total_cache_requests
            self.stdout.write(f"Cache hit ratio: {hit_ratio:.2%}")
        
        self.stdout.write("="*50)
