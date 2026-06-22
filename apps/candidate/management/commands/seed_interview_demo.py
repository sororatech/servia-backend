"""
Seed a demo job + candidate application + scheduled interview so the
Google Meet bot flow can be tested end to end.

The interview is created with a real Google Meet link saved on the
`meet_link` field, which the bot then fetches from the backend (instead of
reading MEET_URL from its environment).

Usage:
    python manage.py seed_interview_demo
    python manage.py seed_interview_demo --candidate-email candidate1@example.com \
        --meet-link https://meet.google.com/eaj-jnxd-qum
"""
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.users.models import RecruiterUser
from apps.job.models import Job
from apps.candidate.models import Candidate
from apps.interview.models import Interview


class Command(BaseCommand):
    help = "Seed a demo job, candidate application and scheduled interview with a real Meet link."

    def add_arguments(self, parser):
        parser.add_argument(
            '--candidate-email',
            default='candidate1@example.com',
            help='Email of the candidate user the interview belongs to (must be the bot AUTH_TOKEN owner).',
        )
        parser.add_argument(
            '--meet-link',
            default='https://meet.google.com/eaj-jnxd-qum',
            help='Real Google Meet link to store on the interview.',
        )
        parser.add_argument(
            '--recruiter-email',
            default=None,
            help='Email of the recruiter that posts the job (defaults to the first recruiter).',
        )
        parser.add_argument(
            '--status',
            default=Candidate.Status.SHORTLISTED,
            help='Candidate application status (default: shortlisted, so the recruiter can schedule).',
        )
        parser.add_argument(
            '--no-interview',
            action='store_true',
            help='Do not pre-create an interview; let the recruiter schedule it from the frontend.',
        )

    def handle(self, *args, **options):
        candidate_email = options['candidate_email']
        meet_link = options['meet_link']
        recruiter_email = options['recruiter_email']
        candidate_status = options['status']
        no_interview = options['no_interview']

        # 1. Candidate user (the bot's AUTH_TOKEN owner).
        try:
            candidate_user = User.objects.get(email=candidate_email)
        except User.DoesNotExist:
            raise CommandError(f"No user found with email '{candidate_email}'.")

        if not candidate_user.first_name and not candidate_user.last_name:
            candidate_user.first_name = 'Demo'
            candidate_user.last_name = 'Candidate'
            candidate_user.save(update_fields=['first_name', 'last_name'])

        # 2. Recruiter that owns the job.
        if recruiter_email:
            try:
                recruiter = RecruiterUser.objects.get(user__email=recruiter_email)
            except RecruiterUser.DoesNotExist:
                raise CommandError(f"No recruiter found with email '{recruiter_email}'.")
        else:
            recruiter = RecruiterUser.objects.first()
            if recruiter is None:
                raise CommandError("No recruiter exists in the database to post the job.")

        # 3. Demo job posted by the recruiter.
        job, job_created = Job.objects.get_or_create(
            title='Demo Hotel Operations Manager',
            posted_by=recruiter,
            defaults={
                'description': 'Demo role for testing the interview bot flow.',
                'requirements': 'Demo requirements.',
                'department': Job.Department.MANAGEMENT,
                'shift_type': Job.ShiftType.FLEXIBLE,
                'employment_type': Job.EmploymentType.FULL_TIME,
                'location': 'Addis Ababa',
                'is_active': True,
            },
        )

        # 4. Candidate application (unique per user+job) with an analyzed CV and
        #    an AI score above the shortlist threshold so the data is realistic.
        ai_fields = {
            'cv_filename': 'demo_candidate_cv.pdf',
            'cv_text': (
                'Experienced hospitality professional with 8+ years in hotel operations, '
                'front office management, and guest relations across 4- and 5-star properties.'
            ),
            'cv_uploaded_at': timezone.now(),
            'cv_status': Candidate.CVStatus.ANALYZED,
            'ai_score': 85,
            'ai_summary': (
                'Strong operations background with proven leadership in front office and '
                'guest relations. Clear fit for a hotel operations management role.'
            ),
            'ai_strengths': [
                'Hotel operations leadership',
                'Front office management',
                'Guest relations',
            ],
            'ai_weaknesses': ['Limited exposure to revenue management software'],
            'ai_skills': ['Operations', 'Leadership', 'Customer Service', 'Scheduling'],
            'ai_feedback': 'Highly recommended for interview based on operations experience.',
            'ai_confidence': Candidate.Confidence.HIGH,
        }

        candidate, cand_created = Candidate.objects.get_or_create(
            user=candidate_user,
            job=job,
            defaults={'status': candidate_status, **ai_fields},
        )
        if not cand_created:
            candidate.status = candidate_status
            for field, value in ai_fields.items():
                setattr(candidate, field, value)
            candidate.save()

        # 5. Optionally pre-create a scheduled interview with the Meet link.
        interview = None
        if not no_interview:
            interview, iv_created = Interview.objects.get_or_create(
                candidate=candidate,
                job=job,
                status=Interview.Status.SCHEDULED,
                defaults={
                    'recruiter': recruiter,
                    'scheduled_time': timezone.now() + timedelta(hours=1),
                    'duration_minutes': 30,
                    'stage': Interview.Stage.STAGE_1,
                    'meet_link': meet_link,
                },
            )
            if not iv_created and interview.meet_link != meet_link:
                interview.meet_link = meet_link
                interview.save(update_fields=['meet_link', 'updated_at'])

        self.stdout.write(self.style.SUCCESS('Demo seed complete.'))
        self.stdout.write('')
        self.stdout.write(f"  Recruiter (job owner): {recruiter.user.email}")
        self.stdout.write(f"  Candidate user:        {candidate_user.email}")
        self.stdout.write(f"  Candidate status:      {candidate.status}")
        self.stdout.write(f"  Job:                   {job.title} ({job.id})")
        self.stdout.write(self.style.WARNING(f"  CANDIDATE_ID = {candidate.id}"))
        if interview is not None:
            self.stdout.write(self.style.WARNING(f"  INTERVIEW_ID = {interview.id}"))
            self.stdout.write(self.style.WARNING(f"  meet_link    = {interview.meet_link}"))
            self.stdout.write('')
            self.stdout.write("Put INTERVIEW_ID (or CANDIDATE_ID) in servia-bot/.env and leave MEET_URL unset.")
        else:
            self.stdout.write('')
            self.stdout.write("No interview pre-created. Schedule it from the frontend, then run the")
            self.stdout.write("bot with CANDIDATE_ID set (and MEET_URL unset) to fetch the saved link.")
