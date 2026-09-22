"""Savol turlari: yaratish, o'quvchi ko'rinishi, baholash (BACKEND_QUIZ_TYPES.md)."""
from rest_framework.test import APITestCase

from apps.accounts.tests import login, register

from .models import Question


class QuizTestBase(APITestCase):
    def setUp(self):
        register(self.client, 't1', 'teacher')
        self.teacher_token = login(self.client, 't1')
        register(self.client, 'p1', 'parent')
        self.parent_token = login(self.client, 'p1')
        self.auth(self.parent_token)
        child = self.client.post('/api/v1/auth/children/', {'username': 's1', 'password': 'StrongPass123!'})
        self.child_id = child.json()['id']
        self.child_token = login(self.client, 's1')
        self.auth(self.teacher_token)
        self.course_id = self.client.post(
            '/api/v1/courses/', {'title': 'Mix', 'subject': 'math'}).json()['id']
        self.auth(self.parent_token)
        self.client.post(f'/api/v1/courses/{self.course_id}/enroll/', {'student_id': self.child_id})
        self.auth(self.teacher_token)
        for req in self.client.get('/api/v1/courses/requests/').json()['results']:
            self.client.post('/api/v1/courses/requests/respond/', {
                'enrollment_id': req['id'], 'action': 'approve'})

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def make_quiz(self, questions):
        self.auth(self.teacher_token)
        return self.client.post('/api/v1/quizzes/', {
            'course': self.course_id, 'topic': 'Mavzu', 'title': 'T', 'questions': questions}, format='json')

    def take(self, quiz_id):
        self.auth(self.child_token)
        return self.client.get(f'/api/v1/quizzes/{quiz_id}/').json()

    def submit(self, quiz_id, answers):
        self.auth(self.child_token)
        return self.client.post(
            f'/api/v1/quizzes/{quiz_id}/attempts/', {'answers': answers}, format='json')

    @staticmethod
    def of_type(questions, qtype):
        return next(q for q in questions if q['type'] == qtype)


class QuestionTypesTests(QuizTestBase):
    ALL_TYPES = [
        {'type': 'single', 'text': 'S', 'points': 5, 'options': [
            {'text': '3/4', 'is_correct': True}, {'text': '2/3', 'is_correct': False}]},
        {'type': 'multiple', 'text': 'M', 'options': [
            {'text': '2', 'is_correct': True}, {'text': '4', 'is_correct': False},
            {'text': '7', 'is_correct': True}]},
        {'type': 'true_false', 'text': 'TF', 'correct_bool': False},
        {'type': 'numeric', 'text': 'N', 'accepted_answers': ['3.14'], 'tolerance': 0.01},
        {'type': 'text', 'text': 'X', 'accepted_answers': ['Toshkent', 'Tashkent']},
        {'type': 'matching', 'text': 'MT', 'pairs': [
            {'left': 'Fransiya', 'right': 'Parij'}, {'left': 'Misr', 'right': 'Qohira'}]},
        {'type': 'ordering', 'text': 'O', 'items': ['1/4', '1/2', '3/4']},
        {'type': 'fill_blank', 'text': 'Suv {{1}} da qaynaydi, {{2}} da muzlaydi',
         'blanks': [{'answers': ['100']}, {'answers': ['0', 'nol']}]},
    ]

    def test_create_all_types_and_teacher_detail(self):
        resp = self.make_quiz(self.ALL_TYPES)
        self.assertEqual(resp.status_code, 201, resp.content)
        qs = resp.json()['questions']
        self.assertEqual([q['type'] for q in qs], [q['type'] for q in self.ALL_TYPES])
        self.assertEqual(self.of_type(qs, 'single')['points'], 5)
        self.assertEqual(self.of_type(qs, 'multiple')['points'], 2)
        self.assertIs(self.of_type(qs, 'true_false')['correct_bool'], False)
        self.assertEqual(self.of_type(qs, 'numeric')['tolerance'], 0.01)
        self.assertEqual(self.of_type(qs, 'text')['accepted_answers'], ['Toshkent', 'Tashkent'])
        self.assertEqual(self.of_type(qs, 'matching')['pairs'][1], {'left': 'Misr', 'right': 'Qohira'})
        self.assertEqual(self.of_type(qs, 'ordering')['items'], ['1/4', '1/2', '3/4'])
        self.assertEqual(self.of_type(qs, 'fill_blank')['blanks'][1]['answers'], ['0', 'nol'])

    def test_legacy_payload_without_type_is_single(self):
        resp = self.make_quiz([{'text': 'Q', 'options': [
            {'text': 'a', 'is_correct': True}, {'text': 'b', 'is_correct': False}]}])
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()['questions'][0]['type'], 'single')
        self.assertEqual(resp.json()['questions'][0]['points'], 2)

    def test_student_view_hides_answer_key(self):
        quiz_id = self.make_quiz(self.ALL_TYPES).json()['id']
        qs = self.take(quiz_id)['questions']
        for q in qs:
            for secret in ('correct_bool', 'accepted_answers', 'tolerance', 'pairs', 'items', 'blanks'):
                self.assertNotIn(secret, q)
            for o in q['options']:
                self.assertNotIn('is_correct', o)
        matching = self.of_type(qs, 'matching')
        left_ids = {p['id'] for p in matching['pairs_left']}
        right_ids = {p['id'] for p in matching['pairs_right']}
        self.assertEqual(len(left_ids), 2)
        self.assertFalse(left_ids & right_ids)
        self.assertEqual(len(self.of_type(qs, 'ordering')['options']), 3)
        self.assertEqual(self.of_type(qs, 'fill_blank')['blank_count'], 2)

    def correct_answers(self, qs):
        answers = []
        for q in qs:
            db = Question.objects.get(pk=q['id'])
            t = q['type']
            if t == 'single':
                opt = next(o for o in db.options.all() if o.is_correct)
                answers.append({'question': q['id'], 'selected_option': str(opt.id)})
            elif t == 'multiple':
                ids = [str(o.id) for o in db.options.all() if o.is_correct]
                answers.append({'question': q['id'], 'selected_options': ids})
            elif t == 'true_false':
                answers.append({'question': q['id'], 'value_bool': False})
            elif t == 'numeric':
                answers.append({'question': q['id'], 'value_text': '3,145'})
            elif t == 'text':
                answers.append({'question': q['id'], 'value_text': '  toshkent '})
            elif t == 'matching':
                answers.append({'question': q['id'], 'pairs': [
                    {'left': p['left_id'], 'right': p['right_id']} for p in db.answer_key['pairs']]})
            elif t == 'ordering':
                answers.append({'question': q['id'], 'order': [str(o.id) for o in db.options.all()]})
            elif t == 'fill_blank':
                answers.append({'question': q['id'], 'blanks': ['100', 'NOL']})
        return answers

    def test_perfect_attempt_scores_full_marks(self):
        quiz_id = self.make_quiz(self.ALL_TYPES).json()['id']
        qs = self.take(quiz_id)['questions']
        resp = self.submit(quiz_id, self.correct_answers(qs))
        self.assertEqual(resp.status_code, 201, resp.content)
        body = resp.json()
        self.assertEqual(body['max_score'], 5 + 2 * 7)
        self.assertEqual(body['score'], body['max_score'])
        self.assertTrue(all(a['is_correct'] and a['earned_points'] == a['points'] for a in body['answers']))
        numeric = next(a for a in body['answers'] if a['question_type'] == 'numeric')
        self.assertEqual(numeric['correct_display'], '3.14 (±0.01)')
        matching = next(a for a in body['answers'] if a['question_type'] == 'matching')
        self.assertEqual(matching['correct_display'], 'Fransiya → Parij; Misr → Qohira')
        ordering = next(a for a in body['answers'] if a['question_type'] == 'ordering')
        self.assertEqual(ordering['given_display'], '1/4 → 1/2 → 3/4')

    def test_wrong_and_partial_answers(self):
        quiz_id = self.make_quiz(self.ALL_TYPES).json()['id']
        qs = self.take(quiz_id)['questions']
        m = self.of_type(qs, 'matching')
        p1, p2 = Question.objects.get(pk=m['id']).answer_key['pairs']
        o = self.of_type(qs, 'ordering')
        reversed_order = [str(x.id) for x in reversed(list(Question.objects.get(pk=o['id']).options.all()))]
        mu = self.of_type(qs, 'multiple')
        only_one = [str(next(x for x in Question.objects.get(pk=mu['id']).options.all() if x.is_correct).id)]
        answers = [
            {'question': self.of_type(qs, 'true_false')['id'], 'value_bool': True},
            {'question': self.of_type(qs, 'numeric')['id'], 'value_text': '3.2'},
            {'question': self.of_type(qs, 'text')['id'], 'value_text': 'Samarqand'},
            {'question': m['id'], 'pairs': [
                {'left': p1['left_id'], 'right': p1['right_id']},
                {'left': p2['left_id'], 'right': p1['right_id']}]},
            {'question': o['id'], 'order': reversed_order},
            {'question': mu['id'], 'selected_options': only_one},
            {'question': self.of_type(qs, 'fill_blank')['id'], 'blanks': ['100', '5']},
        ]
        body = self.submit(quiz_id, answers).json()
        by_type = {a['question_type']: a for a in body['answers']}
        self.assertEqual(by_type['true_false']['earned_points'], 0)
        self.assertEqual(by_type['numeric']['earned_points'], 0)
        self.assertEqual(by_type['text']['earned_points'], 0)
        self.assertEqual(by_type['matching']['earned_points'], 1)
        self.assertFalse(by_type['matching']['is_correct'])
        self.assertEqual(by_type['ordering']['earned_points'], 0)
        self.assertEqual(by_type['multiple']['earned_points'], 0)
        self.assertEqual(by_type['fill_blank']['earned_points'], 1)
        self.assertEqual(by_type['fill_blank']['given_display'], '100; 5')
        self.assertEqual(body['score'], 2.0)

    def test_unanswered_questions_listed_with_null_given(self):
        quiz_id = self.make_quiz(self.ALL_TYPES).json()['id']
        qs = self.take(quiz_id)['questions']
        body = self.submit(quiz_id, [{'question': qs[0]['id'], 'selected_option': None}]).json()
        self.assertEqual(len(body['answers']), len(self.ALL_TYPES))
        self.assertTrue(all(a['given_display'] is None for a in body['answers']))
        self.assertEqual(body['score'], 0)

    def test_foreign_ids_rejected(self):
        quiz_id = self.make_quiz(self.ALL_TYPES).json()['id']
        qs = self.take(quiz_id)['questions']
        m = self.of_type(qs, 'matching')
        resp = self.submit(quiz_id, [{'question': m['id'], 'pairs': [{'left': 'x', 'right': 'y'}]}])
        self.assertEqual(resp.status_code, 400)
        o = self.of_type(qs, 'ordering')
        resp = self.submit(quiz_id, [{'question': o['id'], 'order': ['nope']}])
        self.assertEqual(resp.status_code, 400)

    def test_validation_errors(self):
        two_opts = [{'text': 'a', 'is_correct': True}, {'text': 'b'}]
        bad = [
            {'type': 'single', 'text': 'q', 'points': 0, 'options': two_opts},
            {'type': 'single', 'text': 'q', 'points': 101, 'options': two_opts},
            {'type': 'single', 'text': 'q', 'options': [
                {'text': 'a', 'is_correct': True}, {'text': 'b', 'is_correct': True}]},
            {'type': 'multiple', 'text': 'q', 'options': [{'text': 'a'}, {'text': 'b'}]},
            {'type': 'true_false', 'text': 'q'},
            {'type': 'numeric', 'text': 'q', 'accepted_answers': ['abc']},
            {'type': 'numeric', 'text': 'q', 'accepted_answers': ['1'], 'tolerance': -1},
            {'type': 'text', 'text': 'q', 'accepted_answers': []},
            {'type': 'matching', 'text': 'q', 'pairs': [{'left': 'a', 'right': 'b'}]},
            {'type': 'matching', 'text': 'q', 'pairs': [
                {'left': 'a', 'right': 'b'}, {'left': 'a', 'right': 'c'}]},
            {'type': 'ordering', 'text': 'q', 'items': ['only']},
            {'type': 'fill_blank', 'text': '{{1}} va {{2}}', 'blanks': [{'answers': ['x']}]},
            {'type': 'fill_blank', 'text': 'joy yoq', 'blanks': [{'answers': ['x']}]},
        ]
        for question in bad:
            resp = self.make_quiz([question])
            self.assertEqual(resp.status_code, 400, question)


class SubjectQuizTests(QuizTestBase):
    """Guruhsiz (fan bo'yicha) testlar — BACKEND_QUIZ_TYPES (2).md, 0-bo'lim."""

    QUESTION = [{'text': 'Q', 'options': [
        {'text': 'a', 'is_correct': True}, {'text': 'b', 'is_correct': False}]}]

    def make_subject_quiz(self, **extra):
        self.auth(self.teacher_token)
        payload = {
            'course': None, 'subject': 'chemistry', 'topic': 'Atom tuzilishi',
            'title': 'Kimyo', 'questions': self.QUESTION,
        }
        payload.update(extra)
        return self.client.post('/api/v1/quizzes/', payload, format='json')

    def test_create_without_course_needs_subject(self):
        resp = self.make_subject_quiz()
        self.assertEqual(resp.status_code, 201, resp.content)
        body = resp.json()
        self.assertIsNone(body['course'])
        self.assertEqual(body['subject'], 'chemistry')
        self.assertTrue(body['subject_label'])
        self.assertEqual(self.make_subject_quiz(subject='').status_code, 400)
        self.assertEqual(self.make_subject_quiz(subject='nope').status_code, 400)

    def test_neither_course_nor_subject_is_400(self):
        self.auth(self.teacher_token)
        resp = self.client.post(
            '/api/v1/quizzes/', {'topic': 'x', 'title': 'x', 'questions': self.QUESTION}, format='json',
        )
        self.assertEqual(resp.status_code, 400)

    def test_course_quiz_takes_subject_from_course(self):
        self.auth(self.teacher_token)
        resp = self.client.post('/api/v1/quizzes/', {
            'course': self.course_id, 'subject': 'chemistry', 'topic': 'x', 'title': 'x',
            'questions': self.QUESTION}, format='json')
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.json()['subject'], 'math')

    def test_ungrouped_quiz_cannot_have_lesson(self):
        import uuid
        self.assertEqual(self.make_subject_quiz(lesson=str(uuid.uuid4())).status_code, 400)

    def test_teacher_lists_grouped_and_ungrouped_and_course_filter(self):
        self.make_subject_quiz()
        self.make_quiz(self.QUESTION)
        self.auth(self.teacher_token)
        listing = self.client.get('/api/v1/quizzes/').json()
        rows = listing['results'] if isinstance(listing, dict) else listing
        self.assertEqual(len(rows), 2)
        filtered = self.client.get(f'/api/v1/quizzes/?course={self.course_id}').json()
        rows = filtered['results'] if isinstance(filtered, dict) else filtered
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['course'], self.course_id)

    def test_students_never_see_ungrouped_quiz(self):
        quiz_id = self.make_subject_quiz().json()['id']
        self.auth(self.child_token)
        self.assertEqual(self.client.get(f'/api/v1/quizzes/{quiz_id}/').status_code, 404)
        listing = self.client.get('/api/v1/quizzes/').json()
        rows = listing['results'] if isinstance(listing, dict) else listing
        self.assertEqual(rows, [])

    def test_author_sees_answer_key_and_only_author_manages(self):
        quiz_id = self.make_subject_quiz().json()['id']
        self.auth(self.teacher_token)
        detail = self.client.get(f'/api/v1/quizzes/{quiz_id}/').json()
        self.assertTrue(detail['questions'][0]['options'][0]['is_correct'])
        register(self.client, 't2', 'teacher')
        self.auth(login(self.client, 't2'))
        self.assertEqual(self.client.get(f'/api/v1/quizzes/{quiz_id}/').status_code, 404)
        self.assertEqual(self.client.delete(f'/api/v1/quizzes/{quiz_id}/').status_code, 404)
        self.auth(self.teacher_token)
        self.assertEqual(self.client.delete(f'/api/v1/quizzes/{quiz_id}/').status_code, 204)


class QuizTopicTests(QuizTestBase):
    """`topic` majburiy, `title` ixtiyoriy; ro'yxat/tafsilotda qaytadi; PATCH bilan tahrirlanadi."""

    def make_quiz_with(self, **extra):
        self.auth(self.teacher_token)
        payload = {
            'course': self.course_id, 'topic': 'Kasrlar', 'title': '', 'questions': [
                {'text': 'Q', 'options': [{'text': 'a', 'is_correct': True}, {'text': 'b'}]},
            ],
        }
        payload.update(extra)
        return self.client.post('/api/v1/quizzes/', payload, format='json')

    def test_topic_is_required(self):
        resp = self.make_quiz_with(topic='')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('topic', resp.json()['error']['details'])

    def test_topic_missing_entirely_is_400(self):
        self.auth(self.teacher_token)
        resp = self.client.post('/api/v1/quizzes/', {
            'course': self.course_id, 'title': 'x',
            'questions': [{'text': 'Q', 'options': [{'text': 'a', 'is_correct': True}, {'text': 'b'}]}],
        }, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_title_optional_topic_appears_in_list_and_detail(self):
        resp = self.make_quiz_with()
        self.assertEqual(resp.status_code, 201, resp.content)
        body = resp.json()
        self.assertEqual(body['title'], '')
        self.assertEqual(body['topic'], 'Kasrlar')

        self.auth(self.teacher_token)
        listing = self.client.get('/api/v1/quizzes/').json()
        rows = listing['results'] if isinstance(listing, dict) else listing
        self.assertEqual(rows[0]['topic'], 'Kasrlar')

        detail = self.client.get(f'/api/v1/quizzes/{body["id"]}/').json()
        self.assertEqual(detail['topic'], 'Kasrlar')

    def test_patch_updates_topic_and_title_only(self):
        quiz_id = self.make_quiz_with().json()['id']
        self.auth(self.teacher_token)
        resp = self.client.patch(f'/api/v1/quizzes/{quiz_id}/', {
            'topic': "O'nlik kasrlar", 'title': 'Yangilangan nom',
        }, format='json')
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()['topic'], "O'nlik kasrlar")
        self.assertEqual(resp.json()['title'], 'Yangilangan nom')
        # savollar tegmagan
        self.assertEqual(len(resp.json()['questions']), 1)

    def test_patch_rejects_blank_topic(self):
        quiz_id = self.make_quiz_with().json()['id']
        self.auth(self.teacher_token)
        resp = self.client.patch(f'/api/v1/quizzes/{quiz_id}/', {'topic': ''}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_patch_forbidden_for_non_owner(self):
        quiz_id = self.make_quiz_with().json()['id']
        register(self.client, 'topic_t2', 'teacher')
        self.auth(login(self.client, 'topic_t2'))
        resp = self.client.patch(f'/api/v1/quizzes/{quiz_id}/', {'topic': 'x'}, format='json')
        self.assertEqual(resp.status_code, 404)

    def test_search_by_topic_and_filter_by_subject(self):
        self.make_quiz_with(topic='Trigonometriya')
        self.make_quiz_with(topic='Algebra asoslari')
        self.auth(self.teacher_token)
        resp = self.client.get('/api/v1/quizzes/?search=Trigono').json()
        rows = resp['results'] if isinstance(resp, dict) else resp
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['topic'], 'Trigonometriya')

        resp = self.client.get('/api/v1/quizzes/?subject=math').json()
        rows = resp['results'] if isinstance(resp, dict) else resp
        self.assertEqual(len(rows), 2)
