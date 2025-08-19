"""
Management command for running automated governance workflows
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction
import json
import sys

from discovery.models import DataAsset, ClassificationResult
from discovery.governance import GovernanceOrchestrator


class Command(BaseCommand):
    help = 'Run automated governance workflows on classified data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--asset-id',
            type=int,
            help='Process governance for a specific asset ID'
        )
        
        parser.add_argument(
            '--classification-id',
            type=int,
            help='Process governance for a specific classification result ID'
        )
        
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Number of assets to process in each batch (default: 100)'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run in dry-run mode without making changes'
        )
        
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force processing even if governance was already applied'
        )
        
        parser.add_argument(
            '--retention-sweep',
            action='store_true',
            help='Run retention sweep instead of governance processing'
        )
        
        parser.add_argument(
            '--compliance-report',
            action='store_true',
            help='Generate compliance report'
        )
        
        parser.add_argument(
            '--framework',
            type=str,
            choices=['GDPR', 'HIPAA', 'PCI_DSS', 'SOC2'],
            help='Filter compliance report by framework'
        )
        
        parser.add_argument(
            '--output-file',
            type=str,
            help='Output file for reports (JSON format)'
        )

    def handle(self, *args, **options):
        orchestrator = GovernanceOrchestrator()
        
        # Handle retention sweep
        if options['retention_sweep']:
            return self._handle_retention_sweep(orchestrator, options)
        
        # Handle compliance report
        if options['compliance_report']:
            return self._handle_compliance_report(orchestrator, options)
        
        # Handle governance processing
        return self._handle_governance_processing(orchestrator, options)

    def _handle_governance_processing(self, orchestrator, options):
        """Handle governance workflow processing"""
        start_time = timezone.now()
        
        self.stdout.write(
            self.style.SUCCESS(f"Starting governance processing at {start_time}")
        )
        
        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING("Running in DRY-RUN mode - no changes will be made")
            )
        
        # Get classification results to process
        if options['classification_id']:
            try:
                classification_results = [ClassificationResult.objects.get(id=options['classification_id'])]
            except ClassificationResult.DoesNotExist:
                raise CommandError(f"Classification result {options['classification_id']} not found")
        
        elif options['asset_id']:
            try:
                asset = DataAsset.objects.get(id=options['asset_id'])
                classification_results = ClassificationResult.objects.filter(data_asset=asset)
                if not classification_results.exists():
                    raise CommandError(f"No classification results found for asset {options['asset_id']}")
            except DataAsset.DoesNotExist:
                raise CommandError(f"Asset {options['asset_id']} not found")
        
        else:
            # Process all unprocessed classification results
            filter_kwargs = {}
            if not options['force']:
                # Only process assets that haven't had governance applied
                filter_kwargs['data_asset__metadata__applied_policies__isnull'] = True
            
            classification_results = ClassificationResult.objects.filter(**filter_kwargs)
        
        total_results = classification_results.count()
        
        if total_results == 0:
            self.stdout.write(
                self.style.WARNING("No classification results found to process")
            )
            return
        
        self.stdout.write(f"Found {total_results} classification results to process")
        
        # Process in batches
        batch_size = options['batch_size']
        processed_count = 0
        success_count = 0
        error_count = 0
        
        for batch_start in range(0, total_results, batch_size):
            batch_end = min(batch_start + batch_size, total_results)
            batch = classification_results[batch_start:batch_end]
            
            self.stdout.write(f"Processing batch {batch_start + 1}-{batch_end} of {total_results}")
            
            for classification_result in batch:
                try:
                    if options['dry_run']:
                        # In dry run, just validate what would be done
                        self._dry_run_governance(orchestrator, classification_result)
                        success_count += 1
                    else:
                        # Actually process governance
                        governance_result = orchestrator.process_classification_result(classification_result)
                        
                        if governance_result['status'] == 'success':
                            success_count += 1
                            self.stdout.write(
                                f"✓ Processed asset {classification_result.data_asset.id}: "
                                f"{', '.join(governance_result['governance_actions'])}"
                            )
                        else:
                            error_count += 1
                            self.stdout.write(
                                self.style.ERROR(
                                    f"✗ Failed to process asset {classification_result.data_asset.id}: "
                                    f"{governance_result.get('error', 'Unknown error')}"
                                )
                            )
                    
                    processed_count += 1
                
                except Exception as e:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f"✗ Error processing classification {classification_result.id}: {str(e)}"
                        )
                    )
        
        # Summary
        end_time = timezone.now()
        duration = end_time - start_time
        
        self.stdout.write("\n" + "="*50)
        self.stdout.write(self.style.SUCCESS("GOVERNANCE PROCESSING SUMMARY"))
        self.stdout.write("="*50)
        self.stdout.write(f"Total processed: {processed_count}")
        self.stdout.write(f"Successful: {success_count}")
        self.stdout.write(f"Errors: {error_count}")
        self.stdout.write(f"Duration: {duration}")
        
        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING("\nThis was a DRY-RUN - no actual changes were made")
            )

    def _dry_run_governance(self, orchestrator, classification_result):
        """Simulate governance processing for dry run"""
        # Generate what tags would be applied
        tags = orchestrator.auto_tagger.generate_tags(classification_result)
        
        # Check what policies would match
        matching_policies = []
        for policy in orchestrator.policy_enforcer.policies:
            if policy.matches(classification_result):
                matching_policies.append(policy.name)
        
        # Generate access recommendations
        access_recommendations = orchestrator.access_recommender.generate_recommendations(classification_result)
        
        self.stdout.write(
            f"  Asset {classification_result.data_asset.id} ({classification_result.classification_type}):"
        )
        self.stdout.write(f"    - Would apply tags: {', '.join(tags)}")
        self.stdout.write(f"    - Would apply policies: {', '.join(matching_policies)}")
        self.stdout.write(f"    - Access priority: {access_recommendations['priority']}")

    def _handle_retention_sweep(self, orchestrator, options):
        """Handle retention sweep operations"""
        self.stdout.write(
            self.style.SUCCESS("Starting retention sweep")
        )
        
        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING("Running in DRY-RUN mode - no assets will be retained")
            )
        
        sweep_result = orchestrator.run_retention_sweep(dry_run=options['dry_run'])
        
        # Display results
        self.stdout.write("\n" + "="*50)
        self.stdout.write(self.style.SUCCESS("RETENTION SWEEP SUMMARY"))
        self.stdout.write("="*50)
        self.stdout.write(f"Sweep ID: {sweep_result['sweep_id']}")
        self.stdout.write(f"Total processed: {sweep_result['total_processed']}")
        self.stdout.write(f"Total {'would be ' if options['dry_run'] else ''}retained: {sweep_result['total_retained']}")
        self.stdout.write(f"Errors: {len(sweep_result['errors'])}")
        
        if sweep_result['errors']:
            self.stdout.write("\nErrors:")
            for error in sweep_result['errors']:
                self.stdout.write(
                    self.style.ERROR(f"  Asset {error['asset_id']}: {error['error']}")
                )
        
        # Save to file if requested
        if options['output_file']:
            with open(options['output_file'], 'w') as f:
                json.dump(sweep_result, f, indent=2, default=str)
            self.stdout.write(f"\nResults saved to {options['output_file']}")

    def _handle_compliance_report(self, orchestrator, options):
        """Handle compliance report generation"""
        self.stdout.write(
            self.style.SUCCESS("Generating compliance report")
        )
        
        framework = options.get('framework')
        if framework:
            self.stdout.write(f"Filtering by framework: {framework}")
        
        report = orchestrator.generate_compliance_report(framework=framework)
        
        # Display summary
        self.stdout.write("\n" + "="*50)
        self.stdout.write(self.style.SUCCESS("COMPLIANCE REPORT SUMMARY"))
        self.stdout.write("="*50)
        self.stdout.write(f"Report ID: {report['report_id']}")
        self.stdout.write(f"Total assets: {report['summary']['total_assets']}")
        self.stdout.write(f"Compliant assets: {report['summary']['compliant_assets']}")
        self.stdout.write(f"Non-compliant assets: {report['summary']['non_compliant_assets']}")
        self.stdout.write(f"Overall compliance score: {report['summary']['compliance_score']:.2%}")
        
        # Framework breakdown
        if report['framework_results']:
            self.stdout.write("\nFramework Compliance:")
            for fw_name, fw_data in report['framework_results'].items():
                compliance_pct = fw_data.get('compliance_percentage', 0)
                self.stdout.write(f"  {fw_name}: {compliance_pct:.1f}% ({fw_data['compliant_assets']}/{fw_data['total_assets']})")
        
        # Top violations
        if report['top_violations']:
            self.stdout.write("\nTop Violations:")
            for violation in report['top_violations'][:5]:
                self.stdout.write(f"  {violation['violation']}: {violation['count']} assets")
        
        # Recommendations
        if report['recommendations']:
            self.stdout.write("\nRecommendations:")
            for rec in report['recommendations'][:5]:
                self.stdout.write(f"  • {rec}")
        
        # Save to file if requested
        if options['output_file']:
            with open(options['output_file'], 'w') as f:
                json.dump(report, f, indent=2, default=str)
            self.stdout.write(f"\nFull report saved to {options['output_file']}")
