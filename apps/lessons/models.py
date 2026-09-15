import uuid

from django.conf import settings
from django.db.models import (
    CASCADE,
    BooleanField,
    CharField,
    DateTimeField,
    ForeignKey,
    OneToOneField,
    PositiveIntegerField,
    TextChoices,
    TextField,
    UniqueConstraint,
)
from django.utils.translation import gettext_lazy as _

from apps.core.models import SoftDeleteModel, TimeStampedUUIDModel


class Course(TimeStampedUUIDModel, SoftDeleteModel):
    class Subject(TextChoices):
        # Labellar `gettext_lazy` — `Accept-Language` sarlavhasiga qarab
        # uz/ru/en tarjima qilinadi (`locale/{ru,en}/LC_MESSAGES/django.po`).
        MATH = 'math', _('Matematika')
        PHYSICS = 'physics', _('Fizika')
        ASTRONOMY = 'astronomy', _('Astronomiya')
        CHEMISTRY = 'chemistry', _('Kimyo')
        BIOLOGY = 'biology', _('Biologiya')
        ECOLOGY = 'ecology', _('Ekologiya')
        COMPUTER_SCIENCE = 'computer_science', _('Informatika')
        HISTORY = 'history', _('Tarix')
        GEOGRAPHY = 'geography', _('Geografiya')
        CIVICS = 'civics', _('Huquq asoslari')
        ECONOMICS = 'economics', _('Iqtisodiyot asoslari')
        LITERATURE = 'literature', _('Ona tili va adabiyot')
        MUSIC = 'music', _('Musiqa')
        ART = 'art', _("Tasviriy san'at")
        PHYSICAL_EDUCATION = 'physical_education', _('Jismoniy tarbiya')
        TECHNOLOGY = 'technology', _('Texnologiya')
        CHESS = 'chess', _('Shaxmat')
        ENGLISH = 'english', _('Ingliz tili')
        RUSSIAN = 'russian', _('Rus tili')
        TURKISH = 'turkish', _('Turk tili')
        GERMAN = 'german', _('Nemis tili')
        FRENCH = 'french', _('Fransuz tili')
        ARABIC = 'arabic', _('Arab tili')
        CHINESE = 'chinese', _('Xitoy tili')
        KOREAN = 'korean', _('Koreys tili')
        JAPANESE = 'japanese', _('Yapon tili')
        OTHER = 'other', _('Boshqa')

    teacher = ForeignKey(settings.AUTH_USER_MODEL, CASCADE, related_name='courses')
    title = CharField(max_length=200)
    # Erkin matn EMAS — o'qituvchi tayin ro'yxatdan tanlaydi (2026-09-15: ilgari
    # erkin matn edi, regex bilan aniqlanardi — imlo farqi (Ximiya/kimyo/KIMYO)
    # bo'lsa fan aniqlanmay qolish xavfi bor edi).
    subject = CharField(max_length=100, choices=Subject.choices, default=Subject.OTHER, blank=True)
    description = TextField(blank=True)
    is_active = BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} — {self.teacher.username}'


class Enrollment(TimeStampedUUIDModel):
    class Status(TextChoices):
        PENDING = 'pending', 'Kutilmoqda'
        APPROVED = 'approved', 'Tasdiqlangan'
        DECLINED = 'declined', 'Rad etilgan'

    course = ForeignKey('lessons.Course', CASCADE, related_name='enrollments')
    student = ForeignKey(settings.AUTH_USER_MODEL, CASCADE, related_name='enrollments')
    # O'quvchi/ota-ona so'rovi PENDING bo'lib turadi — kurs o'qituvchisi tasdiqlaganda APPROVED.
    # O'qituvchi o'zi biriktirsa darhol APPROVED (default mavjud yozuvlar uchun ham).
    status = CharField(max_length=10, choices=Status.choices, default=Status.APPROVED, db_index=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=['course', 'student'], name='unique_course_student'),
        ]

    def __str__(self):
        return f'{self.student.username} @ {self.course.title} [{self.status}]'


class Lesson(TimeStampedUUIDModel, SoftDeleteModel):
    class Status(TextChoices):
        SCHEDULED = 'scheduled', 'Rejalashtirilgan'
        LIVE = 'live', 'Jonli'
        FINISHED = 'finished', 'Tugagan'
        CANCELLED = 'cancelled', 'Bekor qilingan'

    course = ForeignKey('lessons.Course', CASCADE, related_name='lessons')
    # Bo'sh bo'lishi mumkin — takrorlanuvchi jadval yaratishda o'qituvchidan
    # mavzu so'ralmaydi (bitta mavzu barcha darslarga bir xil yozilib
    # ketmasligi uchun); frontend mavzusiz darsni "Mavzu yozilmagan" deb
    # belgilaydi, o'qituvchi keyin har birini alohida tahrirlab yozadi.
    title = CharField(max_length=200, blank=True)
    starts_at = DateTimeField(db_index=True)
    duration_min = PositiveIntegerField(default=45)
    status = CharField(max_length=12, choices=Status.choices, default=Status.SCHEDULED, db_index=True)
    # O'qituvchi HAQIQATDA kirgan payt (apps.live.services.issue_room_token,
    # status LIVE'ga o'tganda) — rejalashtirilgan `starts_at`dan farqli
    # (o'qituvchi kech kirishi mumkin). auto_finish_expired_lessons muddatni
    # shundan hisoblaydi, aks holda kech boshlangan dars darhol "tugagan"
    # deb topilib, hali davom etayotgan safar o'rtada uzilib qolardi.
    live_started_at = DateTimeField(null=True, blank=True)
    # LiveKit room name — unique per lesson, generated once.
    room_name = CharField(max_length=64, unique=True, editable=False)

    class Meta:
        ordering = ['starts_at']

    def save(self, *args, **kwargs):
        if not self.room_name:
            self.room_name = f'lesson-{uuid.uuid4().hex[:12]}'
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.title or self.course.title} ({self.starts_at:%Y-%m-%d %H:%M})'


class AttentionCheck(TimeStampedUUIDModel):
    """"Siz shu yerdamisiz?" — dars davomida server belgilagan tasodifiy vaqtlarda.

    Jadval server tomonda yaratiladi (EduTech.docx: o'quvchi vaqtini oldindan
    bila olmasligi kerak). 15 soniya ichida javob bo'lmasa o'tkazib yuborilgan
    hisoblanadi.
    """

    lesson = ForeignKey('lessons.Lesson', CASCADE, related_name='attention_checks')
    student = ForeignKey(settings.AUTH_USER_MODEL, CASCADE, related_name='attention_checks')
    due_at = DateTimeField(db_index=True)
    answered_at = DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['due_at']

    def __str__(self):
        state = 'javob berildi' if self.answered_at else 'kutilmoqda'
        return f'{self.student.username} @ {self.due_at:%H:%M:%S} [{state}]'


class FocusEvent(TimeStampedUUIDModel):
    """Anti-cheat jurnali: o'quvchi dars oynasidan chiqib-kirishlari.

    Brauzer screenshot/screenrecord'ni taqiqlay olmaydi — lekin har bir
    chiqib-kirish shu yerga yoziladi va hisobotda ko'rinadi.
    """

    class Kind(TextChoices):
        EXIT = 'exit', 'Oynadan chiqdi'
        RETURN = 'return', 'Qaytib keldi'

    lesson = ForeignKey('lessons.Lesson', CASCADE, related_name='focus_events')
    student = ForeignKey(settings.AUTH_USER_MODEL, CASCADE, related_name='focus_events')
    kind = CharField(max_length=8, choices=Kind.choices)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.student.username} · {self.kind} · {self.created_at:%H:%M:%S}'


class FocusAlert(TimeStampedUUIDModel):
    """O'quvchi darsdan FOCUS_PARENT_ALERT_THRESHOLD martadan ko'p chiqqanda bir
    marta yaratiladi — ota-ona paneliga ko'rinadigan signal (EPAM imtihon uslubi:
    1-2 marta ogohlantirish, uchinchisida ota-onaga xabar boradi).
    """

    lesson = ForeignKey('lessons.Lesson', CASCADE, related_name='focus_alerts')
    student = ForeignKey(settings.AUTH_USER_MODEL, CASCADE, related_name='focus_alerts')
    exit_count = PositiveIntegerField()

    class Meta:
        ordering = ['-created_at']
        constraints = [
            UniqueConstraint(fields=['lesson', 'student'], name='unique_lesson_student_focus_alert'),
        ]

    def __str__(self):
        return f'{self.student.username} @ {(self.lesson.title or self.lesson.course.title)} · {self.exit_count} marta chiqdi'


class LessonRecording(TimeStampedUUIDModel):
    """Dars video yozuvi (EduTech.docx: "video zapis avtomatik saqlansin").

    Ikki qismdan yig'iladi:
      - VIDEO: LiveKit Track Egress o'qituvchi kamerasini xom (qayta
        kodlashsiz) nusxa ko'chiradi -> `video_file_name`.
      - AUDIO: o'qituvchi brauzeri barcha ishtirokchilar ovozini ichkarida
        aralashtirib (Web Audio API), bo'lak-bo'lak (chunk) serverga
        yuklaydi -> `audio_file_name` (server tomonda qo'shib boriladi).
    Ikkalasi ham tayyor bo'lgach (`video_ready_at` va `audio_finalized_at`
    ikkalasi bor), fon jarayonida `ffmpeg`da vaqt farqiga moslab (`-itsoffset`,
    `video_started_at`/`audio_started_at` orqali hisoblanadi) bitta faylga
    birlashtiriladi -> yakuniy `file_name`. Fayl `recordings` volume'ida
    turadi va FAQAT auth endpoint orqali beriladi. O'qituvchi guruhni
    (kursni) o'chirmaguncha saqlanadi.
    """

    class Status(TextChoices):
        PENDING = 'pending', 'Boshlanmoqda'       # so'rov yuborildi, egress hali tasdiqlamadi
        RECORDING = 'recording', 'Yozilmoqda'     # egress tasdiqladi (egress_id bor)
        MERGING = 'merging', 'Birlashtirilmoqda'  # video+audio tayyor, ffmpeg ishlamoqda
        COMPLETED = 'completed', 'Tayyor'
        FAILED = 'failed', 'Xatolik'

    lesson = OneToOneField('lessons.Lesson', CASCADE, related_name='recording')
    # O'qituvchi dars tugatishda beradigan nom — chatga shu nom bilan tushadi
    title = CharField(max_length=200, blank=True)
    egress_id = CharField(max_length=64, blank=True)
    # Yakuniy (video+audio birlashtirilgan) fayl — faqat merge tugagach to'ladi
    file_name = CharField(max_length=255, blank=True)
    status = CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    error = TextField(blank=True)
    ended_at = DateTimeField(null=True, blank=True)

    # ── Video (Track Egress) ──
    video_file_name = CharField(max_length=255, blank=True)
    video_started_at = DateTimeField(null=True, blank=True)
    video_ready_at = DateTimeField(null=True, blank=True)  # egress to'xtatildi

    # ── Audio (brauzer -> chunked upload) ──
    audio_file_name = CharField(max_length=255, blank=True)
    audio_started_at = DateTimeField(null=True, blank=True)  # brauzer yuborgan, birinchi chunk'da
    audio_finalized_at = DateTimeField(null=True, blank=True)  # o'qituvchi "tugadi" deb belgiladi

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{(self.lesson.title or self.lesson.course.title)} [{self.status}]'


class Attendance(TimeStampedUUIDModel):
    """Auto attendance: stamped when a participant requests a room token / leaves."""

    lesson = ForeignKey('lessons.Lesson', CASCADE, related_name='attendances')
    student = ForeignKey(settings.AUTH_USER_MODEL, CASCADE, related_name='attendances')
    joined_at = DateTimeField(null=True, blank=True)
    left_at = DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-joined_at']
        constraints = [
            UniqueConstraint(fields=['lesson', 'student'], name='unique_lesson_student'),
        ]

    @property
    def minutes(self):
        if self.joined_at and self.left_at:
            return int((self.left_at - self.joined_at).total_seconds() // 60)
        return None

    def __str__(self):
        return f'{self.student.username} @ {(self.lesson.title or self.lesson.course.title)}'


class LessonBan(TimeStampedUUIDModel):
    """O'qituvchi darsdan chetlashtirgan o'quvchi — qayta room token ololmaydi
    (apps.live.services.issue_room_token shu jadvalni tekshiradi)."""

    lesson = ForeignKey('lessons.Lesson', CASCADE, related_name='bans')
    student = ForeignKey(settings.AUTH_USER_MODEL, CASCADE, related_name='lesson_bans')
    banned_by = ForeignKey(settings.AUTH_USER_MODEL, CASCADE, related_name='+')

    class Meta:
        constraints = [
            UniqueConstraint(fields=['lesson', 'student'], name='unique_lesson_student_ban'),
        ]

    def __str__(self):
        return f'{self.student.username} @ {(self.lesson.title or self.lesson.course.title)} [banned]'


class MicRequest(TimeStampedUUIDModel):
    """O'quvchi mikrofon so'ragan ("qo'l ko'tarish"), hali javob berilmagan.

    WebSocket broadcast'dan tashqari bazada ham saqlanadi — shu sababli
    o'qituvchi so'rovdan KEYIN kirsa yoki sahifani yangilasa ham, joriy
    kutayotgan so'rovlar yo'qolib qolmaydi (apps.live.services.pending_mic_requests
    orqali qayta tiklanadi, apps.board.services.get_board() javobiga qo'shiladi).
    Ruxsat berilganda yoki rad etilganda o'chiriladi (apps.live.services.grant_mic /
    deny_mic). Bitta o'quvchi — bitta darsda bir vaqtda faqat BITTA faol so'rov
    (`unique_lesson_student_mic_request` + get_or_create — qayta so'rasa dublikat
    yaratilmaydi; so'rov hal bo'lgach — o'chirilgach — yangi so'rov yuborishi mumkin).
    """

    lesson = ForeignKey('lessons.Lesson', CASCADE, related_name='mic_requests')
    student = ForeignKey(settings.AUTH_USER_MODEL, CASCADE, related_name='mic_requests')

    class Meta:
        ordering = ['created_at']  # FIFO — birinchi so'ragan birinchi ko'rinadi
        constraints = [
            UniqueConstraint(fields=['lesson', 'student'], name='unique_lesson_student_mic_request'),
        ]

    def __str__(self):
        return f'{self.student.username} @ {(self.lesson.title or self.lesson.course.title)} [mic requested]'


class CameraRequest(TimeStampedUUIDModel):
    """O'quvchi kamera so'ragan, hali javob berilmagan — `MicRequest` bilan
    bir xil naqsh (2026-09-04: kamera ham endi ruxsat bilan ochiladi, avval
    hammaga erkin edi)."""

    lesson = ForeignKey('lessons.Lesson', CASCADE, related_name='camera_requests')
    student = ForeignKey(settings.AUTH_USER_MODEL, CASCADE, related_name='camera_requests')

    class Meta:
        ordering = ['created_at']
        constraints = [
            UniqueConstraint(fields=['lesson', 'student'], name='unique_lesson_student_camera_request'),
        ]

    def __str__(self):
        return f'{self.student.username} @ {(self.lesson.title or self.lesson.course.title)} [camera requested]'


class LessonReminder(TimeStampedUUIDModel):
    """'Dars N daqiqadan keyin boshlanadi' bildirishnomasi — har (dars,
    foydalanuvchi) juftligiga FAQAT BIR MARTA yuboriladi (o'qituvchi ham,
    o'quvchi ham shu jadvalda, ikkalasi ham `User.lesson_reminder_minutes`ga
    ko'ra o'z vaqtida ogohlantiriladi — apps.lessons.services.send_lesson_reminders)."""

    lesson = ForeignKey('lessons.Lesson', CASCADE, related_name='reminders')
    user = ForeignKey(settings.AUTH_USER_MODEL, CASCADE, related_name='lesson_reminders')

    class Meta:
        constraints = [
            UniqueConstraint(fields=['lesson', 'user'], name='unique_lesson_reminder_user'),
        ]

    def __str__(self):
        return f'{self.user.username} @ {(self.lesson.title or self.lesson.course.title)}'


class LessonRating(TimeStampedUUIDModel):
    """O'quvchi tugagan darsga baho beradi — o'qituvchi/kurs sifatini kuzatish uchun."""

    lesson = ForeignKey('lessons.Lesson', CASCADE, related_name='ratings')
    student = ForeignKey(settings.AUTH_USER_MODEL, CASCADE, related_name='lesson_ratings')
    stars = PositiveIntegerField()
    description = TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            UniqueConstraint(fields=['lesson', 'student'], name='unique_lesson_student_rating'),
        ]

    def __str__(self):
        return f'{self.student.username} @ {(self.lesson.title or self.lesson.course.title)} · {self.stars}★'
