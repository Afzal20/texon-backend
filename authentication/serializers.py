from rest_framework import serializers
from django.contrib.auth import get_user_model
from dj_rest_auth.registration.serializers import RegisterSerializer as DjRestAuthRegisterSerializer

User = get_user_model()


class UserDetailsSerializer(serializers.ModelSerializer):
    pk = serializers.IntegerField(source="id", read_only=True)

    class Meta:
        model = User
        fields = (
            "pk",
            "id",
            "email",
            "first_name",
            "last_name",
            "phone",
            "avatar",
            "is_verified",
            "is_superuser",
            "is_staff",
            "date_joined",
        )
        read_only_fields = ("pk", "id", "email", "is_verified", "is_superuser", "is_staff", "date_joined")

class RegisterSerializer(DjRestAuthRegisterSerializer):
    """Email-only registration.

    The custom user model has no username field (ACCOUNT_USER_MODEL_USERNAME_FIELD=None),
    which makes dj-rest-auth's default serializer declare `username` with
    max_length=0 — an impossible constraint that broke signup entirely. Here the
    field is optional/blank; allauth skips username handling when it is disabled.
    """

    username = serializers.CharField(required=False, allow_blank=True, write_only=True)
    first_name = serializers.CharField(required=False, allow_blank=True, write_only=True)
    last_name = serializers.CharField(required=False, allow_blank=True, write_only=True)
    phone = serializers.CharField(required=False, allow_blank=True, write_only=True)

    def validate_username(self, username):
        # The user model has no username field, so skip the adapter's
        # clean_username which tries to query by a nonexistent field.
        return ""

    def validate(self, attrs):
        # Drop fields not part of allauth's signup flow.
        attrs.pop("username", None)
        self._first_name = attrs.pop("first_name", "")
        self._last_name = attrs.pop("last_name", "")
        self._phone = attrs.pop("phone", "")
        return super().validate(attrs)

    def get_cleaned_data(self):
        data = super().get_cleaned_data()
        data["first_name"] = self._first_name
        data["last_name"] = self._last_name
        data["phone"] = self._phone
        return data

    def save(self, request):
        user = super().save(request)
        phone = getattr(self, "_phone", "")
        if phone:
            user.phone = phone
            user.save(update_fields=["phone"])
        return user

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data.pop("username", None)
        return data
