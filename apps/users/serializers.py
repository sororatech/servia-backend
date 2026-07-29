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
    username = serializers.CharField(required=False)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'password', 'last_login', 'date_joined']
        read_only_fields = ['id', 'last_login', 'date_joined']

    def validate(self, data):
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
    Includes nested User data with last_login, date_joined, and applied_date.
    """
    user = UserRegistrationSerializer()
    date_joined = serializers.SerializerMethodField()
    last_login = serializers.SerializerMethodField()
    applied_date = serializers.SerializerMethodField()

    class Meta:
        model = CandidateUser
        fields = ['id', 'user', 'phone', 'nationality', 'profile_photo', 'created_at', 'updated_at', 'date_joined', 'last_login', 'applied_date']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_date_joined(self, obj):
        """Get date_joined from the related User model"""
        if obj.user and obj.user.date_joined:
            return obj.user.date_joined.isoformat()
        return None

    def get_last_login(self, obj):
        """Get last_login from the related User model"""
        if obj.user and obj.user.last_login:
            return obj.user.last_login.isoformat()
        return None

    def get_applied_date(self, obj):
        """
        Find the date this user submitted their very first job application.
        Uses a local import to avoid circular dependency issues.
        """
        if not obj.user:
            return None
        
        # Local import to avoid circular dependency
        from apps.candidate.models import Candidate
        
        first_application = Candidate.objects.filter(
            user=obj.user, 
            deleted_at__isnull=True
        ).order_by('applied_at').first()
        
        if first_application and first_application.applied_at:
            return first_application.applied_at.isoformat()
        return None

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user_serializer = UserRegistrationSerializer(data=user_data)
        user_serializer.is_valid(raise_exception=True)
        user = user_serializer.save()
        candidate = CandidateUser.objects.create(user=user, **validated_data)
        return candidate

    def to_representation(self, instance):
        """Override to flatten user data and include date fields"""
        data = super().to_representation(instance)
        if instance.user:
            data['user'] = {
                'id': instance.user.id,
                'email': instance.user.email,
                'first_name': instance.user.first_name,
                'last_name': instance.user.last_name,
            }
            data['date_joined'] = self.get_date_joined(instance)
            data['last_login'] = self.get_last_login(instance)
            data['applied_date'] = self.get_applied_date(instance)
        return data


class RecruiterUserSerializer(serializers.ModelSerializer):
    """
    Serializer for RecruiterUser profile.
    Includes nested User data with last_login and date_joined.
    """
    user = UserRegistrationSerializer()
    date_joined = serializers.SerializerMethodField()
    last_login = serializers.SerializerMethodField()

    class Meta:
        model = RecruiterUser
        fields = ['id', 'user', 'department', 'role', 'is_active', 'created_at', 'updated_at', 'date_joined', 'last_login']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_date_joined(self, obj):
        """Get date_joined from the related User model"""
        if obj.user and obj.user.date_joined:
            return obj.user.date_joined.isoformat()
        return None

    def get_last_login(self, obj):
        """Get last_login from the related User model"""
        if obj.user and obj.user.last_login:
            return obj.user.last_login.isoformat()
        return None

    def create(self, validated_data):
        if 'user' in validated_data:
            user_data = validated_data.pop('user')
            user_serializer = UserRegistrationSerializer(data=user_data)
            user_serializer.is_valid(raise_exception=True)
            user = user_serializer.save()
            recruiter = RecruiterUser.objects.create(user=user, **validated_data)
            return recruiter

    def to_representation(self, instance):
        """Override to flatten user data and include date fields"""
        data = super().to_representation(instance)
        if instance.user:
            data['user'] = {
                'id': instance.user.id,
                'email': instance.user.email,
                'first_name': instance.user.first_name,
                'last_name': instance.user.last_name,
            }
            data['date_joined'] = self.get_date_joined(instance)
            data['last_login'] = self.get_last_login(instance)
        return data


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