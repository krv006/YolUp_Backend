"""Insho (Writing) savoli: yozma javob saqlanadi, avtomatik baholanmaydi va umumiy ballni buzmaydi."""
from .models import Quiz
from .tests_question_types import QuizTestBase

ESSAY = {'type': 'essay', 'text': 'Some people think... Discuss both views.', 'points': 9, 'min_words': 250}
SINGLE = {'type': 'single', 'text': '2+2?', 'points': 2, 'options': [
    {'text': '3', 'is_correct': False}, {'text': '4', 'is_correct': True}]}


class EssayQuestionTests(QuizTestBase):
    def quiz(self, **extra):
        resp = self.make_quiz([SINGLE, ESSAY])
        self.assertEqual(resp.status_code, 201, resp.content)
        return resp.json()

    def test_an_essay_needs_no_answer_key_and_keeps_its_word_minimum(self):
        created = self.quiz()
        essay = self.of_type(created['questions'], 'essay')
        self.assertEqual((essay['min_words'], essay['points']), (250, 9))
        self.assertNotIn('accepted_answers', essay)

    def test_students_see_the_minimum_but_no_key(self):
        quiz_id = self.quiz()['id']
        essay = self.of_type(self.take(quiz_id)['questions'], 'essay')
        self.assertEqual(essay['min_words'], 250)
        self.assertEqual(set(essay) - {'min_words'}, {'id', 'type', 'text', 'points', 'order', 'group', 'options'})

    def test_the_essay_is_saved_but_not_scored_and_not_in_the_maximum(self):
        created = self.quiz()
        essay = self.of_type(created['questions'], 'essay')
        single = self.of_type(created['questions'], 'single')
        right = next(o['id'] for o in self.take(created['id'])['questions'][0]['options'] if o['text'] == '4')
        text = 'In my opinion ' + 'word ' * 300
        resp = self.submit(created['id'], [
            {'question': single['id'], 'selected_option': right}, {'question': essay['id'], 'value_text': text}])
        self.assertEqual(resp.status_code, 201, resp.content)
        body = resp.json()
        self.assertEqual((body['score'], body['max_score']), (2, 2))  # insho maksimumga kirmaydi
        saved = next(a for a in body['answers'] if a['question_type'] == 'essay')
        self.assertEqual(saved['given_display'].split()[0:3], ['In', 'my', 'opinion'])
        self.assertEqual(saved['earned_points'], 0)

    def test_an_empty_essay_is_just_unanswered(self):
        created = self.quiz()
        essay = self.of_type(created['questions'], 'essay')
        resp = self.submit(created['id'], [{'question': essay['id'], 'value_text': '   '}])
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.json()['score'], 0)

    def test_an_essay_can_be_in_a_published_quiz_without_any_answer(self):
        created = self.quiz()
        self.assertEqual(Quiz.objects.get(pk=created['id']).status, Quiz.Status.PUBLISHED)

    def test_the_downloaded_copies_show_a_writing_area_and_no_answer(self):
        quiz_id = self.quiz()['id']
        self.auth(self.teacher_token)
        for mode in ('student', 'teacher'):
            resp = self.client.get(f'/api/v1/quizzes/{quiz_id}/export/?type=csv&mode={mode}')
            self.assertEqual(resp.status_code, 200)
            self.assertIn('250', resp.content.decode('utf-8-sig'))
