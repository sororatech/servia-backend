from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/test/$', consumers.TestConsumer.as_asgi()),
    re_path(r'ws/interview/(?P<interview_id>\w+)/$', consumers.InterviewConsumer.as_asgi()),
]