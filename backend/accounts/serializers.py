from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import UserFavorite

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name", "display_name", "phone",
            "role", "preferred_language", "avatar", "is_active", "date_joined",
        ]
        read_only_fields = ["id", "role", "is_active", "date_joined"]


class AdminUserSerializer(UserSerializer):
    """Used by Super Admins: may change role and active flag and set a password."""

    password = serializers.CharField(write_only=True, required=False, min_length=8)

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ["password"]
        read_only_fields = ["id", "date_joined"]

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        user = User(**validated_data)
        if password:
            validate_password(password, user)
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for key, value in validated_data.items():
            setattr(instance, key, value)
        if password:
            validate_password(password, instance)
            instance.set_password(password)
        instance.save()
        return instance


class RegisterSerializer(serializers.ModelSerializer):
    """Public self-registration. New accounts are always Viewers."""

    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["id", "username", "email", "password", "display_name", "preferred_language"]

    def validate(self, attrs):
        validate_password(attrs["password"], User(username=attrs.get("username"), email=attrs.get("email")))
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data, role=User.Role.VIEWER)
        user.set_password(password)
        user.save()
        return user


class TokenWithUserSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        token["username"] = user.username
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user, context=self.context).data
        return data


class FavoriteSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source="team.name", read_only=True, default=None)
    tournament_name = serializers.CharField(source="tournament.name", read_only=True, default=None)
    match_title = serializers.CharField(source="match.__str__", read_only=True, default=None)

    class Meta:
        model = UserFavorite
        fields = ["id", "team", "match", "tournament", "team_name", "tournament_name", "match_title", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate(self, attrs):
        targets = [attrs.get("team"), attrs.get("match"), attrs.get("tournament")]
        if sum(t is not None for t in targets) != 1:
            raise serializers.ValidationError("Choose exactly one of team, match or tournament.")
        user = self.context["request"].user
        qs = UserFavorite.objects.filter(user=user)
        for key in ("team", "match", "tournament"):
            if attrs.get(key) is not None and qs.filter(**{key: attrs[key]}).exists():
                raise serializers.ValidationError("Already in your favourites.")
        return attrs
