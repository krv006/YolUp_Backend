"""Accounts views — yupqa qatlam: HTTP <-> service/selector.

Biznes-logika services.py da, ko'rish huquqi selectors.py da, ruxsatlar
apps.core.permissions registry'sida.
"""
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext_lazy as _
from rest_framework import generics, serializers, status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.core.permissions import RequirePerm

from . import selectors, services, sessions
from .models import UserSession
from .serializers import (
    CertificateSerializer,
    ChildCreateSerializer,
    ConsentSerializer,
    LinkRequestSerializer,
    LinkRespondSerializer,
    LinkSerializer,
    MeSerializer,
    PasswordChangeSerializer,
    RegisterSerializer,
    UserSerializer,
)


class RegisterView(APIView):
    """Ochiq ro'yxatdan o'tish — muvaffaqiyatli bo'lsa darhol token ham
    qaytadi (auto-login): parol shu so'rovning o'zida tasdiqlangan, alohida
    `/login/` chaqirish shart emas — bir xil telefon raqami bilan ikkinchi
    rol-akkaunt ochayotganda ham qurilma darhol "eslab qoladi"."""

    permission_classes = [AllowAny]
    throttle_scope = 'auth'

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = services.register_user(request=request, **serializer.validated_data)
        refresh = sessions.issue_refresh(user, request)
        services.record_login(user=user, request=request)
        return Response({
            **RegisterSerializer(user).data,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }, status=status.HTTP_201_CREATED)


class LoginView(TokenObtainPairView):
    throttle_scope = 'auth'
    serializer_class = sessions.SessionTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code != 200:
            return response

        from .models import User

        # Muvaffaqiyatli login — IP/qurilma jurnaliga yoziladi (auth.login)
        user = User.objects.filter(username=request.data.get('username', '')).first()
        if user is not None:
            services.record_login(user=user, request=request)
        return response


class LoginHistoryView(APIView):
    """Login tarixi: o'ziniki; ota-ona `?student=<id>` bilan bolasiniki.

    Har yozuvda: vaqt, IP, qurilma (User-Agent) va o'zgarish bayroqlari
    (new_ip / new_device) — "boshqa joydan kirildi" darhol ko'rinadi.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(services.login_history(
            viewer=request.user, student_id=request.query_params.get('student'),
        ))


class RefreshView(TokenRefreshView):
    throttle_scope = 'auth'
    serializer_class = sessions.SessionTokenRefreshSerializer

    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except ObjectDoesNotExist:
            # Token egasi o'chirilgan: simplejwt buni 500 qiladi — frontend sessiyani tugatishi uchun 401 qaytaramiz
            raise InvalidToken(_('Foydalanuvchi topilmadi.'))


class LogoutView(APIView):
    """Chiqish — berilgan refresh token bekor qilinadi (blacklist), qayta
    ishlatib bo'lmaydi. Boshqa qurilmalardagi sessiyalarga ta'sir qilmaydi."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        services.logout(
            user=request.user,
            refresh_token=request.data.get('refresh'),
            device_id=request.data.get('device_id'),
            request=request,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(generics.RetrieveUpdateAPIView):
    """O'z profilim — javobda `linked_accounts` ham bor (xuddi shu telefon
    raqamidagi boshqa rol-akkauntlar, agar bo'lsa)."""

    permission_classes = [IsAuthenticated]
    serializer_class = MeSerializer

    def get_object(self):
        return self.request.user

    def delete(self, request, *args, **kwargs):
        """Akkauntni o'chirish = faolsizlantirish (ma'lumot saqlanadi, kirib bo'lmaydi). Ixtiyoriy `{"password": "..."}`
        berilsa — tekshiriladi."""
        services.deactivate_account(user=request.user, password=request.data.get('password'), request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class SessionListView(APIView):
    """Faol seanslar: `[{id, device, ip, city, last_active, is_current}]` (`city` — hozircha doim null)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        current = str((request.auth or {}).get('sid') or '')
        rows = UserSession.objects.filter(user=request.user, revoked_at__isnull=True)
        return Response([{
            'id': str(s.id), 'device': s.device, 'ip': s.ip, 'city': None,
            'last_active': s.last_active, 'is_current': str(s.id) == current,
        } for s in rows])


class SessionDetailView(APIView):
    """Bitta seansdan chiqarish (o'zingiznikidan ham bo'ladi — bu "chiqish" bilan teng)."""

    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        session = UserSession.objects.filter(pk=pk, user=request.user, revoked_at__isnull=True).first()
        if session is None:
            raise NotFound(_('Seans topilmadi.'))
        sessions.revoke(session)
        return Response(status=status.HTTP_204_NO_CONTENT)


class SessionLogoutOthersView(APIView):
    """Joriy qurilmadan tashqari hamma seanslardan chiqarish. Joriy seans token ichidagi `sid`dan aniqlanadi — eski
    (yangilanmagan) tokenda u yo'q, shunda avval qayta kirish/yangilash kerak (400)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        current = (request.auth or {}).get('sid')
        if not current:
            raise ValidationError({'detail': _('Joriy seans aniqlanmadi — qayta kiring.')})
        others = UserSession.objects.filter(user=request.user, revoked_at__isnull=True).exclude(pk=current)
        count = 0
        for session in others:
            sessions.revoke(session)
            count += 1
        return Response({'revoked': count})


class MeStatsView(APIView):
    """Profil ko'rsatkichlari: `{groups, students, experience_years}`."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(services.me_stats(request.user))


class PasswordChangeView(APIView):
    """Joriy parolni tekshirib yangisini qo'yadi. Javob: `{password_changed_at}`."""

    permission_classes = [IsAuthenticated]
    throttle_scope = 'auth'

    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        changed_at = services.change_password(
            user=request.user, request=request, **serializer.validated_data,
        )
        # /auth/me/ dagi bilan bir xil ko'rinishda (vaqt mintaqasi)
        return Response({'password_changed_at': serializers.DateTimeField().to_representation(changed_at)})


class SwitchAccountView(APIView):
    """Bir xil telefon raqamidagi boshqa rol-akkauntga parolsiz o'tish
    (`linked_accounts` — /auth/me/ javobida ko'rinadi). Joriy access token
    yetarli; yangi juft token (access+refresh) maqsad akkaunt uchun qaytadi."""

    permission_classes = [IsAuthenticated]
    throttle_scope = 'auth'

    def post(self, request, pk):
        target = services.switch_account(current_user=request.user, target_id=pk, request=request)
        refresh = sessions.issue_refresh(target, request)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': MeSerializer(target).data,
        })


class SwitchRoleView(APIView):
    """Boshqa rolga parolsiz o'tish — agar shu telefon raqamida o'sha rol
    hali mavjud bo'lmasa, ro'yxatdan o'tishsiz avtomatik yaratiladi.
    STUDENT hisoblar bu amalni bajara olmaydi (`services.switch_or_provision_role`)."""

    permission_classes = [IsAuthenticated]
    throttle_scope = 'auth'

    def post(self, request):
        role = (request.data.get('role') or '').strip()
        target = services.switch_or_provision_role(current_user=request.user, role=role, request=request)
        refresh = sessions.issue_refresh(target, request)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': MeSerializer(target).data,
        })


class ChildCreateView(APIView):
    permission_classes = [RequirePerm('child.create')]

    def post(self, request):
        serializer = ChildCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        child = services.create_child(creator=request.user, request=request, **serializer.validated_data)
        data = ChildCreateSerializer(child).data
        if getattr(child, 'enrolled_course_id', None):
            data['course_id'] = str(child.enrolled_course_id)
        return Response(data, status=status.HTTP_201_CREATED)


class LinkListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = LinkSerializer

    def get_queryset(self):
        return selectors.links_for_user(self.request.user)


class LinkRequestView(APIView):
    permission_classes = [RequirePerm('link.request')]

    def post(self, request):
        serializer = LinkRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        link, created = services.request_link(
            parent=request.user, username=data.get('username'),
            invite_code=data.get('invite_code'), request=request,
        )
        return Response(
            LinkSerializer(link).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class LinkRespondView(APIView):
    permission_classes = [RequirePerm('link.respond')]

    def post(self, request, pk):
        serializer = LinkRespondSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        link = services.respond_link(
            student=request.user, link_id=pk, action=serializer.validated_data['action'], request=request,
        )
        return Response(LinkSerializer(link).data)


class UserSearchView(APIView):
    """Admin: bildirishnoma yuborish uchun istalgan rol bo'yicha foydalanuvchi qidirish
    (lessons.CourseViewSet.search_students bilan bir xil naqsh, lekin barcha rollar)."""

    permission_classes = [RequirePerm('user.manage')]

    def get(self, request):
        from django.db.models import Q

        from .models import User

        q = (request.query_params.get('q') or '').strip()
        if len(q) < 2:
            return Response([])
        users = User.objects.filter(
            Q(username__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q)
        ).exclude(pk=request.user.pk).order_by('username')[:10]
        return Response(UserSerializer(users, many=True).data)


class TeacherStatsListView(generics.ListAPIView):
    """Admin: barcha o'qituvchilar ro'yxati, har birining umumiy reytingi bilan."""

    permission_classes = [RequirePerm('user.manage')]
    serializer_class = UserSerializer

    def get_queryset(self):
        return selectors.teacher_list()


class PendingTeachersListView(generics.ListAPIView):
    """Admin: tasdiq kutayotgan (hali faollashtirilmagan) o'qituvchilar."""

    permission_classes = [RequirePerm('user.manage')]
    serializer_class = UserSerializer

    def get_queryset(self):
        return selectors.pending_teachers()


class TeacherVideoStatsView(APIView):
    """Admin: Storage — har bir o'qituvchida nechta tayyor dars-yozuvi
    (video) borligi + platformadagi jami video soni."""

    permission_classes = [RequirePerm('user.manage')]

    def get(self, request):
        from apps.lessons import selectors as lesson_selectors
        return Response(lesson_selectors.video_stats_by_teacher())


class ApproveTeacherView(APIView):
    """Admin: o'qituvchini tasdiqlash — shundan keyin kira oladi."""

    permission_classes = [RequirePerm('user.manage')]

    def post(self, request, pk):
        teacher = services.approve_teacher(admin=request.user, teacher_id=pk, request=request)
        return Response(UserSerializer(teacher).data)


class TeacherStatsDetailView(APIView):
    """Admin: bitta o'qituvchi uchun to'liq statistika — reyting, kurslar/
    darslar/o'quvchilar soni, ishonchlilik va baholar taqsimoti (admin panel)."""

    permission_classes = [RequirePerm('user.manage')]

    def get(self, request, pk):
        teacher = services.get_teacher(teacher_id=pk)
        return Response(selectors.teacher_detail_stats(teacher))


class TeacherRatingsListView(generics.ListAPIView):
    """Admin: bitta o'qituvchining barcha darslariga qo'yilgan baholari
    (o'quvchi fikr-mulohazasi bilan) — o'quvchi tomonidan berilgan reytingni
    ko'rish uchun."""

    permission_classes = [RequirePerm('user.manage')]

    def get_serializer_class(self):
        from apps.lessons.serializers import LessonRatingSerializer
        return LessonRatingSerializer

    def get_queryset(self):
        from apps.lessons import selectors as lesson_selectors

        teacher = services.get_teacher(teacher_id=self.kwargs['pk'])
        return lesson_selectors.ratings_for_teacher(teacher)


class MyRatingsListView(generics.ListAPIView):
    """O'qituvchi o'ziga qo'yilgan baholarni (o'quvchi yozgan fikr bilan) ko'radi."""

    permission_classes = [RequirePerm('rating.view_own')]

    def get_serializer_class(self):
        from apps.lessons.serializers import LessonRatingSerializer
        return LessonRatingSerializer

    def get_queryset(self):
        from apps.lessons import selectors as lesson_selectors

        return lesson_selectors.ratings_for_teacher(self.request.user)


class CertificateListCreateView(generics.ListCreateAPIView):
    """O'qituvchi profiliga sertifikat yuklaydi — faqat o'ziniki."""

    permission_classes = [RequirePerm('certificate.manage')]
    serializer_class = CertificateSerializer

    def get_queryset(self):
        return self.request.user.certificates.all()

    def create(self, request, *args, **kwargs):
        serializer = CertificateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        certificate = services.upload_certificate(
            teacher=request.user, file=serializer.validated_data['file'],
            title=serializer.validated_data.get('title', ''),
        )
        return Response(
            CertificateSerializer(certificate, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


class CertificateDeleteView(APIView):
    permission_classes = [RequirePerm('certificate.manage')]

    def delete(self, request, pk):
        services.delete_certificate(teacher=request.user, certificate_id=pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ConsentListCreateView(generics.ListCreateAPIView):
    permission_classes = [RequirePerm('consent.manage')]
    serializer_class = ConsentSerializer

    def get_queryset(self):
        return selectors.consents_for_parent(self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        consent = services.set_consent(
            parent=request.user,
            student=serializer.validated_data['student'],
            kind=serializer.validated_data['kind'],
            granted=serializer.validated_data['granted'],
            request=request,
        )
        return Response(ConsentSerializer(consent).data, status=status.HTTP_201_CREATED)
