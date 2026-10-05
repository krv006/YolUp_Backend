from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from . import selectors
from .models import Consent, ParentChildLink, TeacherCertificate, User


def username_validators():
    """Band login uchun aniq, `username` kaliti ostidagi xabar (mobil ilova
    maydon xatosini shu kalit bo'yicha ko'rsatadi). Model maydonining
    standart xabari inglizcha ("A user with that username already exists.")."""
    return [
        UnicodeUsernameValidator(),
        UniqueValidator(queryset=User.objects.all(), message=_('Bu login band.')),
    ]


class CertificateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeacherCertificate
        fields = ['id', 'file', 'title', 'created_at']
        read_only_fields = ['id', 'created_at']


class UserSerializer(serializers.ModelSerializer):
    """O'qituvchi uchun `avg_rating`/`rating_count` — barcha darslari bo'yicha
    umumiy reyting (boshqa rollarda `null`, apps.lessons.LessonRating asosida
    hisoblanadi — selectors.teacher_rating_stats). `certificates` ham xuddi
    shunday — faqat o'qituvchida, boshqa rollarda bo'sh ro'yxat."""

    avg_rating = serializers.SerializerMethodField()
    rating_count = serializers.SerializerMethodField()
    certificates = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'first_name', 'last_name', 'role', 'phone', 'invite_code', 'avatar',
            'avg_rating', 'rating_count', 'certificates', 'is_approved', 'preferred_language',
            'lesson_reminder_minutes',
        ]
        read_only_fields = ['role', 'invite_code', 'is_approved']
        extra_kwargs = {'username': {'validators': username_validators()}}

    def get_certificates(self, obj):
        if obj.role != User.Role.TEACHER:
            return []
        request = self.context.get('request')
        return CertificateSerializer(
            obj.certificates.all(), many=True, context={'request': request},
        ).data

    def _rating_stats(self, obj):
        if not hasattr(obj, '_rating_stats_cache'):
            obj._rating_stats_cache = (
                selectors.teacher_rating_stats(obj) if obj.role == User.Role.TEACHER
                else {'avg_rating': None, 'rating_count': None}
            )
        return obj._rating_stats_cache

    def get_avg_rating(self, obj):
        return self._rating_stats(obj)['avg_rating']

    def get_rating_count(self, obj):
        return self._rating_stats(obj)['rating_count']


class LinkedAccountSerializer(serializers.ModelSerializer):
    """Xuddi shu telefon raqamidagi BOSHQA akkaunt — qisqa ko'rinish (to'liq
    UserSerializer emas — reyting/sertifikat kabi og'ir maydonlar shart emas)."""

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'role']


class MeSerializer(UserSerializer):
    """`/auth/me/` uchun — UserSerializer + `linked_accounts` (faqat o'zining
    profilida ko'rinadi, boshqa joyda UserSerializer ishlatilganda yo'q —
    boshqa foydalanuvchining telefon-egalari ro'yxati oshkor bo'lmasligi uchun)."""

    linked_accounts = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ['linked_accounts']

    def get_linked_accounts(self, obj):
        return LinkedAccountSerializer(selectors.linked_accounts(obj), many=True).data


class RegisterSerializer(serializers.ModelSerializer):
    """Ochiq ro'yxatdan o'tish — o'qituvchi, ota-ona yoki o'quvchi.

    O'quvchi o'zi ro'yxatdan o'tsa ham, ota-ona hali bog'lanmagan (rozilik
    oqimi keyinroq — `invite_code` orqali)."""

    password = serializers.CharField(write_only=True, validators=[validate_password])
    role = serializers.ChoiceField(choices=[User.Role.TEACHER, User.Role.PARENT, User.Role.STUDENT])

    class Meta:
        model = User
        fields = ['id', 'username', 'password', 'first_name', 'last_name', 'role', 'phone', 'is_approved']
        read_only_fields = ['is_approved']
        extra_kwargs = {'username': {'validators': username_validators()}}


class ChildCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ['id', 'username', 'password', 'first_name', 'last_name', 'invite_code']
        read_only_fields = ['invite_code']
        extra_kwargs = {'username': {'validators': username_validators()}}


class LinkSerializer(serializers.ModelSerializer):
    parent = UserSerializer(read_only=True)
    student = UserSerializer(read_only=True)

    class Meta:
        model = ParentChildLink
        fields = ['id', 'parent', 'student', 'status', 'created_at', 'responded_at']


class LinkRequestSerializer(serializers.Serializer):
    """Ikkalasidan biri yetarli: `username` (o'quvchi logini) yoki `invite_code`
    (eski veb ilova hali ishlatadi — o'tish davri uchun saqlangan)."""

    username = serializers.CharField(max_length=150, required=False, allow_blank=True)
    invite_code = serializers.CharField(max_length=12, required=False, allow_blank=True)

    def validate(self, attrs):
        if not (attrs.get('username') or '').strip() and not (attrs.get('invite_code') or '').strip():
            raise serializers.ValidationError(
                {'username': _("O'quvchi logini yoki taklif kodini kiriting.")},
            )
        return attrs


class LinkRespondSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['approve', 'decline'])


class ConsentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Consent
        fields = ['id', 'student', 'kind', 'granted', 'updated_at']
        read_only_fields = ['updated_at']
