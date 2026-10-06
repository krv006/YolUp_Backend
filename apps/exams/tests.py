"""Imtihon (mock test): ball dvigatellari, shablonlar, sinxron taymer, javob
saqlash, natijalar va ruxsatlar."""
from datetime import timedelta

from django.test import SimpleTestCase
from django.utils import timezone

from apps.accounts.tests import login, register
from apps.notifications.models import Notification
from apps.quizzes.models import Option
from apps.quizzes.tests_question_types import QuizTestBase

from . import scoring
from .models import Exam, ExamSection


def _section(key, earned, maximum, **extra):
    return {'key': key, 'title': key.title(), 'group': extra.pop('group', ''), 'weight': 1,
            'manual': extra.pop('manual', False), 'earned': earned, 'max': maximum,
            'manual_score': extra.pop('manual_score', None)}


class ScoringEngineTests(SimpleTestCase):
    def test_round_half_band_follows_ielts_rule(self):
        self.assertEqual(scoring.round_half_band(6.25), 6.5)
        self.assertEqual(scoring.round_half_band(6.75), 7.0)
        self.assertEqual(scoring.round_half_band(6.125), 6.0)
        self.assertEqual(scoring.round_half_band(6.375), 6.5)
        self.assertEqual(scoring.round_half_band(7.0), 7.0)

    def test_ielts_listening_and_reading_tables(self):
        self.assertEqual(scoring.ielts_band(scoring._IELTS_LISTENING, 1.0), 9.0)
        self.assertEqual(scoring.ielts_band(scoring._IELTS_LISTENING, 30 / 40), 7.0)
        self.assertEqual(scoring.ielts_band(scoring._IELTS_LISTENING, 23 / 40), 6.0)
        self.assertEqual(scoring.ielts_band(scoring._IELTS_READING, 33 / 40), 7.5)
        self.assertEqual(scoring.ielts_band(scoring._IELTS_READING, 0), 0.0)

    def test_ielts_overall_waits_for_manual_bands(self):
        sections = [
            _section('listening', 40, 40), _section('reading', 30, 40),
            _section('writing', 0, 4, manual=True), _section('speaking', None, None, manual=True),
        ]
        partial = scoring.compute({'type': 'ielts'}, sections)
        self.assertIsNone(partial['total'])
        self.assertEqual(partial['pending'], ['writing', 'speaking'])
        by_key = {s['key']: s for s in partial['sections']}
        self.assertEqual(by_key['listening']['score'], 9.0)
        self.assertEqual(by_key['reading']['score'], 7.0)

    def test_ielts_overall_band_when_complete(self):
        sections = [
            _section('listening', 40, 40), _section('reading', 40, 40),
            _section('writing', 0, 4, manual=True, manual_score=7.0),
            _section('speaking', None, None, manual=True, manual_score=6.5),
        ]
        result = scoring.compute({'type': 'ielts'}, sections)
        self.assertEqual(result['total']['score'], 8.0)  # (9+9+7+6.5)/4 = 7.875 -> 8.0
        self.assertFalse(result['approximate'])

    def test_sat_scaled_scores_are_approximate(self):
        perfect = [
            _section('rw_1', 27, 27, group='rw'), _section('rw_2', 27, 27, group='rw'),
            _section('math_1', 22, 22, group='math'), _section('math_2', 22, 22, group='math'),
        ]
        result = scoring.compute({'type': 'sat'}, perfect)
        self.assertEqual(result['total']['score'], 1600)
        self.assertTrue(result['approximate'])
        half = [
            _section('rw_1', 13.5, 27, group='rw'), _section('rw_2', 13.5, 27, group='rw'),
            _section('math_1', 0, 22, group='math'), _section('math_2', 0, 22, group='math'),
        ]
        groups = {g['key']: g['score'] for g in scoring.compute({'type': 'sat'}, half)['groups']}
        self.assertEqual(groups, {'rw': 500, 'math': 200})

    def test_milliy_levels(self):
        full = scoring.compute({'type': 'milliy'}, [_section('main', 50, 50)])
        self.assertEqual(full['total']['score'], 75.0)
        self.assertEqual(full['total']['level'], 'A+')
        half = scoring.compute({'type': 'milliy'}, [_section('main', 25, 50)])
        self.assertEqual(half['total']['score'], 37.5)
        self.assertIsNone(half['total']['level'])
        b = scoring.compute({'type': 'milliy'}, [_section('main', 38.5, 50)])  # 57.75 -> B
        self.assertEqual(b['total']['level'], 'B')
        self.assertTrue(b['approximate'])

    def test_percent_engine_weights_and_pass_mark(self):
        sections = [
            {**_section('a', 5, 10), 'weight': 3},
            {**_section('b', 10, 10), 'weight': 1},
        ]
        result = scoring.compute({'type': 'percent', 'scale': 100, 'pass_percent': 60}, sections)
        self.assertEqual(result['total']['score'], 62.5)  # (0.5*3 + 1*1) / 4
        self.assertTrue(result['total']['passed'])

    def test_percent_engine_manual_section_is_pending_until_scored(self):
        sections = [_section('a', 5, 10), _section('w', 0, 0, manual=True)]
        self.assertIsNone(scoring.compute({'type': 'percent'}, sections)['total'])
        sections[1]['manual_score'] = 100
        self.assertEqual(scoring.compute({'type': 'percent'}, sections)['total']['score'], 75.0)

    def test_manual_validation(self):
        self.assertEqual(scoring.validate_manual({'type': 'ielts'}, 'writing', '6.5'), 6.5)
        for bad in (9.5, -1, 6.3, 'x'):
            with self.assertRaises(scoring.ManualScoreError):
                scoring.validate_manual({'type': 'ielts'}, 'writing', bad)
        with self.assertRaises(scoring.ManualScoreError):
            scoring.validate_manual({'type': 'percent'}, 'a', 101)


class ExamTestBase(QuizTestBase):
    def setUp(self):
        super().setUp()
        register(self.client, 's2', 'student')
        self.outsider_token = login(self.client, 's2')
        register(self.client, 't2', 'teacher')
        self.teacher2_token = login(self.client, 't2')

    # --- yordamchilar -------------------------------------------------------
    def quiz(self, count=2, points=2):
        questions = [
            {'type': 'single', 'text': f'Q{i}', 'points': points, 'options': [
                {'text': 'to\'g\'ri', 'is_correct': True}, {'text': 'xato', 'is_correct': False}]}
            for i in range(count)
        ]
        resp = self.make_quiz(questions)
        self.assertEqual(resp.status_code, 201, resp.content)
        return resp.json()['id']

    def custom_template(self, items=None, scoring_cfg=None):
        self.auth(self.teacher_token)
        items = items or [
            {'type': 'section', 'key': 'a', 'title': 'A', 'minutes': 10},
            {'type': 'break', 'key': 'rest', 'title': 'Tanaffus', 'minutes': 5},
            {'type': 'section', 'key': 'b', 'title': 'B', 'minutes': 10},
        ]
        resp = self.client.post('/api/v1/exams/templates/', {
            'name': 'Mening imtihonim', 'items': items, 'scoring': scoring_cfg or {'scale': 100},
        }, format='json')
        self.assertEqual(resp.status_code, 201, resp.content)
        return resp.json()['id']

    def create_exam(self, template, sections, starts_in=120, title='Mock', token=None, course=None):
        self.auth(token or self.teacher_token)
        starts = (timezone.now() + timedelta(minutes=starts_in)).isoformat()
        return self.client.post('/api/v1/exams/', {
            'course': course or self.course_id, 'template': template, 'title': title,
            'starts_at': starts, 'sections': sections,
        }, format='json')

    def make_exam(self, **kwargs):
        template = self.custom_template()
        qa, qb = self.quiz(), self.quiz()
        resp = self.create_exam(template, [{'key': 'a', 'quiz': qa}, {'key': 'b', 'quiz': qb}], **kwargs)
        self.assertEqual(resp.status_code, 201, resp.content)
        self.qa, self.qb = qa, qb
        return resp.json()

    def shift(self, exam_id, minutes_ago, seconds=0):
        """Imtihon `minutes_ago` daqiqa oldin boshlangandek ko'rsatadi."""
        exam = Exam.objects.get(pk=exam_id)
        total = sum(s.minutes for s in exam.sections.exclude(kind=ExamSection.Kind.OFFLINE))
        exam.starts_at = timezone.now() - timedelta(minutes=minutes_ago, seconds=seconds)
        exam.ends_at = exam.starts_at + timedelta(minutes=total)
        exam.save(update_fields=['starts_at', 'ends_at'])

    def current(self, exam_id, token=None):
        self.auth(token or self.child_token)
        return self.client.get(f'/api/v1/exams/{exam_id}/current/')

    def answers_for(self, quiz_id, correct=True):
        self.auth(self.teacher_token)
        detail = self.client.get(f'/api/v1/quizzes/{quiz_id}/').json()
        result = []
        for question in detail['questions']:
            option = Option.objects.get(question_id=question['id'], is_correct=correct)
            result.append({'question': question['id'], 'selected_option': str(option.id)})
        return result

    def save(self, exam_id, answers, token=None):
        self.auth(token or self.child_token)
        return self.client.put(f'/api/v1/exams/{exam_id}/answers/', {'answers': answers}, format='json')

    def results(self, exam_id, token):
        self.auth(token)
        return self.client.get(f'/api/v1/exams/{exam_id}/results/')


class TemplateTests(ExamTestBase):
    def test_system_templates_are_listed(self):
        self.auth(self.teacher_token)
        body = self.client.get('/api/v1/exams/templates/').json()
        self.assertEqual([t['id'] for t in body][:3], ['ielts', 'sat', 'milliy'])
        sat = body[1]
        self.assertEqual([i['type'] for i in sat['items']], ['section', 'section', 'break', 'section', 'section'])
        self.assertEqual(sat['items'][2]['minutes'], 10)

    def test_custom_template_crud_and_isolation(self):
        template_id = self.custom_template()
        self.auth(self.teacher_token)
        ids = [t['id'] for t in self.client.get('/api/v1/exams/templates/').json()]
        self.assertIn(template_id, ids)
        self.auth(self.teacher2_token)
        ids2 = [t['id'] for t in self.client.get('/api/v1/exams/templates/').json()]
        self.assertNotIn(template_id, ids2)
        self.assertEqual(self.client.delete(f'/api/v1/exams/templates/{template_id}/').status_code, 404)
        self.auth(self.teacher_token)
        self.assertEqual(self.client.delete(f'/api/v1/exams/templates/{template_id}/').status_code, 204)

    def test_invalid_templates_are_rejected(self):
        self.auth(self.teacher_token)
        bad_item_sets = {
            'break at the end': [
                {'type': 'section', 'key': 'a', 'title': 'A', 'minutes': 10},
                {'type': 'break', 'key': 'r', 'title': 'R', 'minutes': 5}],
            'duplicate key': [
                {'type': 'section', 'key': 'a', 'title': 'A', 'minutes': 10},
                {'type': 'section', 'key': 'a', 'title': 'B', 'minutes': 10}],
            'no section': [{'type': 'offline', 'key': 'x', 'title': 'X'}],
            'zero minutes': [{'type': 'section', 'key': 'a', 'title': 'A', 'minutes': 0}],
            'bad key': [{'type': 'section', 'key': 'A b', 'title': 'A', 'minutes': 5}],
            'too long': [{'type': 'section', 'key': 'a', 'title': 'A', 'minutes': 300},
                         {'type': 'section', 'key': 'b', 'title': 'B', 'minutes': 300},
                         {'type': 'section', 'key': 'c', 'title': 'C', 'minutes': 300}],
        }
        for name, items in bad_item_sets.items():
            resp = self.client.post('/api/v1/exams/templates/', {
                'name': 'x', 'items': items}, format='json')
            self.assertEqual(resp.status_code, 400, name)
            self.assertIn('items', resp.json()['error']['details'], name)

    def test_student_cannot_create_templates(self):
        self.auth(self.child_token)
        resp = self.client.post('/api/v1/exams/templates/', {
            'name': 'x', 'items': [{'type': 'section', 'key': 'a', 'title': 'A', 'minutes': 5}]},
            format='json')
        self.assertEqual(resp.status_code, 403)


class ExamCreateTests(ExamTestBase):
    def test_create_ielts_exam(self):
        sections = [{'key': k, 'quiz': self.quiz()} for k in ('listening', 'reading', 'writing')]
        with self.captureOnCommitCallbacks(execute=True):
            resp = self.create_exam('ielts', sections)
        self.assertEqual(resp.status_code, 201, resp.content)
        body = resp.json()
        self.assertEqual(body['template_key'], 'ielts')
        self.assertEqual(body['total_minutes'], 150)
        self.assertEqual(body['state'], 'upcoming')
        self.assertEqual([s['key'] for s in body['sections']], ['listening', 'reading', 'writing', 'speaking'])
        speaking = body['sections'][3]
        self.assertEqual(speaking['kind'], 'offline')
        self.assertIsNone(speaking['starts_at'])
        self.assertTrue(body['sections'][2]['manual'])
        # imtihon chegaralari ketma-ket
        self.assertEqual(body['sections'][0]['ends_at'], body['sections'][1]['starts_at'])
        # yozilgan o'quvchiga bildirishnoma bordi
        self.assertEqual(Notification.objects.filter(kind='exam_scheduled').count(), 1)

    def test_sat_preset_includes_break_in_timeline(self):
        sections = [{'key': k, 'quiz': self.quiz()} for k in ('rw_1', 'rw_2', 'math_1', 'math_2')]
        body = self.create_exam('sat', sections).json()
        self.assertEqual(body['total_minutes'], 32 + 32 + 10 + 35 + 35)
        kinds = [s['kind'] for s in body['sections']]
        self.assertEqual(kinds, ['section', 'section', 'break', 'section', 'section'])

    def test_section_minutes_can_be_overridden(self):
        resp = self.create_exam('milliy', [{'key': 'main', 'quiz': self.quiz(), 'minutes': 90}])
        self.assertEqual(resp.json()['total_minutes'], 90)

    def test_validation_errors(self):
        quiz = self.quiz()
        cases = {
            'missing section': self.create_exam('ielts', [{'key': 'listening', 'quiz': quiz}]),
            'unknown key': self.create_exam('milliy', [{'key': 'main', 'quiz': quiz}, {'key': 'zzz', 'quiz': quiz}]),
            'past start': self.create_exam('milliy', [{'key': 'main', 'quiz': quiz}], starts_in=-5),
            'unknown template': self.create_exam('toefl', [{'key': 'main', 'quiz': quiz}]),
        }
        for name, resp in cases.items():
            self.assertEqual(resp.status_code, 400, name)
        # bir test ikki bo'limda
        self.assertEqual(self.create_exam('sat', [
            {'key': 'rw_1', 'quiz': quiz}, {'key': 'rw_2', 'quiz': quiz},
            {'key': 'math_1', 'quiz': self.quiz()}, {'key': 'math_2', 'quiz': self.quiz()},
        ]).status_code, 400)

    def test_draft_quiz_cannot_be_attached(self):
        self.auth(self.teacher_token)
        draft = self.client.post('/api/v1/quizzes/', {
            'course': self.course_id, 'topic': 'T', 'status': 'draft',
            'questions': [{'type': 'single', 'text': 'Q', 'options': [
                {'text': 'a', 'is_correct': False}, {'text': 'b', 'is_correct': False}]}],
        }, format='json')
        self.assertEqual(draft.status_code, 201, draft.content)
        resp = self.create_exam('milliy', [{'key': 'main', 'quiz': draft.json()['id']}])
        self.assertEqual(resp.status_code, 400)

    def test_only_course_teacher_can_create_and_only_with_own_quizzes(self):
        quiz = self.quiz()
        self.assertEqual(
            self.create_exam('milliy', [{'key': 'main', 'quiz': quiz}], token=self.teacher2_token).status_code, 403)
        self.assertEqual(
            self.create_exam('milliy', [{'key': 'main', 'quiz': quiz}], token=self.child_token).status_code, 403)

    def test_edit_and_delete_only_before_start(self):
        exam = self.make_exam()
        self.auth(self.teacher_token)
        resp = self.client.patch(f'/api/v1/exams/{exam["id"]}/', {'title': 'Yangi nom'}, format='json')
        self.assertEqual(resp.json()['title'], 'Yangi nom')
        later = (timezone.now() + timedelta(days=3)).isoformat()
        resp = self.client.patch(f'/api/v1/exams/{exam["id"]}/', {'starts_at': later}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['total_minutes'], 25)
        self.shift(exam['id'], 1)
        self.assertEqual(self.client.patch(
            f'/api/v1/exams/{exam["id"]}/', {'title': 'x'}, format='json').status_code, 400)
        self.assertEqual(self.client.delete(f'/api/v1/exams/{exam["id"]}/').status_code, 400)

    def test_delete_before_start(self):
        exam = self.make_exam()
        self.auth(self.teacher_token)
        self.assertEqual(self.client.delete(f'/api/v1/exams/{exam["id"]}/').status_code, 204)
        self.assertFalse(Exam.objects.exists())


class ExamTakingTests(ExamTestBase):
    def test_upcoming_exam_has_no_questions(self):
        exam = self.make_exam()
        body = self.current(exam['id']).json()
        self.assertEqual(body['state'], 'upcoming')
        self.assertIsNone(body['item'])
        self.assertIn('server_now', body)

    def test_timeline_phases_follow_the_server_clock(self):
        exam = self.make_exam()
        self.shift(exam['id'], 3)
        body = self.current(exam['id']).json()
        self.assertEqual((body['state'], body['item']['key'], body['item']['kind']), ('running', 'a', 'section'))
        self.assertEqual(body['next']['kind'], 'break')
        self.assertEqual(len(body['item']['questions']), 2)

        self.shift(exam['id'], 12)
        body = self.current(exam['id']).json()
        self.assertEqual(body['item']['kind'], 'break')
        self.assertNotIn('questions', body['item'])

        self.shift(exam['id'], 18)
        body = self.current(exam['id']).json()
        self.assertEqual(body['item']['key'], 'b')
        self.assertIsNone(body['next'])

        self.shift(exam['id'], 40)
        body = self.current(exam['id']).json()
        self.assertEqual((body['state'], body['item']), ('finished', None))

    def test_questions_never_leak_the_answer_key(self):
        exam = self.make_exam()
        self.shift(exam['id'], 1)
        text = self.current(exam['id']).content.decode()
        self.assertNotIn('is_correct', text)
        self.assertNotIn('answer_key', text)

    def test_outsider_and_foreign_course_get_404(self):
        exam = self.make_exam()
        self.shift(exam['id'], 1)
        self.assertEqual(self.current(exam['id'], self.outsider_token).status_code, 404)
        self.auth(self.outsider_token)
        self.assertEqual(self.client.get(f'/api/v1/exams/{exam["id"]}/').status_code, 404)
        self.assertEqual(self.client.get('/api/v1/exams/').json(), [])

    def test_save_answers_and_restore_after_refresh(self):
        exam = self.make_exam()
        self.shift(exam['id'], 3)
        answers = self.answers_for(self.qa)
        self.assertEqual(self.save(exam['id'], answers).json()['saved'], 2)
        body = self.current(exam['id']).json()
        self.assertEqual(len(body['item']['saved']), 2)
        # qayta yuborsa ustiga yozadi (avtosaqlash)
        wrong = self.answers_for(self.qa, correct=False)
        self.assertEqual(self.save(exam['id'], wrong).status_code, 200)
        from .models import ExamAnswer
        self.assertEqual(ExamAnswer.objects.count(), 2)
        self.assertEqual(sum(a.earned_points for a in ExamAnswer.objects.all()), 0)

    def test_cannot_answer_other_sections_or_after_time(self):
        exam = self.make_exam()
        self.shift(exam['id'], 3)  # hozir A bo'limi
        self.assertEqual(self.save(exam['id'], self.answers_for(self.qb)).status_code, 403)
        # A tugadi (10 daqiqa) + GRACE (5 soniya) dan keyin A javobi rad etiladi
        self.shift(exam['id'], 10, seconds=30)
        self.assertEqual(self.save(exam['id'], self.answers_for(self.qa)).status_code, 403)

    def test_last_second_autosave_is_accepted_within_grace(self):
        exam = self.make_exam()
        self.shift(exam['id'], 10, seconds=2)
        self.assertEqual(self.save(exam['id'], self.answers_for(self.qa)).status_code, 200)

    def test_cannot_answer_before_start(self):
        exam = self.make_exam()
        self.assertEqual(self.save(exam['id'], self.answers_for(self.qa)).status_code, 403)

    def test_foreign_questions_rejected(self):
        exam = self.make_exam()
        self.shift(exam['id'], 3)
        other = self.quiz()
        self.assertEqual(self.save(exam['id'], self.answers_for(other)).status_code, 400)

    def test_finish_early_blocks_further_answers(self):
        exam = self.make_exam()
        self.shift(exam['id'], 3)
        self.save(exam['id'], self.answers_for(self.qa))
        self.auth(self.child_token)
        self.assertEqual(self.client.post(f'/api/v1/exams/{exam["id"]}/finish/').status_code, 200)
        self.assertEqual(self.current(exam['id']).json()['state'], 'submitted')
        self.assertEqual(self.save(exam['id'], self.answers_for(self.qa)).status_code, 403)

    def test_teacher_cannot_take_exam(self):
        exam = self.make_exam()
        self.shift(exam['id'], 3)
        self.assertEqual(self.current(exam['id'], self.teacher_token).status_code, 403)


class ExamResultsTests(ExamTestBase):
    def finished_exam(self):
        exam = self.make_exam()
        self.shift(exam['id'], 3)
        self.save(exam['id'], [self.answers_for(self.qa)[0]])  # A: 1 ta to'g'ri / 2 savol = 50%
        self.shift(exam['id'], 18)
        self.save(exam['id'], self.answers_for(self.qb, correct=False))  # B: 0%
        return exam

    def test_student_sees_result_only_after_exam_ends(self):
        exam = self.finished_exam()
        body = self.results(exam['id'], self.child_token).json()
        self.assertTrue(body['results'][0]['hidden'])
        self.shift(exam['id'], 40)
        item = self.results(exam['id'], self.child_token).json()['results'][0]
        self.assertEqual(item['total']['score'], 25.0)  # (50% + 0%) / 2
        by_key = {s['key']: s for s in item['sections']}
        self.assertEqual((by_key['a']['earned'], by_key['a']['max']), (2.0, 4.0))
        self.assertEqual(by_key['b']['percent'], 0.0)

    def test_teacher_sees_everyone_including_absent(self):
        exam = self.finished_exam()
        self.shift(exam['id'], 40)
        body = self.results(exam['id'], self.teacher_token).json()
        self.assertEqual(len(body['results']), 1)  # kursda faqat s1 bor
        # s2 ni ham kursga yozib, kelmagan sifatida ko'rinishini tekshiramiz
        from apps.accounts.models import User
        from apps.lessons.models import Enrollment
        Enrollment.objects.create(
            course_id=self.course_id, student=User.objects.get(username='s2'),
            status=Enrollment.Status.APPROVED,
        )
        body = self.results(exam['id'], self.teacher_token).json()
        absent = [r for r in body['results'] if not r['participated']]
        self.assertEqual([r['student']['username'] for r in absent], ['s2'])

    def test_student_never_sees_classmates(self):
        exam = self.finished_exam()
        self.shift(exam['id'], 40)
        from apps.accounts.models import User
        from apps.lessons.models import Enrollment
        Enrollment.objects.create(
            course_id=self.course_id, student=User.objects.get(username='s2'),
            status=Enrollment.Status.APPROVED,
        )
        body = self.results(exam['id'], self.child_token).json()
        self.assertEqual([r['student']['username'] for r in body['results']], ['s1'])
        other = User.objects.get(username='s2')
        self.auth(self.child_token)
        self.assertEqual(
            self.client.get(f'/api/v1/exams/{exam["id"]}/results/{other.id}/').status_code, 404)

    def test_parent_sees_child_result_after_end(self):
        exam = self.finished_exam()
        self.auth(self.parent_token)
        self.assertEqual(len(self.client.get('/api/v1/exams/').json()), 1)
        self.assertTrue(self.results(exam['id'], self.parent_token).json()['results'][0]['hidden'])
        self.shift(exam['id'], 40)
        item = self.results(exam['id'], self.parent_token).json()['results'][0]
        self.assertEqual(item['total']['score'], 25.0)

    def test_pass_mark_in_custom_scoring(self):
        template = self.custom_template(scoring_cfg={'scale': 50, 'pass_percent': 20})
        qa, qb = self.quiz(), self.quiz()
        exam = self.create_exam(template, [{'key': 'a', 'quiz': qa}, {'key': 'b', 'quiz': qb}]).json()
        self.shift(exam['id'], 3)
        self.save(exam['id'], self.answers_for(qa))  # A to'liq
        self.shift(exam['id'], 40)
        item = self.results(exam['id'], self.child_token).json()['results'][0]
        self.assertEqual(item['total']['score'], 25.0)  # 50% * 50
        self.assertTrue(item['total']['passed'])


class IeltsManualScoreTests(ExamTestBase):
    def ielts_exam(self):
        quizzes = {k: self.quiz(count=1) for k in ('listening', 'reading', 'writing')}
        exam = self.create_exam('ielts', [{'key': k, 'quiz': q} for k, q in quizzes.items()]).json()
        self.shift(exam['id'], 5)
        self.save(exam['id'], self.answers_for(quizzes['listening']))
        self.shift(exam['id'], 35)
        self.save(exam['id'], self.answers_for(quizzes['reading']))
        self.shift(exam['id'], 100)
        from apps.accounts.models import User
        self.student_id = User.objects.get(username='s1').id
        return exam, quizzes

    def put_manual(self, exam_id, scores, token=None):
        self.auth(token or self.teacher_token)
        return self.client.put(
            f'/api/v1/exams/{exam_id}/results/{self.student_id}/manual/', {'scores': scores}, format='json')

    def test_overall_band_after_teacher_scores_writing_and_speaking(self):
        exam, _quizzes = self.ielts_exam()
        self.shift(exam['id'], 200)
        before = self.results(exam['id'], self.teacher_token).json()['results'][0]
        self.assertIsNone(before['total'])
        self.assertEqual(before['pending'], ['writing', 'speaking'])

        resp = self.put_manual(exam['id'], {'writing': 7, 'speaking': 6.5})
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertEqual(body['total']['score'], 8.0)  # (9 + 9 + 7 + 6.5) / 4 = 7.875 -> 8.0
        self.assertEqual({s['key']: s['score'] for s in body['sections']},
                         {'listening': 9.0, 'reading': 9.0, 'writing': 7.0, 'speaking': 6.5})

    def test_manual_score_validation_and_permissions(self):
        exam, _quizzes = self.ielts_exam()
        self.assertEqual(self.put_manual(exam['id'], {'writing': 7.3}).status_code, 400)
        self.assertEqual(self.put_manual(exam['id'], {'listening': 7}).status_code, 400)
        self.assertEqual(self.put_manual(exam['id'], {'writing': 7}, token=self.child_token).status_code, 403)
        self.assertEqual(self.put_manual(exam['id'], {'writing': 7}, token=self.teacher2_token).status_code, 404)

    def test_teacher_sees_written_answers_for_manual_sections(self):
        exam, quizzes = self.ielts_exam()  # hozir Writing davri
        self.save(exam['id'], self.answers_for(quizzes['writing']))
        self.shift(exam['id'], 200)
        self.auth(self.teacher_token)
        detail = self.client.get(f'/api/v1/exams/{exam["id"]}/results/{self.student_id}/').json()
        self.assertEqual([a['section'] for a in detail['manual_answers']], ['writing'])
        # o'quvchining o'ziga yozma javoblar bloki qaytmaydi
        self.auth(self.child_token)
        own = self.client.get(f'/api/v1/exams/{exam["id"]}/results/{self.student_id}/').json()
        self.assertNotIn('manual_answers', own)


class QuizGuardTests(ExamTestBase):
    def test_attached_quiz_cannot_be_edited_or_deleted(self):
        exam = self.make_exam()
        self.auth(self.teacher_token)
        patch = self.client.patch(f'/api/v1/quizzes/{self.qa}/', {'questions': [
            {'type': 'single', 'text': 'Yangi', 'options': [
                {'text': 'a', 'is_correct': True}, {'text': 'b', 'is_correct': False}]}]}, format='json')
        self.assertEqual(patch.status_code, 400)
        self.assertEqual(self.client.delete(f'/api/v1/quizzes/{self.qa}/').status_code, 400)
        # metadata (nom/mavzu) o'zgartirilishi mumkin
        ok = self.client.patch(f'/api/v1/quizzes/{self.qa}/', {'title': 'Yangi nom'}, format='json')
        self.assertEqual(ok.status_code, 200)
        self.assertTrue(Exam.objects.filter(pk=exam['id']).exists())
