
# --- FIX FOR DRF DUPLICATE CONVERTER CRASH ---
import rest_framework.urlpatterns

# Save the original function DRF is using
_original_drf_register = rest_framework.urlpatterns.register_converter

# Create a safe version that ignores duplicates
def _safe_register(converter, type_name):
    try:
        _original_drf_register(converter, type_name)
    except ValueError:
        pass  # Ignore the "already registered" error

# Replace DRF's function with our safe version
rest_framework.urlpatterns.register_converter = _safe_register



from .celery import app as celery_app

__all__ = ('celery_app',)



