from django.db import migrations
from django.contrib.auth import get_user_model
from apps.users.models import CandidateUser, RecruiterUser

User = get_user_model()

def create_default_accounts(apps, schema_editor):
    """
    Create default admin, recruiter, and candidate accounts.
    Safe to run multiple times (idempotent).
    """
    # 1. Admin Account
    if not User.objects.filter(email='admin@servia.com').exists():
        admin = User.objects.create_superuser(
            username='admin@servia.com',
            email='admin@servia.com',
            password='Admin@Servia123!'
        )
        RecruiterUser.objects.create(
            user=admin, 
            role=RecruiterUser.Role.ADMIN, 
            is_active=True
        )
        print("✅ Admin account created: admin@servia.com")

    # 2. Recruiter Account
    if not User.objects.filter(email='recruiter@servia.com').exists():
        recruiter = User.objects.create_user(
            username='recruiter@servia.com',
            email='recruiter@servia.com',
            password='Recruiter@Servia123!'
        )
        RecruiterUser.objects.create(
            user=recruiter, 
            role=RecruiterUser.Role.RECRUITER, 
            is_active=True
        )
        print("✅ Recruiter account created: recruiter@servia.com")

    # 3. Candidate Account
    if not User.objects.filter(email='candidate@servia.com').exists():
        candidate = User.objects.create_user(
            username='candidate@servia.com',
            email='candidate@servia.com',
            password='Candidate@Servia123!'
        )
        CandidateUser.objects.create(user=candidate)
        print("✅ Candidate account created: candidate@servia.com")

class Migration(migrations.Migration):
  
    dependencies = [
        ('users', '0005_merge_20260611_1302'),  
    ]

    operations = [
        migrations.RunPython(create_default_accounts),
    ]