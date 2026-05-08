from django.apps import AppConfig

class CandidateConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.candidate'
    label = 'candidate'
    
    def ready(self):
        """Register signal handlers when app is ready"""
        import apps.candidate.signals  # noqa: F401