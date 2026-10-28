import re
from datetime import date

from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from . import selectors
from .models import Consent, ParentChildLink, TeacherCertificate, User


PHONE_RE = re.compile(r'^\+?[0-9][0-9 ()-]{5,18}$')


def clean_phone(value: str) -> str:
    value = (value or '').strip()
    if value and not PHONE_RE.match(value):
        raise serializers.ValidationError(_("Telefon raqami noto'g'ri (masalan +998901234567)."))
    return value


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
        # Bir so'rov ichida bir xil o'qituvchi ko'p qatorda uchraydi (kurslar/bildirishnomalar/chat ro'yxati) — bir marta o'qiymiz
        cache = self.context.setdefault('_teacher_certificates', {})
        if obj.pk not in cache:
            request = self.context.get('request')
            cache[obj.pk] = CertificateSerializer(
                obj.certificates.all(), many=True, context={'request': request},
            ).data
        return cache[obj.pk]

    def _rating_stats(self, obj):
        if not hasattr(obj, '_rating_stats_cache'):
            if obj.role != User.Role.TEACHER:
                obj._rating_stats_cache = {'avg_rating': None, 'rating_count': None}
            else:
                cache = self.context.setdefault('_teacher_ratings', {})
                if obj.pk not in cache:
                    cache[obj.pk] = selectors.teacher_rating_stats(obj)
                obj._rating_stats_cache = cache[obj.pk]
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
    # Profil maydonlari faqat o'zining profilida (boshqalarga — chat, kurs ro'yxati — chiqmaydi: email/bio oshkor bo'lmasin)
    email = serializers.EmailField(required=False, allow_blank=True, max_length=254)
    bio = serializers.CharField(required=False, allow_blank=True, max_length=1000)
    experience_years = serializers.IntegerField(required=False, allow_null=True, min_value=0, max_value=80)

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + [
            'linked_accounts', 'email', 'middle_name', 'birth_date', 'city', 'bio', 'experience_years', 'subject',
            'parent_phone', 'password_changed_at', 'two_factor_enabled', 'notify_messages', 'notify_email',
            'email_verified', 'phone_verified', 'phone_verified_at',
        ]
        read_only_fields = UserSerializer.Meta.read_only_fields + [
            'parent_phone', 'password_changed_at', 'two_factor_enabled', 'email_verified', 'phone_verified',
            'phone_verified_at',
        ]

    def validate_email(self, value):
        return (value or '').strip().lower()

    def update(self, instance, validated_data):
        """Email yoki telefon o'zgarsa yangi manzil/raqam tasdiqlanmagan hisoblanadi."""
        from apps.core.sms import normalize_phone

        if 'email' in validated_data and validated_data['email'] != instance.email:
            instance.email_verified = False
        if 'phone' in validated_data and normalize_phone(validated_data['phone'] or '') != normalize_phone(instance.phone or ''):
            instance.phone_verified = False
            instance.phone_verified_at = None
        return super().update(instance, validated_data)

    def validate_birth_date(self, value):
        if value is not None and not (date(1900, 1, 1) <= value <= date.today()):
            raise serializers.ValidationError(_("Tug'ilgan sana noto'g'ri."))
        return value

    def validate_subject(self, value):
        from apps.lessons.models import Course

        value = (value or '').strip()
        if value and value not in Course.Subject.values:
            raise serializers.ValidationError(_("Noma'lum fan."))
        return value

    def validate_city(self, value):
        return (value or '').strip()

    def validate_middle_name(self, value):
        return (value or '').strip()

    def get_linked_accounts(self, obj):
        return LinkedAccountSerializer(selectors.linked_accounts(obj), many=True).data


class RegisterSerializer(serializers.ModelSerializer):
    """Ochiq ro'yxatdan o'tish — o'qituvchi, ota-ona yoki o'quvchi.

    O'quvchi o'zi ro'yxatdan o'tsa ham, ota-ona hali bog'lanmagan (rozilik
    oqimi keyinroq — `invite_code` orqali)."""

    password = serializers.CharField(write_only=True, validators=[validate_password])
    role = serializers.ChoiceField(choices=[User.Role.TEACHER, User.Role.PARENT, User.Role.STUDENT])
    # SMS bilan tasdiqlangan raqam uchun bir martalik token (`/auth/register/phone/verify/`); berilmasa telefon tasdiqlanmagan qoladi
    phone_token = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'password', 'first_name', 'last_name', 'role', 'phone', 'phone_token', 'is_approved']
        read_only_fields = ['is_approved']
        extra_kwargs = {'username': {'validators': username_validators()}}


class ChildCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    parent_phone = serializers.CharField(required=False, allow_blank=True, max_length=20)
    # Faqat o'qituvchi yaratganda: shu (o'z) kursiga darhol qo'shiladi
    course_id = serializers.UUIDField(required=False, write_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'password', 'first_name', 'last_name', 'parent_phone', 'course_id', 'invite_code']
        read_only_fields = ['invite_code']
        extra_kwargs = {'username': {'validators': username_validators()}}

    def validate_parent_phone(self, value):
        return clean_phone(value)


class PasswordResetRequestSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=32)


class PasswordResetVerifySerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=32)
    code = serializers.CharField(max_length=10)


class PasswordResetConfirmSerializer(serializers.Serializer):
    reset_token = serializers.CharField(max_length=200)
    password = serializers.CharField(write_only=True)


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)


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
