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
    # 🔍 DEBUG: Print what we actually received
        print(f"\n🔍 DEBUG RecruiterUserSerializer.create():")
        print(f"   validated_data keys: {list(validated_data.keys())}")
        print(f"   'user' in validated_data: {'user' in validated_data}")
        if 'user' in validated_data:
            print(f"   user_data type: {type(validated_data['user'])}")
            print(f"   user_data: {validated_data['user']}")
            print(f"   department: {validated_data.get('department')}")
            print(f"   role: {validated_data.get('role')}\n")
    
        user_data = validated_data.pop('user')
        user_serializer = UserRegistrationSerializer(data=user_data)
        user_serializer.is_valid(raise_exception=True)
        user = user_serializer.save()
        recruiter = RecruiterUser.objects.create(user=user, **validated_data)
        return recruiter
class UserProfileSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for user profile.
    Includes user_type and profile-specific fields.
    """
    user_type = serializers.SerializerMethodField()
    profile = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'user_type', 'profile', 'date_joined']
        read_only_fields = ['id', 'email', 'date_joined']
    
    def get_user_type(self, obj):
        if hasattr(obj, 'recruiter_profile'):
            return 'recruiter'
        elif hasattr(obj, 'candidate_profile'):
            return 'candidate'
        elif obj.is_superuser:
            return 'admin'
        return 'unknown'
    
    def get_profile(self, obj):
        if hasattr(obj, 'recruiter_profile'):
            recruiter = obj.recruiter_profile
            return {
                'id': str(recruiter.id),
                'department': recruiter.department,
                'role': recruiter.role,
                'is_active': recruiter.is_active,
            }
        elif hasattr(obj, 'candidate_profile'):
            candidate = obj.candidate_profile
            return {
                'id': str(candidate.id),
                'phone': candidate.phone,
                'nationality': candidate.nationality,
                'profile_photo': candidate.profile_photo,
            }
        return None


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating basic user fields.
    Email is read-only for security.
    """
    class Meta:
        model = User
        fields = ['first_name', 'last_name']
        read_only_fields = ['email', 'username']


class RecruiterProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating recruiter-specific fields."""
    class Meta:
        model = RecruiterUser
        fields = ['department', 'role']


class CandidateProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating candidate-specific fields."""
    class Meta:
        model = CandidateUser
        fields = ['phone', 'nationality', 'profile_photo']