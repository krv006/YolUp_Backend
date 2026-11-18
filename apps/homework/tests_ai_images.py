"""AI ga beriladigan rasmlar: EXIF aylantirish, ko'p fayl, doska sahifalari, PDF/Word ichidagi rasmlar, vazifa sharti rasmi, HEIC."""
import base64
import io
import zipfile
from unittest.mock import patch

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings
from PIL import Image

from apps.quizzes.tests_ai_exam import completion, make_pdf

from . import ai_grader, images as hw_images, services
from .models import Assignment, Submission
from .tests_ai_engine import GRADE, LLM_ON, FakeGrader
from .tests_hardening import HomeworkBase


def jpeg_bytes(size=(1200, 800), *, exif_orientation=None, color='white'):
    image = Image.new('RGB', size, color)
    buffer = io.BytesIO()
    if exif_orientation:
        exif = image.getexif()
        exif[274] = exif_orientation
        image.save(buffer, 'JPEG', exif=exif)
    else:
        image.save(buffer, 'JPEG')
    return buffer.getvalue()


def png_bytes(size=(1200, 800)):
    buffer = io.BytesIO()
    Image.new('RGB', size, 'white').save(buffer, 'PNG')
    return buffer.getvalue()


def image_pdf(count, size=(900, 1200)):
    """`count` sahifali PDF, har sahifada bitta katta rasm (doska PDF'i kabi)."""
    pages = [Image.new('RGB', size, 'white') for _ in range(count)]
    buffer = io.BytesIO()
    pages[0].save(buffer, 'PDF', save_all=True, append_images=pages[1:])
    return buffer.getvalue()


def mixed_pdf():
    """1-sahifa: matn, 2-sahifa: qo'lyozma surati (aralash PDF)."""
    from pypdf import PdfReader, PdfWriter

    writer = PdfWriter()
    writer.add_page(PdfReader(io.BytesIO(make_pdf('Savol 1: x=2 va x=3. Savol 2: x=5. ' * 4))).pages[0])
    writer.add_page(PdfReader(io.BytesIO(image_pdf(1))).pages[0])
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def docx_with(images: list, text='Birinchi masalaning yechimi quyidagicha: x=2 va x=3, ikkinchisi esa x=5. ' * 3):
    from docx import Document

    document = Document()
    document.add_paragraph(text)
    for data in images:
        document.add_picture(io.BytesIO(data))
    out = io.BytesIO()
    document.save(out)
    return out.getvalue()


def sent_images(fake):
    """So'nggi AI so'rovidagi rasmlar: [PIL.Image]."""
    content = fake.payloads[-1]['messages'][1]['content']
    if not isinstance(content, list):
        return []
    out = []
    for part in content[1:]:
        data = part['image_url']['url'].split(',', 1)[1]
        out.append(Image.open(io.BytesIO(base64.b64decode(data))))
    return out


def prompt_text(fake):
    content = fake.payloads[-1]['messages'][1]['content']
    return content if isinstance(content, str) else content[0]['text']


@override_settings(HOMEWORK_AI_IMAGE_TOKEN_BUDGET=10**9, **LLM_ON)  # sahifa soni/tartibi testlari: byudjet cheklamasin (byudjet alohida sinaladi)
class AiImageBase(HomeworkBase):
    def setUp(self):
        super().setUp()
        self.fake = FakeGrader()
        patcher = patch('apps.quizzes.llm.requests.post', side_effect=self.fake)
        patcher.start()
        self.addCleanup(patcher.stop)

    def post(self, assignment_id, *uploads):
        resp = self.api(self.student).post(
            f'/api/v1/homework/assignments/{assignment_id}/submit/', {'files': list(uploads)}, format='multipart')
        self.assertEqual(resp.status_code, 201, resp.content)
        return Submission.objects.get(pk=resp.data['id'])

    def grade(self):
        services.sync_ai_results()
        self.assertTrue(self.fake.payloads, 'AI chaqirilmadi')


class ExifTests(SimpleTestCase):
    def test_a_phone_photo_stored_sideways_is_turned_upright(self):
        # EXIF=6: kamera 90° burilgan; 400x200 saqlangan, aslida 200x400 bo'lishi kerak
        image = hw_images.open_image(jpeg_bytes((400, 200), exif_orientation=6))
        self.assertEqual(image.size, (200, 400))

    def test_a_photo_without_exif_is_untouched(self):
        self.assertEqual(hw_images.open_image(jpeg_bytes((400, 200))).size, (400, 200))

    def test_broken_bytes_raise_a_clear_error(self):
        with self.assertRaises(hw_images.ImageError):
            hw_images.open_image(b'not an image')


class PhotoTests(AiImageBase):
    def test_the_ai_gets_the_photo_upright(self):
        assignment_id = self.assignment()
        self.post(assignment_id, SimpleUploadedFile('ish.jpg', jpeg_bytes((400, 200), exif_orientation=6), content_type='image/jpeg'))
        self.grade()
        [image] = sent_images(self.fake)
        self.assertEqual(image.size, (200, 400))


class MultiFileTests(AiImageBase):
    def test_every_uploaded_photo_reaches_the_ai_not_only_the_first(self):
        assignment_id = self.assignment()
        files = [SimpleUploadedFile(f'{n}.png', png_bytes(), content_type='image/png') for n in range(3)]
        self.post(assignment_id, *files)
        self.grade()
        self.assertEqual(len(sent_images(self.fake)), 3)

    def test_text_of_all_files_is_combined(self):
        assignment_id = self.assignment()
        first = SimpleUploadedFile('a.pdf', make_pdf('BIRINCHI-FAYL ' * 8), content_type='application/pdf')
        second = SimpleUploadedFile('b.pdf', make_pdf('IKKINCHI-FAYL ' * 8), content_type='application/pdf')
        self.post(assignment_id, first, second)
        self.grade()
        text = prompt_text(self.fake)
        self.assertIn('BIRINCHI-FAYL', text)
        self.assertIn('IKKINCHI-FAYL', text)

    def test_text_file_plus_photo_sends_both(self):
        assignment_id = self.assignment()
        first = SimpleUploadedFile('a.pdf', make_pdf('MATNLI-FAYL ' * 8), content_type='application/pdf')
        second = SimpleUploadedFile('b.png', png_bytes(), content_type='image/png')
        self.post(assignment_id, first, second)
        self.grade()
        self.assertIn('MATNLI-FAYL', prompt_text(self.fake))
        self.assertEqual(len(sent_images(self.fake)), 1)


class BoardPagesTests(AiImageBase):
    def test_a_long_board_is_sent_up_to_the_image_limit_and_the_rest_is_reported(self):
        assignment_id = self.assignment()
        pages = ai_grader.MAX_IMAGES + 3
        submission = self.post(assignment_id, SimpleUploadedFile('doska.pdf', image_pdf(pages), content_type='application/pdf'))
        self.grade()
        self.assertEqual(len(sent_images(self.fake)), ai_grader.MAX_IMAGES)
        submission.refresh_from_db()
        self.assertEqual(submission.ai_result['skipped_images'], 3)
        note = submission.ai_result['summary']['recommendations'][0]
        self.assertIn('3 ta', note)

    def test_a_board_that_fits_reports_nothing_skipped(self):
        assignment_id = self.assignment()
        submission = self.post(assignment_id, SimpleUploadedFile('doska.pdf', image_pdf(8), content_type='application/pdf'))
        self.grade()
        self.assertEqual(len(sent_images(self.fake)), 8)
        submission.refresh_from_db()
        self.assertNotIn('skipped_images', submission.ai_result)

    def test_many_pages_are_sent_smaller_to_keep_the_price_down(self):
        assignment_id = self.assignment()
        self.post(assignment_id, SimpleUploadedFile('doska.pdf', image_pdf(8, size=(3000, 4000)), content_type='application/pdf'))
        self.grade()
        for image in sent_images(self.fake):
            self.assertLessEqual(max(image.size), hw_images.IMAGE_SIDE_MANY)

    def test_few_pages_keep_the_full_size(self):
        assignment_id = self.assignment()
        self.post(assignment_id, SimpleUploadedFile('doska.pdf', image_pdf(2, size=(3000, 4000)), content_type='application/pdf'))
        self.grade()
        sizes = [max(image.size) for image in sent_images(self.fake)]
        self.assertTrue(all(hw_images.IMAGE_SIDE_MANY < size <= hw_images.IMAGE_SIDE for size in sizes), sizes)


class EmbeddedImageTests(AiImageBase):
    def test_a_pdf_with_text_and_a_handwriting_photo_sends_both(self):
        assignment_id = self.assignment()
        self.post(assignment_id, SimpleUploadedFile('ish.pdf', mixed_pdf(), content_type='application/pdf'))
        self.grade()
        self.assertIn('Savol 1', prompt_text(self.fake))
        self.assertEqual(len(sent_images(self.fake)), 1)

    def test_a_word_file_sends_its_text_and_its_pictures(self):
        assignment_id = self.assignment()
        data = docx_with([jpeg_bytes((800, 600))])
        self.post(assignment_id, SimpleUploadedFile('ish.docx', data, content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'))
        self.grade()
        self.assertIn('Birinchi masalaning yechimi', prompt_text(self.fake))
        self.assertEqual(len(sent_images(self.fake)), 1)

    def test_tiny_pictures_such_as_logos_are_ignored(self):
        data = docx_with([jpeg_bytes((64, 64)), jpeg_bytes((800, 600))])
        self.assertEqual(len(hw_images.docx_images(data)), 1)

    def test_a_word_file_with_only_pictures_is_graded_from_them(self):
        assignment_id = self.assignment()
        data = docx_with([jpeg_bytes((800, 600))], text='x')
        self.post(assignment_id, SimpleUploadedFile('ish.docx', data, content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'))
        self.grade()
        self.assertEqual(len(sent_images(self.fake)), 1)

    def test_a_corrupt_archive_gives_no_images_instead_of_crashing(self):
        self.assertEqual(hw_images.docx_images(b'not a zip'), [])
        self.assertEqual(hw_images.pdf_images(b'%PDF-1.4 broken'), [])

    def test_docx_pictures_keep_document_order_by_number(self):
        out = io.BytesIO()
        with zipfile.ZipFile(out, 'w') as archive:
            for number in (10, 2, 1):
                archive.writestr(f'word/media/image{number}.png', png_bytes((400 + number, 400)))
        sizes = [Image.open(io.BytesIO(data)).size[0] for _mime, data in hw_images.docx_images(out.getvalue())]
        self.assertEqual(sizes, [401, 402, 410])


class TaskImageTests(AiImageBase):
    def with_attachment(self, name, data):
        assignment_id = self.assignment()
        assignment = Assignment.objects.get(pk=assignment_id)
        assignment.attachment.save(name, ContentFile(data), save=False)
        assignment.attachment_name = name
        assignment.save()
        return assignment_id

    def test_a_task_photo_is_shown_to_the_ai_before_the_student_work(self):
        assignment_id = self.with_attachment('shart.png', png_bytes((900, 300)))
        self.post(assignment_id, SimpleUploadedFile('ish.png', png_bytes((300, 900)), content_type='image/png'))
        self.grade()
        task, work = sent_images(self.fake)
        self.assertEqual((task.size, work.size), ((900, 300), (300, 900)))
        text = prompt_text(self.fake)
        self.assertIn('ASSIGNMENT IMAGES: the first 1 attached image', text)
        self.assertIn('The last 1 attached image', text)

    def test_a_text_task_file_adds_no_task_image(self):
        assignment_id = self.with_attachment('shart.pdf', make_pdf('Shart matni: tenglamani yeching. ' * 4))
        self.post(assignment_id, SimpleUploadedFile('ish.png', png_bytes(), content_type='image/png'))
        self.grade()
        self.assertEqual(len(sent_images(self.fake)), 1)
        self.assertNotIn('ASSIGNMENT IMAGES', prompt_text(self.fake))
        self.assertIn('Shart matni', prompt_text(self.fake))

    def test_an_unreadable_task_file_does_not_stop_grading(self):
        assignment_id = self.with_attachment('shart.png', b'broken')
        self.post(assignment_id, SimpleUploadedFile('ish.png', png_bytes(), content_type='image/png'))
        self.grade()
        self.assertEqual(len(sent_images(self.fake)), 1)


class HeicTests(AiImageBase):
    def heic(self, size=(600, 400)):
        from pillow_heif import register_heif_opener

        register_heif_opener()
        buffer = io.BytesIO()
        Image.new('RGB', size, 'white').save(buffer, 'HEIF')
        return buffer.getvalue()

    def test_an_iphone_photo_is_stored_as_jpeg_and_graded(self):
        assignment_id = self.assignment()
        submission = self.post(assignment_id, SimpleUploadedFile('IMG_1.HEIC', self.heic(), content_type='image/heic'))
        self.assertEqual(submission.original_name, 'IMG_1.jpg')
        with submission.file.open('rb') as handle:
            self.assertEqual(Image.open(handle).format, 'JPEG')
        self.grade()
        self.assertEqual(len(sent_images(self.fake)), 1)

    def test_extra_heic_files_are_converted_too(self):
        assignment_id = self.assignment()
        first = SimpleUploadedFile('a.png', png_bytes(), content_type='image/png')
        second = SimpleUploadedFile('b.heif', self.heic(), content_type='image/heif')
        submission = self.post(assignment_id, first, second)
        self.assertEqual([f.original_name for f in submission.extra_files.all()], ['b.jpg'])

    def test_a_broken_heic_is_rejected_with_a_clear_message(self):
        assignment_id = self.assignment()
        resp = self.api(self.student).post(
            f'/api/v1/homework/assignments/{assignment_id}/submit/',
            {'file': SimpleUploadedFile('IMG_2.heic', b'not heic', content_type='image/heic')}, format='multipart')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('HEIC', str(resp.json()))
        self.assertFalse(Submission.objects.exists())

    def test_an_oversized_heic_is_rejected_by_size(self):
        assignment_id = self.assignment()
        with patch('apps.homework.rules.MAX_FILE_SIZE_MB', 0):
            resp = self.api(self.student).post(
                f'/api/v1/homework/assignments/{assignment_id}/submit/',
                {'file': SimpleUploadedFile('big.heic', self.heic(), content_type='image/heic')}, format='multipart')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('MB', str(resp.json()))


class TokenEstimateTests(SimpleTestCase):
    def test_the_formula_matches_the_documented_openai_example(self):
        self.assertEqual(hw_images.estimate_tokens((1536, 1536)), 25501)   # OpenAI hujjati: gpt-4o-mini, 4 bo'lak
        self.assertEqual(hw_images.estimate_tokens((900, 1200)), 25501)
        self.assertEqual(hw_images.estimate_tokens((4000, 3000)), 25501)

    def test_small_and_thin_images(self):
        self.assertEqual(hw_images.estimate_tokens((512, 512)), 2833 + 5667)
        self.assertEqual(hw_images.estimate_tokens((200, 100)), 2833 + 5667)
        self.assertEqual(hw_images.estimate_tokens((768, 2048)), 2833 + 5667 * 2 * 4)

    def test_fit_budget_keeps_order_and_always_keeps_the_first(self):
        pages = [hw_images.to_jpeg(Image.new('RGB', (900, 1200), 'white')) for _ in range(5)]
        kept, dropped = hw_images.fit_budget(pages, 80_000)
        self.assertEqual((len(kept), dropped), (3, 2))
        kept, dropped = hw_images.fit_budget(pages, 1)  # byudjet bitta rasmga ham yetmasa ham birinchisi qoladi
        self.assertEqual((len(kept), dropped), (1, 4))
        kept, dropped = hw_images.fit_budget(pages, 10**9)
        self.assertEqual((len(kept), dropped), (5, 0))
        self.assertEqual(hw_images.fit_budget([], 80_000), ([], 0))


@override_settings(**LLM_ON)
class TokenBudgetTests(AiImageBase):
    """Standart byudjet (80 000): 128 000 tokenli kontekstga sig'maydigan so'rov butunlay rad etilmasin, ortiqcha sahifa "sig'madi" bo'lsin."""

    def test_a_long_board_sends_only_what_fits_the_context_and_reports_the_rest(self):
        with override_settings(HOMEWORK_AI_IMAGE_TOKEN_BUDGET=80_000):
            assignment_id = self.assignment()
            submission = self.post(assignment_id, SimpleUploadedFile('doska.pdf', image_pdf(8), content_type='application/pdf'))
            self.grade()
            sent = sent_images(self.fake)
            self.assertEqual(len(sent), 3)
            total = sum(hw_images.estimate_tokens(image.size) for image in sent)
            self.assertLessEqual(total, 80_000)
            submission.refresh_from_db()
            self.assertEqual(submission.ai_result['skipped_images'], 5)
            self.assertIn('5 ta', submission.ai_result['summary']['recommendations'][0])

    def test_the_default_budget_leaves_room_in_a_128k_context(self):
        import importlib

        base = importlib.import_module('root.settings.base')  # sinfdagi override'siz haqiqiy standart qiymat
        # rasmlar + matn (~41 000 belgi ~ 12 000 token) + chiqish tokenlari kontekstdan oshmasin
        self.assertLessEqual(base.HOMEWORK_AI_IMAGE_TOKEN_BUDGET + 12_000 + base.OPENAI_MAX_OUTPUT_TOKENS, 128_000)

    def test_a_task_photo_takes_part_of_the_budget(self):
        with override_settings(HOMEWORK_AI_IMAGE_TOKEN_BUDGET=80_000):
            assignment_id = TaskImageTests.with_attachment(self, 'shart.png', png_bytes((900, 1200)))
            self.post(assignment_id, SimpleUploadedFile('doska.pdf', image_pdf(4), content_type='application/pdf'))
            self.grade()
            sent = sent_images(self.fake)
            # 1 ta shart rasmi (25 501) + 2 ta sahifa (51 002) = 76 503; 3-sahifa sig'maydi
            self.assertEqual(len(sent), 3)
            self.assertIn('ASSIGNMENT IMAGES: the first 1 attached image', prompt_text(self.fake))
