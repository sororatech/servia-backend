from django.apps import AppConfig


class CandidateConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.candidate'
    label = 'candidate'
    
    def ready(self):
        """
        Register signal handlers when app is ready.
        This ensures signals are connected before any models are used.
        """
        # Import signals module to register receivers
        # noqa: F401 (imported but unused - this is intentional for signal registration)
        import apps.candidate.signals