"""
Reset a completed (or cancelled) interview back to scheduled so the bot can
resolve it again via /resolve-active/.

Usage:
    python manage.py reset_demo_interview
    python manage.py reset_demo_interview --interview-id 69a1f980-a117-403d-90a5-1f88fdae9b14
    python manage.py reset_demo_interview --candidate-id 8922e8ac-1818-4dbf-b0a5-0151ede608fc
"""
from django.core.management.base import BaseCommand, CommandError
from django.core.cache import cache

from apps.interview.consumers import follow_up_cache_key
from apps.interview.models import Interview, InterviewConversation


class Command(BaseCommand):
    help = (
        "Reset an interview to scheduled status for another bot test run "
        "(clears bot_join_status to pending)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--interview-id',
            default=None,
            help='Interview UUID to reset (defaults to the latest for the candidate).',
        )
        parser.add_argument(
            '--candidate-id',
            default='8922e8ac-1818-4dbf-b0a5-0151ede608fc',
            help='Demo candidate UUID (used when --interview-id is omitted).',
        )

    def handle(self, *args, **options):
        interview_id = options['interview_id']
        candidate_id = options['candidate_id']

        if interview_id:
            try:
                interview = Interview.objects.get(pk=interview_id)
            except Interview.DoesNotExist:
                raise CommandError(f"No interview found with id '{interview_id}'.")
        else:
            interview = (
                Interview.objects.filter(candidate_id=candidate_id)
                .order_by('-updated_at')
                .first()
            )
            if interview is None:
                raise CommandError(
                    f"No interview found for candidate '{candidate_id}'. "
                    "Run seed_interview_demo first or schedule one from the frontend."
                )

        previous_status = interview.status
        deleted_count, _ = InterviewConversation.objects.filter(
            interview_id=interview.id,
        ).delete()
        cache.delete(follow_up_cache_key(interview.id))

        interview.status = Interview.Status.SCHEDULED
        interview.bot_join_status = Interview.BotJoinStatus.PENDING
        interview.save(update_fields=['status', 'bot_join_status', 'updated_at'])

        self.stdout.write(self.style.SUCCESS('Interview reset for another bot run.'))
        self.stdout.write(f"  Previous status:     {previous_status}")
        self.stdout.write(f"  Cleared transcript:  {deleted_count} row(s)")
        self.stdout.write(f"  INTERVIEW_ID =        {interview.id}")
        self.stdout.write(f"  CANDIDATE_ID =        {interview.candidate_id}")
        self.stdout.write(f"  meet_link =           {interview.meet_link}")
        self.stdout.write('')
        self.stdout.write('Run the bot with CANDIDATE_ID set (MEET_URL unset).')
