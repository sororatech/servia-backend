from django.contrib import admin
from .models import CandidateUser, RecruiterUser

admin.site.register(CandidateUser)
admin.site.register(RecruiterUser)