from django.contrib import admin
from .models import AIReport, TemporaryAIResponse

admin.site.register(AIReport)
admin.site.register(TemporaryAIResponse)