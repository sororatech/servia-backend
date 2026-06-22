"""
ASGI config for servia_backend project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/

"""

import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'servia_backend.settings')

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from servia_backend.routing import websocket_urlpatterns
from servia_backend.ws_auth import TokenAuthMiddlewareStack

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': TokenAuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
