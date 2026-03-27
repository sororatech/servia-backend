from django.core.management.base import BaseCommand
from apps.candidate.models import Candidate
from apps.ai_reports.tasks import analyze_cv_task


class Command(BaseCommand):
    help = "Re-trigger Gemini CV analysis for candidates missing ai_skills."

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Re-analyze all ANALYZED candidates, not just those missing ai_skills.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print which candidates would be queued without actually queuing them.',
        )

    def handle(self, *args, **options):
        if options['all']:
            qs = Candidate.objects.filter(
                cv_status__in=[Candidate.CVStatus.ANALYZED, Candidate.CVStatus.ERROR]
            )
        else:
            # Default: candidates that failed OR were analyzed but have no skills yet
            qs = Candidate.objects.filter(
                cv_status__in=[Candidate.CVStatus.ANALYZED, Candidate.CVStatus.ERROR],
                ai_skills=[],
            )

        qs = qs.select_related('user', 'job').exclude(cv_text__isnull=True).exclude(cv_text='')

        total = qs.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS("No candidates to reanalyze."))
            return

        dry_run = options['dry_run']
        self.stdout.write(
            f"{'[DRY RUN] ' if dry_run else ''}Found {total} candidate(s) to reanalyze.\n"
        )

        queued = 0
        skipped = 0
        for candidate in qs:
            job_desc = candidate.job.description if candidate.job.description else ''
            if not job_desc.strip():
                self.stdout.write(
                    self.style.WARNING(
                        f"  SKIP  {candidate.user.email} — job '{candidate.job.title}' has no description"
                    )
                )
                skipped += 1
                continue

            self.stdout.write(
                f"  {'WOULD QUEUE' if dry_run else 'QUEUING'}  "
                f"{candidate.user.get_full_name() or candidate.user.email} "
                f"— {candidate.job.title}"
            )

            if not dry_run:
                candidate.cv_status = Candidate.CVStatus.PROCESSING
                candidate.save(update_fields=['cv_status'])
                analyze_cv_task.delay(
                    str(candidate.id),
                    candidate.cv_text,
                    job_desc,
                )
            queued += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"\n{'Would queue' if dry_run else 'Queued'} {queued} task(s). Skipped {skipped}."
            )
        )
