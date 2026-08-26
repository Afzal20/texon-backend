from django.db.models import Max
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .llm import MAX_HISTORY_MESSAGES, stream_completion_sync, title_from_message
from .models import Conversation, Message
from .serializers import ConversationDetailSerializer, ConversationSerializer


class ConversationViewSet(viewsets.ModelViewSet):
    """Chat history — every user sees only their own conversations."""

    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "delete", "head", "options"]
    filterset_fields: list[str] = []
    search_fields = ["title"]
    ordering_fields = ["updated_at", "created_at"]

    def get_queryset(self):
        return (
            Conversation.objects.filter(user=self.request.user)
            .annotate(
                message_count=Max("messages__id"),
                last_message_at=Max("messages__created_at"),
            )
        )

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ConversationDetailSerializer
        return ConversationSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ChatView(APIView):
    """Non-streaming HTTP chat endpoint (used as WebSocket fallback on Vercel)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        text = (request.data.get("message") or "").strip()
        if not text:
            return Response({"detail": "Empty message."}, status=status.HTTP_400_BAD_REQUEST)
        if len(text) > 8000:
            return Response({"detail": "Message too long."}, status=status.HTTP_400_BAD_REQUEST)

        conversation_id = request.data.get("conversation_id")
        try:
            if conversation_id:
                conversation = Conversation.objects.get(id=conversation_id, user=request.user)
            else:
                conversation = Conversation.objects.create(user=request.user)
        except Conversation.DoesNotExist:
            return Response({"detail": "Conversation not found."}, status=status.HTTP_404_NOT_FOUND)

        # Save user message
        is_first = not conversation.messages.exists()
        user_message = Message.objects.create(conversation=conversation, role="user", content=text)
        if is_first:
            conversation.title = title_from_message(text)
            conversation.save(update_fields=["title", "updated_at"])
        else:
            conversation.save(update_fields=["updated_at"])

        # Build history and stream LLM response
        history = list(
            conversation.messages.order_by("-id")
            .values("role", "content")[:MAX_HISTORY_MESSAGES]
        )
        history = list(reversed(history))

        try:
            reply_parts = list(stream_completion_sync(history))
            content = "".join(reply_parts)
        except Exception:
            return Response(
                {"detail": "The AI service is unavailable right now. Please try again."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        assistant_message = Message.objects.create(
            conversation=conversation, role="assistant", content=content
        )
        conversation.save(update_fields=["updated_at"])

        return Response({
            "id": str(assistant_message.id),
            "response": content,
            "conversation_id": conversation.id,
        })
