from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from . import selectors
from .models import Consent, ParentChildLink, TeacherCertificate, User


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


class ChildCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ['id', 'username', 'password', 'first_name', 'last_name', 'invite_code']
        read_only_fields = ['invite_code']


class LinkSerializer(serializers.ModelSerializer):
    parent = UserSerializer(read_only=True)
    student = UserSerializer(read_only=True)

    class Meta:
        model = ParentChildLink
        fields = ['id', 'parent', 'student', 'status', 'created_at', 'responded_at']


class LinkRequestSerializer(serializers.Serializer):
    invite_code = serializers.CharField(max_length=12)


class LinkRespondSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['approve', 'decline'])


class ConsentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Consent
        fields = ['id', 'student', 'kind', 'granted', 'updated_at']
        read_only_fields = ['updated_at']
