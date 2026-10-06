"""`ai.grade_file` — yangi `google-genai` mijozi bilan ishlash (Client soxta).

Asl `homework/tests.py` testlari `grade_file` ni butunlay soxtalashtiradi, shuning
uchun Gemini'ga so'rov qanday tuzilishi (model, sozlamalar, fayl qismlari,
qayta urinish) shu yerda sinaladi."""
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings
from google.genai import types
from PIL import Image

from . import ai
from .tests import FAKE_RESULT

GOOD = json.dumps(FAKE_RESULT)


def fake_client(*responses):
    """`genai.Client(...)` o'rniga: ketma-ket berilgan javoblarni qaytaradi
    (matn yoki Exception)."""
    client = MagicMock()
    side_effect = [
        r if isinstance(r, Exception) else SimpleNamespace(text=r) for r in responses
    ]
    client.models.generate_content.side_effect = side_effect
    return client


@override_settings(GEMINI_API_KEY='test-key', GEMINI_MODEL='test-model')
@patch('apps.homework.ai.time.sleep', lambda *_: None)
class GradeFileTests(SimpleTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def image(self, size=(40, 30)):
        path = self.dir / 'work.png'
        Image.new('RGB', size, 'white').save(path)
        return path

    def run_grade(self, client, path, **kwargs):
        with patch('google.genai.Client', return_value=client) as client_cls:
            result = ai.grade_file(path, **kwargs)
        return result, client_cls

    def test_image_is_sent_as_jpeg_part_with_system_prompt_and_config(self):
        client = fake_client(GOOD)
        result, client_cls = self.run_grade(client, self.image(), subject_text='math')
        self.assertEqual(result['overall_score'], 78)

        client_cls.assert_called_once()
        self.assertEqual(client_cls.call_args.kwargs['api_key'], 'test-key')
        self.assertEqual(client_cls.call_args.kwargs['http_options'].timeout, ai.REQUEST_TIMEOUT_MS)

        call = client.models.generate_content.call_args.kwargs
        self.assertEqual(call['model'], 'test-model')
        config = call['config']
        self.assertEqual(config.response_mime_type, 'application/json')
        self.assertEqual(config.temperature, 0.1)
        self.assertEqual(config.max_output_tokens, 8192)
        self.assertIn('Mathematics teacher', config.system_instruction)

        prompt, part = call['contents']
        self.assertIsInstance(prompt, str)
        self.assertEqual(part.inline_data.mime_type, 'image/jpeg')
        self.assertTrue(part.inline_data.data.startswith(b'\xff\xd8'))  # JPEG

    def test_docx_text_is_extracted_locally(self):
        import docx

        path = self.dir / 'work.docx'
        document = docx.Document()
        document.add_paragraph('2x + 3 = 7, x = 2')
        document.save(path)
        client = fake_client(GOOD)
        self.run_grade(client, path)
        contents = client.models.generate_content.call_args.kwargs['contents']
        self.assertTrue(all(isinstance(c, str) for c in contents))
        self.assertIn('2x + 3 = 7, x = 2', contents[1])

    def test_pdf_is_sent_inline_when_small(self):
        path = self.dir / 'work.pdf'
        path.write_bytes(b'%PDF-1.4 fake')
        client = fake_client(GOOD)
        self.run_grade(client, path)
        part = client.models.generate_content.call_args.kwargs['contents'][1]
        self.assertEqual(part.inline_data.mime_type, 'application/pdf')
        client.files.upload.assert_not_called()

    def test_large_file_goes_through_the_files_api(self):
        path = self.dir / 'speech.mp3'
        path.write_bytes(b'0' * 64)
        client = fake_client(GOOD)
        client.files.upload.return_value = SimpleNamespace(name='files/abc', state='ACTIVE')
        with patch.object(ai, 'INLINE_SIZE_LIMIT_BYTES', 10):
            self.run_grade(client, path, skill_key='speaking')
        upload = client.files.upload.call_args.kwargs
        self.assertEqual(upload['file'], str(path))
        self.assertEqual(upload['config'].mime_type, 'audio/mpeg')
        sent = client.models.generate_content.call_args.kwargs['contents'][1]
        self.assertEqual(sent.name, 'files/abc')

    def test_large_file_waits_until_processing_finishes(self):
        path = self.dir / 'speech.mp3'
        path.write_bytes(b'0' * 64)
        client = fake_client(GOOD)
        client.files.upload.return_value = SimpleNamespace(name='files/abc', state='FileState.PROCESSING')
        client.files.get.side_effect = [
            SimpleNamespace(name='files/abc', state='FileState.PROCESSING'),
            SimpleNamespace(name='files/abc', state='FileState.ACTIVE'),
        ]
        with patch.object(ai, 'INLINE_SIZE_LIMIT_BYTES', 10):
            self.run_grade(client, path)
        self.assertEqual(client.files.get.call_count, 2)
        self.assertEqual(client.models.generate_content.call_args.kwargs['contents'][1].state,
                         'FileState.ACTIVE')

    def test_failed_file_processing_raises(self):
        path = self.dir / 'speech.mp3'
        path.write_bytes(b'0' * 64)
        client = fake_client(GOOD)
        client.files.upload.return_value = SimpleNamespace(name='files/abc', state='FileState.FAILED')
        with patch.object(ai, 'INLINE_SIZE_LIMIT_BYTES', 10):
            with self.assertRaises(ai.HomeworkAIError):
                self.run_grade(client, path)
        client.models.generate_content.assert_not_called()

    def test_invalid_json_is_retried_with_a_correction_hint(self):
        client = fake_client('bu json emas', GOOD)
        result, _cls = self.run_grade(client, self.image())
        self.assertEqual(result['grade'], 'Yaxshi')
        self.assertEqual(client.models.generate_content.call_count, 2)
        second = client.models.generate_content.call_args.kwargs['contents']
        self.assertIn('not valid JSON', second[-1])

    def test_blocked_response_without_text_is_retried(self):
        client = MagicMock()
        client.models.generate_content.side_effect = [SimpleNamespace(text=None), SimpleNamespace(text=GOOD)]
        result, _cls = self.run_grade(client, self.image())
        self.assertEqual(result['overall_score'], 78)

    def test_api_errors_are_retried_then_succeed(self):
        client = fake_client(RuntimeError('503'), GOOD)
        result, _cls = self.run_grade(client, self.image())
        self.assertEqual(result['overall_score'], 78)
        self.assertEqual(client.models.generate_content.call_count, 2)

    def test_gives_up_after_all_retries(self):
        client = fake_client(RuntimeError('a'), RuntimeError('b'), RuntimeError('kvota tugadi'))
        with self.assertRaises(ai.HomeworkAIError) as ctx:
            self.run_grade(client, self.image())
        self.assertIn('3 urinishdan keyin', str(ctx.exception))
        self.assertIn('kvota tugadi', str(ctx.exception))

    @override_settings(GEMINI_API_KEY='')
    def test_missing_key_is_a_clear_error(self):
        with self.assertRaises(ai.HomeworkAIError) as ctx:
            ai.grade_file(self.image())
        self.assertIn('GEMINI_API_KEY', str(ctx.exception))

    def test_real_sdk_types_accept_our_arguments(self):
        """Soxta Client'siz: SDK'ning o'z tiplari bizning sozlamalarimizni qabul qiladi
        (paket versiyasi o'zgarib API buzilsa — shu test qizaradi)."""
        config = types.GenerateContentConfig(system_instruction='s', **ai.GENERATION_CONFIG)
        self.assertEqual(config.top_p, 0.9)
        types.HttpOptions(timeout=ai.REQUEST_TIMEOUT_MS)
        types.UploadFileConfig(mime_type='audio/mpeg')
        types.Part.from_bytes(data=b'x', mime_type='image/jpeg')
