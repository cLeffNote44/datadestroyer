from django.core.management.base import BaseCommand
from django.utils import timezone
from exposures.models import DeletionRequest, DeletionStatus, DeletionTarget, PurgeJob, PurgeJobStatus
from documents.models import Document, DocumentStatus
from django.db import transaction


class Command(BaseCommand):
    help = "Purges due deletion requests by marking documents deleted and updating statuses"

    def handle(self, *args, **options):
        job = PurgeJob.objects.create(status=PurgeJobStatus.RUNNING, started_at=timezone.now())
        succeeded = 0
        failed = 0
        logs = []
        try:
            due = DeletionRequest.objects.select_related("user", "document").filter(
                status__in=[DeletionStatus.APPROVED, DeletionStatus.SCHEDULED],
                scheduled_for__lte=timezone.now(),
            )
            total = due.count()
            job.items_total = total
            job.save(update_fields=["items_total"])

            for req in due:
                req.status = DeletionStatus.IN_PROGRESS
                req.started_at = timezone.now()
                req.save(update_fields=["status", "started_at", "updated_at"])
                try:
                    with transaction.atomic():
                        if req.target == DeletionTarget.DOCUMENT or req.document_id:
                            doc = req.document
                            if doc:
                                doc.mark_as_deleted()
                            else:
                                raise ValueError("Document not found")
                        elif req.target == DeletionTarget.USER_ALL_DATA:
                            for doc in Document.objects.filter(owner=req.user, status__in=[DocumentStatus.ACTIVE, DocumentStatus.SCHEDULED_DELETE]):
                                doc.mark_as_deleted()
                        elif req.target == DeletionTarget.CATEGORY and req.category_id:
                            for doc in Document.objects.filter(owner=req.user, category_id=req.category_id, status__in=[DocumentStatus.ACTIVE, DocumentStatus.SCHEDULED_DELETE]):
                                doc.mark_as_deleted()
                        else:
                            raise ValueError("Unsupported or invalid target")
                        req.status = DeletionStatus.COMPLETED
                        req.completed_at = timezone.now()
                        req.save(update_fields=["status", "completed_at", "updated_at"])
                        succeeded += 1
                        logs.append({"request": str(req.id), "result": "completed"})
                except Exception as e:
                    req.status = DeletionStatus.FAILED
                    req.failure_reason = str(e)
                    req.save(update_fields=["status", "failure_reason", "updated_at"])
                    failed += 1
                    logs.append({"request": str(req.id), "result": "failed", "error": str(e)})

            job.status = PurgeJobStatus.COMPLETED if failed == 0 else PurgeJobStatus.FAILED
            job.items_succeeded = succeeded
            job.items_failed = failed
            job.finished_at = timezone.now()
            job.log = logs
            job.save(update_fields=["status", "items_succeeded", "items_failed", "finished_at", "log"])

        except Exception as e:
            job.status = PurgeJobStatus.FAILED
            job.finished_at = timezone.now()
            logs.append({"error": str(e)})
            job.log = logs
            job.save(update_fields=["status", "finished_at", "log"])
            raise

