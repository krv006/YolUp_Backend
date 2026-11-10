"""Hammani cheklash (17), bir martalik ruxsat (18) va ochiq mikrofon/kamera rejimi (19) — 2026-11-10."""
from types import SimpleNamespace
from unittest import mock

import jwt
from django.utils import timezone
from livekit.protocol.models import TrackSource, TrackType
from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import Consent, ParentChildLink, User
from apps.lessons.models import Course, Enrollment, Lesson


def make(username, role):
    user = User(username=username, role=role, is_approved=True)
    user.set_password('x')
    user.save()
    return user


class FakeRoom:
    """LiveKit xona API'si: ishtirokchilar, ovozi o'chirilgan treklar va ruxsat yangilanishlari yoziladi."""

    def __init__(self, participants):
        self.participants = participants
        self.muted, self.updates = [], []

    async def list_participants(self, _request):
        return SimpleNamespace(participants=self.participants)

    async def mute_published_track(self, request):
        self.muted.append((request.identity, request.track_sid))
        for p in self.participants:
            for track in p.tracks:
                if track.sid == request.track_sid:
                    track.muted = True  # haqiqiy LiveKit'dagidek: ikkinchi marta o'chirilmaydi

    async def update_participant(self, request):
        perm = request.permission
        self.updates.append((request.identity, set(perm.can_publish_sources), perm.can_publish))
        for p in self.participants:
            if p.identity == request.identity:
                p.permission = SimpleNamespace(can_publish_sources=list(perm.can_publish_sources), can_publish=perm.can_publish)


def fake_livekit(room):
    class Client:
        def __init__(self, *args, **kwargs):
            self.room = room

        async def aclose(self):
            return None

    return Client


def participant(identity, sources=(), audio_muted=False):
    """Treklar faqat ruxsat berilgan manbalar uchun bor (ruxsatsiz o'quvchi hech narsa nashr qila olmaydi)."""
    names = {getattr(s, 'name', s) if not isinstance(s, str) else s for s in sources}
    names |= {'microphone' if s == TrackSource.MICROPHONE else 'camera' if s == TrackSource.CAMERA else str(s) for s in sources}
    tracks = []
    if 'microphone' in names:
        tracks.append(SimpleNamespace(type=TrackType.AUDIO, source=TrackSource.MICROPHONE, muted=audio_muted, sid=f'A-{identity}'))
    if 'camera' in names:
        tracks.append(SimpleNamespace(type=TrackType.VIDEO, source=TrackSource.CAMERA, muted=False, sid=f'V-{identity}'))
        tracks.append(SimpleNamespace(type=TrackType.VIDEO, source=TrackSource.SCREEN_SHARE, muted=False, sid=f'S-{identity}'))
    return SimpleNamespace(
        identity=identity, tracks=tracks,
        permission=SimpleNamespace(can_publish_sources=list(sources), can_publish=bool(sources)),
    )


class MediaBase(APITestCase):
    def setUp(self):
        self.teacher = make('mc_t', User.Role.TEACHER)
        self.s1, self.s2, self.s3 = (make(f'mc_s{i}', User.Role.STUDENT) for i in (1, 2, 3))
        self.parent = make('mc_p', User.Role.PARENT)
        self.course = Course.objects.create(teacher=self.teacher, title='Speaking')
        for s in (self.s1, self.s2, self.s3):
            Enrollment.objects.create(course=self.course, student=s, status=Enrollment.Status.APPROVED)
        ParentChildLink.objects.create(parent=self.parent, student=self.s3, status=ParentChildLink.Status.APPROVED)
        self.lesson = Lesson.objects.create(
            course=self.course, starts_at=timezone.now(), duration_min=60, status=Lesson.Status.LIVE, live_started_at=timezone.now(),
        )
        self.client = APIClient()
        self.events = []
        patcher = mock.patch('apps.board.realtime._send', side_effect=lambda lesson_id, event: self.events.append(event))
        patcher.start()
        self.addCleanup(patcher.stop)

    def api(self, user):
        self.client.force_authenticate(user)
        return self.client

    def uid(self, user):
        return f'user-{user.id}'

    def room(self):
        return FakeRoom([
            participant(self.uid(self.teacher), ['microphone', 'camera', 'screen_share']),
            participant(self.uid(self.s1), [TrackSource.MICROPHONE, TrackSource.CAMERA]),
            participant(self.uid(self.s2), [TrackSource.MICROPHONE]),
            participant(self.uid(self.s3), []),
        ])

    def claims(self, user):
        resp = self.api(user).post('/api/v1/live/token/', {'lesson_id': str(self.lesson.id)}, format='json')
        self.assertEqual(resp.status_code, 200, resp.content)
        return resp.json(), jwt.decode(resp.json()['token'], options={'verify_signature': False})['video']


class RestrictAllTests(MediaBase):
    def test_mute_all_mutes_and_takes_the_microphone_permission_away(self):
        room = self.room()
        with mock.patch('apps.live.services.LiveKitAPI', fake_livekit(room)):
            resp = self.api(self.teacher).post(
                '/api/v1/live/mute-all/', {'lesson_id': str(self.lesson.id), 'except': [str(self.s2.id)]}, format='json',
            )
        self.assertEqual((resp.status_code, resp.json()), (200, {'muted': 1}))
        self.assertEqual(room.muted, [(self.uid(self.s1), f'A-{self.uid(self.s1)}')])
        # s1: mikrofon olinadi, kamera qoladi; s2 (istisno) va o'qituvchiga tegilmaydi; s3 da ruxsat yo'q edi
        self.assertEqual(room.updates, [(self.uid(self.s1), {TrackSource.CAMERA}, True)])
        self.assertEqual([e for e in self.events if e['type'] == 'mic_revoked'], [{'type': 'mic_revoked', 'student_id': str(self.s1.id)}])

    def test_camera_off_all_turns_cameras_off_but_not_screen_share_and_revokes_only_the_camera(self):
        room = self.room()
        with mock.patch('apps.live.services.LiveKitAPI', fake_livekit(room)):
            resp = self.api(self.teacher).post('/api/v1/live/camera-off-all/', {'lesson_id': str(self.lesson.id)}, format='json')
            alias = self.api(self.teacher).post(
                '/api/v1/live/mute-all/', {'lesson_id': str(self.lesson.id), 'kind': 'video'}, format='json')
        self.assertEqual(resp.json(), {'camera_off': 1})
        self.assertEqual(room.muted, [(self.uid(self.s1), f'V-{self.uid(self.s1)}')])  # ekran trekiga tegilmadi
        self.assertEqual(room.updates, [(self.uid(self.s1), {TrackSource.MICROPHONE}, True)])
        self.assertEqual(alias.json(), {'camera_off': 0})  # ikkinchi marta: hech kimda kamera qolmagan
        self.assertTrue(any(e == {'type': 'camera_revoked', 'student_id': str(self.s1.id)} for e in self.events))

    def test_last_source_removed_closes_publishing_instead_of_opening_everything(self):
        room = self.room()
        with mock.patch('apps.live.services.LiveKitAPI', fake_livekit(room)):
            self.api(self.teacher).post('/api/v1/live/mute-all/', {'lesson_id': str(self.lesson.id)}, format='json')
        by_identity = {identity: (sources, can_publish) for identity, sources, can_publish in room.updates}
        self.assertEqual(by_identity[self.uid(self.s2)], (set(), False))  # bo'sh ro'yxat "hammasi ochiq" bo'lib qolmasin

    def test_permissions_and_bad_kind(self):
        body = {'lesson_id': str(self.lesson.id)}
        self.assertEqual(self.api(self.s1).post('/api/v1/live/camera-off-all/', body, format='json').status_code, 403)
        self.assertEqual(self.api(self.teacher).post('/api/v1/live/mute-all/', {**body, 'kind': 'zzz'}, format='json').status_code, 400)


class ReleaseMediaTests(MediaBase):
    def release(self, user, kind, room=None):
        with mock.patch('apps.live.services.LiveKitAPI', fake_livekit(room or self.room())):
            return self.api(user).post('/api/v1/live/release-media/', {'lesson_id': str(self.lesson.id), 'kind': kind}, format='json')

    def test_student_turning_the_mic_off_loses_the_permission(self):
        room = self.room()
        resp = self.release(self.s1, 'microphone', room)
        self.assertEqual((resp.status_code, resp.json()), (200, {'revoked': True, 'open': False}))
        self.assertEqual(room.updates, [(self.uid(self.s1), {TrackSource.CAMERA}, True)])
        self.assertEqual(room.muted, [])  # o'quvchi o'zi o'chirgan, qayta mute qilinmaydi
        self.assertIn({'type': 'mic_revoked', 'student_id': str(self.s1.id)}, self.events)
        # kamera ruxsati saqlanadi; "camera" kaliti ham ishlaydi
        again = self.release(self.s1, 'camera', room)
        self.assertEqual(again.json()['revoked'], True)
        self.assertEqual(room.updates[-1], (self.uid(self.s1), set(), False))

    def test_releasing_something_never_granted_does_nothing(self):
        room = self.room()
        self.assertEqual(self.release(self.s3, 'microphone', room).json(), {'revoked': False, 'open': False})
        self.assertEqual(room.updates, [])

    def test_open_mode_keeps_the_permission_and_outsiders_are_refused(self):
        Lesson.objects.filter(pk=self.lesson.pk).update(open_mic=True)
        room = self.room()
        self.assertEqual(self.release(self.s1, 'microphone', room).json(), {'revoked': False, 'open': True})
        self.assertEqual(room.updates, [])
        outsider = make('mc_out', User.Role.STUDENT)
        self.assertEqual(self.release(outsider, 'microphone').status_code, 403)
        self.assertEqual(self.release(self.s1, 'nope').status_code, 400)

    def test_livekit_failure_is_swallowed_for_the_student(self):
        with mock.patch('apps.live.services.LiveKitAPI', mock.Mock(side_effect=RuntimeError('down'))):
            resp = self.api(self.s1).post('/api/v1/live/release-media/', {'lesson_id': str(self.lesson.id), 'kind': 'microphone'}, format='json')
        self.assertEqual((resp.status_code, resp.json()), (200, {'revoked': False, 'open': False}))


class OpenModeTests(MediaBase):
    def patch(self, body, room=None):
        with mock.patch('apps.live.services.LiveKitAPI', fake_livekit(room or self.room())):
            return self.api(self.teacher).patch(f'/api/v1/live/lesson/{self.lesson.id}/media-mode/', body, format='json')

    def test_toggles_are_independent_and_reported_to_everyone(self):
        resp = self.patch({'open_mic': True})
        self.assertEqual((resp.status_code, resp.json()), (200, {'open_mic': True, 'open_camera': False}))
        self.assertIn({'type': 'media_mode', 'open_mic': True, 'open_camera': False}, self.events)
        self.lesson.refresh_from_db()
        self.assertEqual((self.lesson.open_mic, self.lesson.open_camera), (True, False))
        self.assertEqual(self.patch({'open_camera': True}).json(), {'open_mic': True, 'open_camera': True})
        got = self.api(self.s1).get(f'/api/v1/live/lesson/{self.lesson.id}/media-mode/')
        self.assertEqual(got.json(), {'open_mic': True, 'open_camera': True})
        self.assertEqual(self.api(self.s1).get(f'/api/v1/live/lesson/{self.lesson.id}/presence/').json()['open_mic'], True)

    def test_turning_on_adds_the_permission_to_everyone_in_the_room(self):
        room = self.room()
        self.patch({'open_mic': True}, room)
        got = {identity: sources for identity, sources, _can in room.updates}
        self.assertNotIn(self.uid(self.teacher), got)
        self.assertEqual(got[self.uid(self.s3)], {TrackSource.MICROPHONE})
        self.assertEqual(got[self.uid(self.s1)], {TrackSource.MICROPHONE, TrackSource.CAMERA})  # mavjud ruxsat saqlanadi

    def test_camera_mode_respects_parent_consent(self):
        Consent.objects.create(student=self.s3, granted_by=self.parent, kind=Consent.Kind.CAMERA, granted=False)
        room = self.room()
        self.patch({'open_camera': True}, room)
        self.assertNotIn(self.uid(self.s3), {identity for identity, _s, _c in room.updates})
        _body, video = self.claims(self.s3)  # keyin kirganda ham kamera olmaydi
        self.assertNotIn('camera', video.get('canPublishSources', []))

    def test_late_joiners_get_the_open_sources_in_their_token(self):
        body, video = self.claims(self.s1)
        self.assertEqual((video.get('canPublish', False), video.get('canPublishSources', [])), (False, []))
        self.assertEqual((body['open_mic'], body['open_camera']), (False, False))
        Lesson.objects.filter(pk=self.lesson.pk).update(open_mic=True, open_camera=True)
        body, video = self.claims(self.s1)
        self.assertEqual(sorted(video['canPublishSources']), ['camera', 'microphone'])
        self.assertTrue(video['canPublish'])
        self.assertEqual((body['open_mic'], body['open_camera']), (True, True))
        teacher_body, teacher_video = self.claims(self.teacher)
        self.assertIn('screen_share', teacher_video['canPublishSources'])

    def test_turning_off_mutes_and_takes_the_permission_back(self):
        Lesson.objects.filter(pk=self.lesson.pk).update(open_mic=True)
        room = self.room()
        resp = self.patch({'open_mic': False}, room)
        self.assertEqual(resp.json(), {'open_mic': False, 'open_camera': False})
        self.assertEqual({identity for identity, _m in room.muted}, {self.uid(self.s1), self.uid(self.s2)})
        self.assertIn({'type': 'mic_revoked', 'student_id': str(self.s2.id)}, self.events)

    def test_only_the_lessons_teacher_and_valid_values(self):
        other = make('mc_t2', User.Role.TEACHER)
        url = f'/api/v1/live/lesson/{self.lesson.id}/media-mode/'
        self.assertEqual(self.api(self.s1).patch(url, {'open_mic': True}, format='json').status_code, 403)
        self.assertEqual(self.api(other).patch(url, {'open_mic': True}, format='json').status_code, 403)
        self.assertEqual(self.patch({'open_mic': 'yes'}).status_code, 400)
        self.assertEqual(self.patch({}).json(), {'open_mic': False, 'open_camera': False})  # o'zgarish yo'q
