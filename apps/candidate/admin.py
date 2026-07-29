from django.contrib import admin
from .models import Candidate, ActivityLog

admin.site.register(Candidate)
admin.site.register(ActivityLog)