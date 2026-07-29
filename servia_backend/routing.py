from django.urls import re_path
from apps.interview.consumers import InterviewConsumer
from websocket.consumers import TestConsumer

websocket_urlpatterns = [
    re_path(r'ws/test/$', TestConsumer.as_asgi()),
    re_path(r'ws/interview/(?P<interview_id>[-\w]+)/$', InterviewConsumer.as_asgi()),
]
