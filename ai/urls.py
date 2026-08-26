from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ChatView, ConversationViewSet

router = DefaultRouter()
router.register("conversations", ConversationViewSet, basename="ai-conversations")

urlpatterns = [
    path("chat/", ChatView.as_view(), name="ai-chat"),
] + router.urls
