from django.contrib.auth import get_user_model
from rest_framework import serializers
from apps.users.models import RecruiterUser, CandidateUser

User = get_user_model()


class RecruiterSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source="user.first_name")
    last_name = serializers.CharField(source="user.last_name")
    email = serializers.EmailField(source="user.email")

    class Meta:
        model = RecruiterUser
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "department",
            "role",
            "is_active",
            "created_at",
        ]

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})

        user = instance.user

        user.first_name = user_data.get("first_name", user.first_name)
        user.last_name = user_data.get("last_name", user.last_name)
        user.email = user_data.get("email", user.email)

        user.save()

        instance.department = validated_data.get(
            "department",
            instance.department
        )

        instance.role = validated_data.get(
            "role",
            instance.role
        )

        instance.save()

        return instance


class RecruiterCreateSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(write_only=True)
    last_name = serializers.CharField(write_only=True)
    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = RecruiterUser
        fields = [
            "first_name",
            "last_name",
            "email",
            "password",
            "department",
            "role",
        ]

    def create(self, validated_data):
        first_name = validated_data.pop("first_name")
        last_name = validated_data.pop("last_name")
        email = validated_data.pop("email")
        password = validated_data.pop("password")

        user = User.objects.create_user(
            username=email,
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=password
        )

        recruiter = RecruiterUser.objects.create(
            user=user,
            **validated_data
        )

        return recruiter


class CandidateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateUser
        fields = "__all__"