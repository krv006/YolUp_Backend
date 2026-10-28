"""Global qidiruv: guruhlar, darslar, testlar, xabarlar va odamlar — hammasi rol bo'yicha cheklangan (faqat ko'rish huquqi bor narsalar)."""
from django.db.models import Q
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts import selectors as account_selectors
from apps.accounts.models import User
from apps.chat import selectors as chat_selectors
from apps.chat.models import Message
from apps.lessons import selectors as lesson_selectors
from apps.quizzes import selectors as quiz_selectors

TYPES = ('groups', 'lessons', 'quizzes', 'messages', 'people')
PER_TYPE_IN_ALL = 5
MIN_QUERY = 2


def _groups(user, q):
    qs = lesson_selectors.courses_for(user).filter(Q(title__icontains=q) | Q(subject__icontains=q)).distinct()
    return [{'type': 'groups', 'id': str(c.id), 'title': c.title, 'subtitle': c.get_subject_display()} for c in qs]


def _lessons(user, q):
    qs = lesson_selectors.lessons_for(user).filter(Q(title__icontains=q) | Q(course__title__icontains=q)).order_by('-starts_at')
    return [{
        'type': 'lessons', 'id': str(lesson.id), 'title': lesson.title or lesson.course.title,
        'subtitle': lesson.course.title, 'starts_at': lesson.starts_at, 'status': lesson.status,
    } for lesson in qs]


def _quizzes(user, q):
    qs = quiz_selectors.quizzes_for(user).filter(Q(title__icontains=q) | Q(topic__icontains=q)).order_by('-created_at')
    return [{
        'type': 'quizzes', 'id': str(quiz.id), 'title': quiz.title or quiz.topic,
        'subtitle': quiz.course.title if quiz.course_id else '',
    } for quiz in qs]


def _messages(user, q):
    room_ids = list(chat_selectors.rooms_for(user).values_list('id', flat=True))
    qs = (
        Message.objects.filter(room_id__in=room_ids, deleted_at__isnull=True, kind=Message.Kind.USER, text__icontains=q)
        .exclude(hides__user=user).select_related('room', 'room__course', 'sender').order_by('-created_at')
    )
    rows = []
    for message in qs:
        text = ' '.join(message.text.split())
        at = text.lower().find(q.lower())
        start = max(0, at - 30)
        rows.append({
            'type': 'messages', 'id': str(message.id), 'room_id': str(message.room_id), 'message_id': str(message.id),
            'title': text[start:start + 120], 'subtitle': (message.room.course.title if message.room.course_id else '') or message.room.title_for(user),
            'sender': message.sender.get_full_name() or message.sender.username, 'created_at': message.created_at,
        })
    return rows


def _people(user, q):
    if user.role == User.Role.TEACHER:
        found = account_selectors.teacher_people_search(user, q)
        return [{'type': 'people', 'id': p['id'], 'title': p['name'], 'subtitle': f"@{p['username']}", 'role': p['role'],
                 'avatar': p['avatar'], 'room_id': p['room_id']} for p in found]
    # O'quvchi/ota-ona: o'z guruhlari o'qituvchilari
    courses = lesson_selectors.courses_for(user).select_related('teacher')
    seen, rows = set(), []
    for course in courses:
        teacher = course.teacher
        text = f'{teacher.get_full_name()} {teacher.username}'.lower()
        if teacher.id not in seen and q.lower() in text:
            seen.add(teacher.id)
            rows.append({'type': 'people', 'id': str(teacher.id), 'title': teacher.get_full_name() or teacher.username,
                         'subtitle': f'@{teacher.username}', 'role': teacher.role,
                         'avatar': teacher.avatar.url if teacher.avatar else None, 'room_id': None})
    return rows


FINDERS = {'groups': _groups, 'lessons': _lessons, 'quizzes': _quizzes, 'messages': _messages, 'people': _people}


class SearchView(APIView):
    """`GET /search/?q=&type=all|groups|lessons|quizzes|messages|people&page=&page_size=`.

    `type=all` (standart) — har turdan 5 tadan (`counts` — har turdagi jami). Bitta tur — sahifalangan ro'yxat. Ikki harfdan
    qisqa so'rov — bo'sh natija."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        q = (request.query_params.get('q') or '').strip()
        kind = request.query_params.get('type') or 'all'
        if kind != 'all' and kind not in TYPES:
            raise ValidationError({'type': f"Mumkin: all, {', '.join(TYPES)}"})
        if len(q) < MIN_QUERY:
            return Response({'count': 0, 'next': None, 'previous': None, 'results': [], 'counts': {}})
        if kind == 'all':
            results, counts = [], {}
            for name in TYPES:
                rows = FINDERS[name](request.user, q)
                counts[name] = len(rows)
                results.extend(rows[:PER_TYPE_IN_ALL])
            return Response({'count': len(results), 'next': None, 'previous': None, 'results': results, 'counts': counts})
        try:
            size = max(1, min(int(request.query_params.get('page_size', 20)), 50))
            page = max(1, int(request.query_params.get('page', 1)))
        except ValueError:
            raise ValidationError({'page': "Son bo'lishi kerak."}) from None
        rows = FINDERS[kind](request.user, q)
        start = (page - 1) * size
        base = request.build_absolute_uri(request.path)
        extra = f'&q={q}&type={kind}&page_size={size}'
        return Response({
            'count': len(rows),
            'next': f'{base}?page={page + 1}{extra}' if start + size < len(rows) else None,
            'previous': f'{base}?page={page - 1}{extra}' if page > 1 else None,
            'results': rows[start:start + size], 'counts': {kind: len(rows)},
        })
