"""
Django management command to run data discovery scans
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.utils import timezone

from discovery.models import DiscoveryJob, DiscoveryStatus
from discovery.scanner import data_discovery_scanner
from discovery.signals import initialize_real_time_monitoring

User = get_user_model()


class Command(BaseCommand):
    help = 'Run data discovery and classification scans'

    def add_arguments(self, parser):
        parser.add_argument(
            '--apps',
            nargs='+',
            type=str,
            help='Specific apps to scan (default: all apps)'
        )
        
        parser.add_argument(
            '--models',
            nargs='+', 
            type=str,
            help='Specific models to scan (default: all models)'
        )
        
        parser.add_argument(
            '--job-name',
            type=str,
            default='Manual Discovery Scan',
            help='Name for the discovery job'
        )
        
        parser.add_argument(
            '--no-lineage',
            action='store_true',
            help='Skip data lineage detection'
        )
        
        parser.add_argument(
            '--no-insights',
            action='store_true', 
            help='Skip insight generation'
        )
        
        parser.add_argument(
            '--init-monitoring',
            action='store_true',
            help='Initialize real-time monitoring system'
        )
        
        parser.add_argument(
            '--user',
            type=str,
            help='Username of user running the scan (default: first superuser)'
        )

    def handle(self, *args, **options):
        try:
            # Initialize monitoring if requested
            if options['init_monitoring']:
                self.stdout.write("🔄 Initializing real-time monitoring system...")
                initialize_real_time_monitoring()
                self.stdout.write(
                    self.style.SUCCESS("✅ Real-time monitoring initialized successfully")
                )
            
            # Get or create user for the job
            user = None
            if options['user']:
                try:
                    user = User.objects.get(username=options['user'])
                except User.DoesNotExist:
                    raise CommandError(f"User '{options['user']}' does not exist")
            else:
                # Use first superuser
                user = User.objects.filter(is_superuser=True).first()
                if not user:
                    # Create a system user if no superuser exists
                    user = User.objects.create(
                        username='discovery_system',
                        email='system@discovery.local',
                        is_staff=True,
                        is_superuser=True
                    )
                    self.stdout.write(
                        self.style.WARNING("⚠️ Created system user for discovery jobs")
                    )

            # Create discovery job
            job = DiscoveryJob.objects.create(
                name=options['job_name'],
                description=f"Manual discovery scan via management command",
                job_type='full_scan',
                target_apps=options.get('apps', []),
                target_models=options.get('models', []),
                created_by=user,
                status=DiscoveryStatus.PENDING,
                configuration={
                    'include_lineage': not options['no_lineage'],
                    'include_insights': not options['no_insights'],
                    'command_line_run': True
                }
            )

            self.stdout.write(f"🚀 Starting discovery job: {job.name}")
            self.stdout.write(f"   Job ID: {job.id}")
            
            # Run the discovery scan
            result = data_discovery_scanner.run_full_discovery(
                discovery_job=job,
                target_apps=options.get('apps'),
                target_models=options.get('models'),
                include_lineage=not options['no_lineage'],
                include_insights=not options['no_insights']
            )

            # Report results
            self.stdout.write("\n" + "="*50)
            self.stdout.write("📊 DISCOVERY SCAN RESULTS")
            self.stdout.write("="*50)
            
            self.stdout.write(f"✅ Assets discovered: {result.assets_discovered}")
            self.stdout.write(f"🔍 Assets classified: {result.assets_classified}")
            
            if not options['no_lineage']:
                self.stdout.write(f"🔗 Lineage relationships: {result.lineage_relationships}")
            
            if not options['no_insights']:
                self.stdout.write(f"💡 Insights generated: {result.insights_generated}")
            
            self.stdout.write(f"⚡ Processing time: {result.processing_time:.2f}s")
            
            if result.errors_encountered > 0:
                self.stdout.write(
                    self.style.WARNING(f"⚠️ Errors encountered: {result.errors_encountered}")
                )
                if result.error_details:
                    self.stdout.write("Error details:")
                    for error in result.error_details[:5]:  # Show first 5 errors
                        self.stdout.write(f"  - {error}")
            
            # Final job status
            job.refresh_from_db()
            if job.status == DiscoveryStatus.COMPLETED:
                self.stdout.write(
                    self.style.SUCCESS(f"\n🎉 Discovery job completed successfully!")
                )
                
                # Show additional statistics
                if job.results_summary:
                    summary = job.results_summary
                    self.stdout.write(f"   Phases completed: {summary.get('phases_completed', 'N/A')}")
                    
            elif job.status == DiscoveryStatus.FAILED:
                self.stdout.write(
                    self.style.ERROR(f"\n❌ Discovery job failed!")
                )
                if job.error_log:
                    self.stdout.write("Error log:")
                    for line in job.error_log.split('\n')[:10]:  # Show first 10 lines
                        if line.strip():
                            self.stdout.write(f"  {line}")
            
            self.stdout.write(f"\n📋 Job details: DiscoveryJob ID {job.id}")
            
        except Exception as e:
            raise CommandError(f"Discovery scan failed: {str(e)}")
