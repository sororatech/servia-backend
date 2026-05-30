import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'servia_backend.settings')

app = Celery('servia_backend')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


app.conf.beat_schedule = {
    'check-system-health-every-5min': {
        'task': 'apps.users.tasks.check_system_health',
        'schedule': 300.0, 
    },
}
app.conf.timezone = 'UTC'