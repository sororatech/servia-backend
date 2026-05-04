from rest_framework import serializers
from django.contrib.auth.models import User
from .models import CandidateUser, RecruiterUser
from django.core.exceptions import ValidationError as DjangoValidationError
from django.contrib.auth.password_validation import validate_password
class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for the built-in User model.
    Password is write-only.
    """
    password = serializers.CharField(write_only=True, validators=[validate_password])
    # Make username optional (it will be auto-filled)
    username = serializers.CharField(required=False)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'password']
        read_only_fields = ['id']

    def validate(self, data):
        # If username not provided, set it to email
        if 'username' not in data or not data['username']:
            data['username'] = data.get('email')
        return data

    def create(self, validated_data):
        
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)  
        user.save()
        return user


class CandidateUserSerializer(serializers.ModelSerializer):
    """
    Serializer for CandidateUser profile.
    Includes nested User data.
    """
    user = UserRegistrationSerializer()  # uses our custom registration serializer

    class Meta:
        model = CandidateUser
        fields = ['id', 'user', 'phone', 'nationality', 'profile_photo', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user_serializer = UserRegistrationSerializer(data=user_data)
        user_serializer.is_valid(raise_exception=True)
        user = user_serializer.save()
        candidate = CandidateUser.objects.create(user=user, **validated_data)
        return candidate


class RecruiterUserSerializer(serializers.ModelSerializer):
    """
    Serializer for RecruiterUser profile.
    Includes nested User data.
    """
    user = UserRegistrationSerializer()

    class Meta:
        model = RecruiterUser
        fields = ['id', 'user', 'department', 'role', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user_serializer = UserRegistrationSerializer(data=user_data)
        user_serializer.is_valid(raise_exception=True)
        user = user_serializer.save()
        recruiter = RecruiterUser.objects.create(user=user, **validated_data)
        return recruiter