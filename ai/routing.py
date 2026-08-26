"""WebSocket URL routing (imported by config/asgi.py when present)."""

from django.urls import path

from .consumers import ChatConsumer

websocket_urlpatterns = [
    path("ws/ai/chat/", ChatConsumer.as_asgi()),
]
