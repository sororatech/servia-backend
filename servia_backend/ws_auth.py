"""WebSocket authentication middleware.

Resolves the connecting user from (in priority order):
  1. a ``?token=<key>`` query-string param (used by the interview bot), then
  2. the httpOnly ``auth_token`` cookie set at login (used by browser clients), then
  3. an ``["auth", "<key>"]`` WebSocket subprotocol (legacy/explicit clients).

This avoids exposing any auth token to client-side JavaScript: browsers send the
httpOnly cookie automatically on the WebSocket handshake.
"""
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.sessions import CookieMiddleware
from django.contrib.auth.models import AnonymousUser


@database_sync_to_async
def _resolve_user(token_key):
    if not token_key:
        return AnonymousUser()
    try:
        from rest_framework.authtoken.models import Token

        return Token.objects.select_related("user").get(key=token_key).user
    except Exception:
        return AnonymousUser()


def _token_from_scope(scope):
    query_string = scope.get("query_string", b"")
    if query_string:
        params = parse_qs(query_string.decode())
        token = params.get("token", [None])[0]
        if token:
            return token

    cookies = scope.get("cookies") or {}
    if cookies.get("auth_token"):
        return cookies["auth_token"]

    subprotocols = scope.get("subprotocols") or []
    if len(subprotocols) >= 2 and subprotocols[0] == "auth":
        return subprotocols[1]

    return None


class TokenAuthMiddleware:
    """Populate ``scope['user']`` from a DRF token (cookie/query/subprotocol)."""

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        scope["user"] = await _resolve_user(_token_from_scope(scope))
        return await self.inner(scope, receive, send)


def TokenAuthMiddlewareStack(inner):
    # CookieMiddleware populates scope["cookies"] before we read the auth cookie.
    return CookieMiddleware(TokenAuthMiddleware(inner))
