"""
Seed a candidate user + front-desk (or custom) job application with analyzed CV
and shortlisted status so a recruiter can schedule an interview from the frontend.

Usage:
    python manage.py seed_shortlisted_candidate
    python manage.py seed_shortlisted_candidate --first-name Rigbe --last-name Welu \\
        --email rigbe.welu@example.com --recruiter-email rigbe1221@gmail.com
"""
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.users.models import CandidateUser, RecruiterUser
from apps.job.models import Job
from apps.candidate.models import Candidate


class Command(BaseCommand):
    help = "Seed a shortlisted candidate with analyzed CV on a job owned by a recruiter."

    def add_arguments(self, parser):
        parser.add_argument('--first-name', default='Rigbe')
        parser.add_argument('--last-name', default='Welu')
        parser.add_argument('--email', default='rigbe.welu@example.com')
        parser.add_argument(
            '--recruiter-email',
            default='rigbe1221@gmail.com',
            help='Recruiter who owns the job (log into the frontend with this account).',
        )
        parser.add_argument('--job-title', default='Front Desk Receptionist')
        parser.add_argument(
            '--department',
            default=Job.Department.FRONT_OFFICE,
            help='Job department code (default: front_office).',
        )
        parser.add_argument('--ai-score', type=int, default=88)
        parser.add_argument(
            '--password',
            default='Testpass123!',
            help='Password for the candidate user if created (dev only).',
        )

    def handle(self, *args, **options):
        first_name = options['first_name'].strip()
        last_name = options['last_name'].strip()
        email = options['email'].strip().lower()
        recruiter_email = options['recruiter_email']
        job_title = options['job_title'].strip()
        department = options['department']
        ai_score = options['ai_score']
        password = options['password']

        try:
            recruiter = RecruiterUser.objects.get(user__email=recruiter_email)
        except RecruiterUser.DoesNotExist:
            raise CommandError(f"No recruiter found with email '{recruiter_email}'.")

        candidate_user, user_created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': email,
                'first_name': first_name,
                'last_name': last_name,
            },
        )
        if user_created:
            candidate_user.set_password(password)
            candidate_user.save()
        else:
            candidate_user.first_name = first_name
            candidate_user.last_name = last_name
            candidate_user.save(update_fields=['first_name', 'last_name'])

        CandidateUser.objects.get_or_create(user=candidate_user)

        job, _ = Job.objects.get_or_create(
            title=job_title,
            posted_by=recruiter,
            defaults={
                'description': (
                    f'{job_title} role focused on guest check-in/out, reservations, '
                    'and delivering a warm first impression for hotel guests.'
                ),
                'requirements': (
                    '1–3 years front office or reception experience. '
                    'Strong communication, customer service, and basic PMS familiarity.'
                ),
                'department': department,
                'shift_type': Job.ShiftType.ROTATING,
                'employment_type': Job.EmploymentType.FULL_TIME,
                'location': 'Addis Ababa',
                'is_active': True,
                'core_skills': ['Customer Service', 'Communication', 'Front Office', 'Reservations'],
            },
        )

        cv_text = (
            f'{first_name} {last_name} — Front desk professional with 4 years of experience '
            'in hotel reception, guest check-in/out, reservations, and handling guest inquiries. '
            'Proficient with Opera PMS, multilingual guest support, and coordinating with '
            'housekeeping and concierge teams.'
        )
        ai_fields = {
            'cv_filename': f'{first_name.lower()}_{last_name.lower()}_front_desk_cv.pdf',
            'cv_text': cv_text,
            'cv_uploaded_at': timezone.now(),
            'cv_status': Candidate.CVStatus.ANALYZED,
            'ai_score': ai_score,
            'ai_summary': (
                f'Strong front desk profile with solid guest-facing experience. '
                f'{first_name} demonstrates clear communication skills and front office readiness.'
            ),
            'ai_strengths': [
                'Guest relations',
                'Front desk operations',
                'Reservations handling',
                'Professional communication',
            ],
            'ai_weaknesses': ['Limited night-shift experience noted'],
            'ai_skills': ['Customer Service', 'Front Office', 'Opera PMS', 'Communication'],
            'ai_feedback': 'Recommended for interview — CV score exceeds shortlist threshold.',
            'ai_confidence': Candidate.Confidence.HIGH,
            'status': Candidate.Status.SHORTLISTED,
        }

        application, app_created = Candidate.objects.get_or_create(
            user=candidate_user,
            job=job,
            defaults=ai_fields,
        )
        if not app_created:
            for field, value in ai_fields.items():
                setattr(application, field, value)
            application.save()

        self.stdout.write(self.style.SUCCESS('Shortlisted candidate seeded.'))
        self.stdout.write('')
        self.stdout.write(f"  Recruiter (log in as): {recruiter.user.email}")
        self.stdout.write(f"  Candidate:             {first_name} {last_name} ({email})")
        if user_created:
            self.stdout.write(f"  Candidate password:    {password}  (dev only)")
        self.stdout.write(f"  Job:                   {job.title} ({job.id})")
        self.stdout.write(f"  AI score:              {application.ai_score}")
        self.stdout.write(f"  Status:                {application.status}")
        self.stdout.write(self.style.WARNING(f"  CANDIDATE_ID = {application.id}"))
        self.stdout.write('')
        self.stdout.write(
            'Open the recruiter Candidates page, find this candidate, and schedule an interview '
            '(paste your Google Meet link in the form).'
        )
