"""Speaking (audio) uy vazifasi: OpenAI avval ovozni matnga aylantiradi, keyin matn + ravonlik statistikasi baholanadi.
Talaffuz AI tomonidan baholanmaydi — o'qituvchiga aniq aytiladi. Soxta OpenAI bilan."""
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from apps.lessons.models import Course
from apps.quizzes import llm
from apps.quizzes.tests_ai_exam import completion, error, reply

from . import services
from .models import Submission
from .tests_hardening import HomeworkBase

LLM_ON = dict(OPENAI_API_KEY='sk-test', OPENAI_MODEL='gpt-test', OPENAI_BASE_URL='https://llm.test/v1', OPENAI_STT_MODEL='whisper-1')

TEXT = 'I think learning english is very important because it helps me to find a good job and to travel'
WORDS = TEXT.split()


def word_timings(pause_after=None, pause=3.0):
    """Har so'z 0.4 s; `pause_after` — shu indeksdagi so'zdan keyin `pause` soniyalik jimlik."""
    cursor, rows = 0.0, []
    for index, word in enumerate(WORDS):
        rows.append({'word': word, 'start': round(cursor, 2), 'end': round(cursor + 0.4, 2)})
        cursor += 0.4 + (pause if index == pause_after else 0.0)
    return rows


SPEAKING_GRADE = {
    'overall_score': 70,
    'questions': [
        {'question_number': 1, 'question': 'Fluency and Coherence', 'student_answer': 'one pause', 'analysis': 'Ravon', 'score': 75},
        {'question_number': 2, 'question': 'Lexical Resource', 'student_answer': 'good job, travel', 'analysis': "Oddiy so'zlar", 'score': 65},
        {'question_number': 3, 'question': 'Grammatical Range and Accuracy', 'student_answer': 'it helps me to find', 'analysis': "To'g'ri", 'score': 70},
    ],
    'summary': {'strengths': ['Aniq fikr'], 'weaknesses': ['Qisqa'], 'topics_to_review': ['Linking words'], 'recommendations': ['Ko\'proq gapiring']},
}


class FakeOpenAI:
    """/audio/transcriptions va /chat/completions ni ajratib javob beradi, hamma chaqiruvni yozib boradi."""

    def __init__(self, transcription=None, grading=None):
        self.transcription = transcription if transcription is not None else reply(
            200, {'text': TEXT, 'duration': 6.5, 'words': word_timings(pause_after=5), 'segments': [{'avg_logprob': -0.2}]})
        self.grading = grading if grading is not None else completion(SPEAKING_GRADE)
        self.calls = []

    def __call__(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.transcription if url.endswith('/audio/transcriptions') else self.grading

    def urls(self):
        return [url.rsplit('/v1', 1)[-1] for url, _ in self.calls]


@override_settings(**LLM_ON)
class SpeakingAiTests(HomeworkBase):
    def setUp(self):
        super().setUp()
        from unittest.mock import patch

        self.fake = FakeOpenAI()
        patcher = patch('apps.quizzes.llm.requests.post', side_effect=self.fake)
        patcher.start()
        self.addCleanup(patcher.stop)
        Course.objects.filter(pk=self.course.pk).update(subject=Course.Subject.ENGLISH)

    def speaking(self, name='speech.mp3', **assignment):
        upload = SimpleUploadedFile(name, b'ID3' + b'0' * 400, content_type='audio/mpeg')
        resp = self.submit(self.assignment(skill_key='speaking', title='Talk about English', **assignment), upload)
        self.assertEqual(resp.status_code, 201, resp.content)
        return Submission.objects.get(pk=resp.data['id'])

    def test_audio_is_transcribed_then_graded_and_handed_to_the_teacher(self):
        submission = self.speaking()
        self.assertEqual(self.fake.calls, [])  # topshirish so'rovi ichida AI chaqirilmaydi
        self.assertEqual(services.sync_ai_results(), {'done': 1, 'failed': 0, 'waiting': 0})
        submission.refresh_from_db()
        self.assertEqual(submission.status, 'pending_review')
        self.assertEqual(self.fake.urls(), ['/audio/transcriptions', '/chat/completions'])
        result = submission.result
        self.assertEqual((result['source'], result['engine']), ('audio-transcript', 'openai'))
        self.assertEqual(result['transcript'], TEXT)
        self.assertEqual(len(result['questions']), 3)
        self.assertEqual(result['delivery']['words'], len(WORDS))
        self.assertEqual(result['delivery']['pauses'], 1)
        self.assertEqual(result['delivery']['longest_pause_seconds'], 3.0)
        self.assertIn('Talaffuz', result['summary']['recommendations'][0])  # talaffuz baholanmagani o'qituvchiga aytiladi
        self.assertEqual(result['summary']['recommendations'][1], "Ko'proq gapiring")
        self.assertEqual(submission.ai_overall_score, 70.0)

    def test_transcription_request_carries_the_file_model_and_language_hint(self):
        self.speaking()
        services.sync_ai_results()
        url, kwargs = self.fake.calls[0]
        self.assertTrue(url.endswith('/audio/transcriptions'))
        self.assertEqual(kwargs['data']['model'], 'whisper-1')
        self.assertEqual(kwargs['data']['language'], 'en')
        self.assertEqual(kwargs['data']['response_format'], 'verbose_json')
        self.assertEqual(kwargs['files']['file'][0], 'speech.mp3')
        self.assertTrue(kwargs['files']['file'][1].startswith(b'ID3'))
        self.assertEqual(kwargs['headers']['Authorization'], 'Bearer sk-test')

    def test_grading_prompt_marks_the_text_as_a_transcript_and_forbids_judging_pronunciation(self):
        self.speaking(extra_instructions='Part 2 style')
        services.sync_ai_results()
        payload = self.fake.calls[1][1]['json']
        system, user = payload['messages'][0]['content'], payload['messages'][1]['content']
        self.assertIn('SPEAKING MODE', system)
        self.assertIn('do NOT judge pronunciation', system)
        self.assertIn(TEXT, user)
        self.assertIn('DELIVERY STATISTICS', user)
        self.assertIn('words_per_minute', user)
        self.assertIn('Part 2 style', user)

    def test_silent_or_too_short_recording_goes_to_the_teacher_without_paying_for_grading(self):
        self.fake.transcription = reply(200, {'text': 'Hmm yes', 'duration': 1.0, 'words': [], 'segments': []})
        submission = self.speaking()
        self.assertEqual(services.sync_ai_results(), {'done': 0, 'failed': 1, 'waiting': 0})
        submission.refresh_from_db()
        self.assertEqual(submission.status, 'pending_review')
        self.assertIn('eshitilmadi', submission.error)
        self.assertEqual(self.fake.urls(), ['/audio/transcriptions'])  # baholash so'rovi yuborilmadi

    def test_corrupt_audio_is_rejected_permanently_with_a_clear_note(self):
        self.fake.transcription = error(400, message='Invalid file format')
        submission = self.speaking()
        self.assertEqual(services.sync_ai_results(), {'done': 0, 'failed': 1, 'waiting': 0})
        submission.refresh_from_db()
        self.assertEqual(submission.status, 'pending_review')
        self.assertIn("o'qib bo'lmadi", submission.error)

    def test_temporary_transcription_failure_is_retried_next_cycle(self):
        self.fake.transcription = error(500)
        submission = self.speaking()
        self.assertEqual(services.sync_ai_results(), {'done': 0, 'failed': 0, 'waiting': 1})
        submission.refresh_from_db()
        self.assertEqual(submission.status, 'checking')
        self.fake.transcription = reply(200, {'text': TEXT, 'duration': 6.5, 'words': word_timings(), 'segments': []})
        self.assertEqual(services.sync_ai_results(), {'done': 1, 'failed': 0, 'waiting': 0})

    def test_invalid_key_goes_to_manual_without_leaking_the_key(self):
        self.fake.transcription = error(401)
        submission = self.speaking()
        services.sync_ai_results()
        submission.refresh_from_db()
        self.assertEqual(submission.status, 'pending_review')
        self.assertNotIn('sk-test', submission.error)

    def test_other_audio_formats_use_the_same_path(self):
        for name in ('voice.m4a', 'voice.wav', 'voice.ogg'):
            self.fake.calls.clear()
            self.speaking(name)
            services.sync_ai_results()
            self.assertEqual(self.fake.calls[0][1]['files']['file'][0], name)


@override_settings(**{**LLM_ON, 'OPENAI_STT_MODEL': 'gpt-4o-mini-transcribe'})
class TranscribeFormatTests(HomeworkBase):
    def test_non_whisper_models_get_plain_json_without_word_timestamps(self):
        from unittest.mock import patch

        fake = FakeOpenAI(transcription=reply(200, {'text': TEXT}))
        with patch('apps.quizzes.llm.requests.post', side_effect=fake):
            spoken = llm.transcribe(b'ID3', 'a.mp3')
        data = fake.calls[0][1]['data']
        self.assertEqual((data['model'], data['response_format']), ('gpt-4o-mini-transcribe', 'json'))
        self.assertNotIn('timestamp_granularities[]', data)
        self.assertNotIn('language', data)
        self.assertEqual((spoken['text'], spoken['words']), (TEXT, []))
