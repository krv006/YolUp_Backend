import secrets
import string
import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db.models import (
    CASCADE,
    BooleanField,
    CharField,
    DateField,
    DateTimeField,
    FileField,
    ForeignKey,
    GenericIPAddressField,
    ImageField,
    Index,
    PositiveIntegerField,
    PositiveSmallIntegerField,
    SET_NULL,
    TextChoices,
    TextField,
    UniqueConstraint,
    UUIDField,
)

from django.utils import timezone

from apps.core.models import TimeStampedUUIDModel
from apps.core.uploads import certificate_path


def generate_invite_code() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return 'FK-' + ''.join(secrets.choice(alphabet) for _ in range(4))


class User(AbstractUser):
    class Role(TextChoices):
        SUPER_ADMIN = 'super_admin', 'Super Admin'
        ADMIN = 'admin', 'Admin'
        TEACHER = 'teacher', "O'qituvchi"
        STUDENT = 'student', "O'quvchi"
        PARENT = 'parent', 'Ota-ona'

    id = UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = CharField(max_length=16, choices=Role.choices, default=Role.STUDENT, db_index=True)
    # O'qituvchi ro'yxatdan o'tganda False — admin tasdiqlaguncha kursi/darsi ochilmaydi
    # (RequirePerm shu bayroqni tekshiradi, apps.core.permissions.user_has_perm).
    is_approved = BooleanField(default=True)
    # Ataylab UNIQUE EMAS — bitta real inson bir xil raqam bilan bir nechta
    # rol-akkaunt ochishi mumkin (o'qituvchi + ota-ona + o'quvchi), har biri
    # o'z login/parolisi bilan. Shu raqamni ishlatgan boshqa akkauntlar
    # `apps.accounts.selectors.linked_accounts()` orqali topiladi (profil —
    # o'ziniki — va admin panelida ko'rinadi).
    phone = CharField(max_length=20, null=True, blank=True, db_index=True)
    # Student's invite code — parent enters it to request a link (consent flow).
    invite_code = CharField(max_length=12, unique=True, null=True, blank=True)
    avatar = ImageField(upload_to='avatars/', null=True, blank=True)
    # Frontend `PATCH /auth/me/` orqali yozadi — qurilma/brauzerdan mustaqil,
    # foydalanuvchi qayerdan kirsa ham tanlagan tili saqlanib qoladi. Har bir
    # so'rovdagi `Accept-Language` esa mustaqil ishlayveradi (LocaleMiddleware);
    # bu maydon faqat "eslab qolingan tanlov" — ikkalasi bir-biriga bog'liq emas.
    preferred_language = CharField(max_length=8, choices=settings.LANGUAGES, default='uz', blank=True)
    # Dars boshlanishidan necha daqiqa oldin eslatma kelishi kerak — foydalanuvchi
    # PATCH /auth/me/ orqali o'zgartiradi (apps.lessons.services.send_lesson_reminders).
    # Standart 15 — o'quvchi/ota-ona uchun; o'qituvchiga ro'yxatdan o'tishda
    # `services.register_user` alohida TEACHER_LESSON_REMINDER_MINUTES (10)
    # qo'yadi, chunki o'qituvchi darsni BOSHLASHI kerak, undan oldinroq
    # ogohlantirilishi tabiiy.
    lesson_reminder_minutes = PositiveIntegerField(default=15)
    # Profil (faqat o'zi ko'radi va tahrirlaydi): otasining ismi, tug'ilgan sana, shahar, o'zi haqida, tajriba (yil),
    # o'qituvchining asosiy fani (Course.Subject kodlaridan biri). `email` — AbstractUser'dan; tasdiqlash xati yo'q.
    middle_name = CharField(max_length=100, blank=True, default='')
    birth_date = DateField(null=True, blank=True)
    city = CharField(max_length=100, blank=True, default='')
    bio = TextField(blank=True, default='')
    experience_years = PositiveSmallIntegerField(null=True, blank=True)
    subject = CharField(max_length=100, blank=True, default='')
    # O'qituvchi o'quvchi hisobini yaratganda kiritadigan ota-ona telefoni (hisob bog'lanishiga ta'sir qilmaydi)
    parent_phone = CharField(max_length=20, blank=True, default='')
    # Parol oxirgi marta o'zgartirilgan payt (`POST /auth/password/change/`)
    password_changed_at = DateTimeField(null=True, blank=True)
    # Oxirgi faollik (autentifikatsiyalangan so'rov yoki chat ulanishi yopilishi) — chat a'zolari ro'yxatida "5 daqiqa oldin"
    last_seen_at = DateTimeField(null=True, blank=True)
    # Ikki bosqichli tasdiqlash (SMS kod) — yoqilgan bo'lsa loginda paroldan keyin kod so'raladi
    two_factor_enabled = BooleanField(default=False)
    # Email/telefon tasdiqlangan (kod orqali). Manzil/raqam o'zgarsa yana `false` bo'ladi.
    email_verified = BooleanField(default=False)
    phone_verified = BooleanField(default=False)
    phone_verified_at = DateTimeField(null=True, blank=True)
    # Tizim sozlamalari: "Yangi xabarlar" va "Email xabarnomalar" tugmalari
    notify_messages = BooleanField(default=True)
    notify_email = BooleanField(default=False)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.role == self.Role.STUDENT and not self.invite_code:
            code = generate_invite_code()
            while User.objects.filter(invite_code=code).exists():
                code = generate_invite_code()
            self.invite_code = code
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.username} ({self.get_role_display()})'


class ParentChildLink(TimeStampedUUIDModel):
    """Parent ↔ student connection. Analytics open to the parent only while APPROVED.

    Two ways a link is created:
      - parent creates the child account themselves -> APPROVED immediately
      - parent enters the student's invite code -> PENDING until the student approves
    The student can revoke (decline) an approved link at any time.
    """

    class Status(TextChoices):
        PENDING = 'pending', 'Kutilmoqda'
        APPROVED = 'approved', 'Tasdiqlangan'
        DECLINED = 'declined', 'Rad etilgan'

    parent = ForeignKey('accounts.User', CASCADE, related_name='child_links')
    student = ForeignKey('accounts.User', CASCADE, related_name='parent_links')
    status = CharField(max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True)
    responded_at = DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            UniqueConstraint(fields=['parent', 'student'], name='unique_parent_student'),
        ]

    def __str__(self):
        return f'{self.parent.username} -> {self.student.username} [{self.status}]'


class Consent(TimeStampedUUIDModel):
    """Per-child consent flags managed by the linked parent (FRD: privacy.consent_collect)."""

    class Kind(TextChoices):
        RECORDING = 'recording', 'Dars yozib olish'
        CAMERA = 'camera', 'Kamera'
        ANALYTICS = 'analytics', 'Tahlil (davomat/faollik)'

    student = ForeignKey('accounts.User', CASCADE, related_name='consents')
    granted_by = ForeignKey('accounts.User', CASCADE, related_name='granted_consents')
    kind = CharField(max_length=16, choices=Kind.choices)
    granted = BooleanField(default=False)

    class Meta:
        constraints = [
            UniqueConstraint(fields=['student', 'kind'], name='unique_student_consent_kind'),
        ]

    def __str__(self):
        return f'{self.student.username} · {self.kind} = {self.granted}'


class TeacherCertificate(TimeStampedUUIDModel):
    """O'qituvchi profiliga yuklaydigan malaka sertifikati (rasm yoki PDF)."""

    teacher = ForeignKey('accounts.User', CASCADE, related_name='certificates')
    file = FileField(upload_to=certificate_path)
    title = CharField(max_length=200, blank=True)
    issuer = CharField(max_length=200, blank=True, default='')
    issued_year = PositiveSmallIntegerField(null=True, blank=True)

    class Status(TextChoices):
        PENDING = 'pending', 'Tekshirilmoqda'
        VERIFIED = 'verified', 'Tasdiqlangan'
        REJECTED = 'rejected', 'Rad etilgan'

    status = CharField(max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True)
    reject_reason = TextField(blank=True, default='')
    verified_at = DateTimeField(null=True, blank=True)
    reviewed_by = ForeignKey('accounts.User', SET_NULL, null=True, blank=True, related_name='reviewed_certificates')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.teacher.username} · {self.title or self.file.name}'


class SocialIdentity(TimeStampedUUIDModel):
    """Google/Apple akkaunt bilan bog'lanish: provayderning o'zgarmas `sub` identifikatori bo'yicha."""

    class Provider(TextChoices):
        GOOGLE = 'google', 'Google'
        APPLE = 'apple', 'Apple'

    user = ForeignKey(settings.AUTH_USER_MODEL, CASCADE, related_name='social_identities')
    provider = CharField(max_length=10, choices=Provider.choices)
    subject = CharField(max_length=255)
    email = CharField(max_length=254, blank=True, default='')

    class Meta:
        constraints = [UniqueConstraint(fields=['provider', 'subject'], name='unique_social_identity')]

    def __str__(self):
        return f'{self.provider}:{self.user_id}'


class UserSession(TimeStampedUUIDModel):
    """Faol seans (qurilma) — `auth/sessions/` ro'yxati. Token ichidagi `sid` shu qatorning id'si
    (qarang `apps.accounts.sessions`). `last_active` token yangilanganda (taxminan soatiga bir) yangilanadi."""

    user = ForeignKey(settings.AUTH_USER_MODEL, CASCADE, related_name='sessions')
    device = CharField(max_length=120, blank=True, default='')
    user_agent = CharField(max_length=300, blank=True, default='')
    ip = GenericIPAddressField(null=True, blank=True)
    # IP bo'yicha shahar (GEOIP_CITY_DB sozlangan bo'lsa), aks holda bo'sh
    city = CharField(max_length=100, blank=True, default='')
    last_active = DateTimeField(default=timezone.now)
    revoked_at = DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-last_active']
        indexes = [Index(fields=['user', 'revoked_at'])]

    def __str__(self):
        return f'{self.user_id} · {self.device}'
