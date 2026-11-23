"""AI test: mavzu aniq yozilsa katta materialdan (kitob) aynan shu mavzuga oid qismlar olinadi va mavzu majburiy.
Kitob sarlavhasi/mundarijasi haqida savol chiqmasin. (Butun ish oqimi testlari — tests_ai_exam.py, AiExamJobTests.)"""
import json
from unittest.mock import patch

from django.test import SimpleTestCase

from . import ai_exam, material_text

COVER = 'GRAMMAR IN USE. Cover page, contents, preface and publisher notes. ' * 900          # ~60 000 belgi
CHAPTER = ('Using the verb to be: I am a student, he is a teacher, they are friends. To be or not to be. '
           'The verb to be has three present forms. ') * 12                                   # ~1 300 belgi
BACK = 'Appendix: irregular verbs, answer keys and index. ' * 900                              # ~45 000 belgi
BOOK = COVER + CHAPTER + BACK


class SelectRelevantTests(SimpleTestCase):
    def test_short_material_is_returned_whole(self):
        self.assertEqual(material_text.select_relevant('Short text about bees.', 'bees', 1000), 'Short text about bees.')

    def test_a_big_book_is_searched_for_the_topic_not_read_from_the_front(self):
        picked = material_text.select_relevant(BOOK, 'to be', 40000)
        self.assertIn('Using the verb to be', picked)
        self.assertLessEqual(len(picked), 40000)
        # eski xatti-harakat (boshidan kesish) bu bo'limni umuman ko'rmasdi
        self.assertNotIn('Using the verb to be', BOOK[:40000])

    def test_without_a_topic_or_when_nothing_matches_it_still_reads_from_the_front(self):
        self.assertEqual(material_text.select_relevant(BOOK, '', 40000), BOOK[:40000])
        self.assertEqual(material_text.select_relevant(BOOK, 'photosynthesis', 40000), BOOK[:40000])

    def test_uzbek_word_endings_still_match(self):
        text = 'Mundarija va so\'zboshi. ' * 2000 + 'Kvadrat tenglamani yechish: diskriminant topiladi. ' * 30 + 'Ilova. ' * 500
        self.assertIn('Kvadrat tenglamani yechish', material_text.select_relevant(text, 'Kvadrat tenglamalar', 5000))

    def test_selected_parts_keep_their_original_order(self):
        text = ('intro ' * 700) + 'alpha topic marker one. ' * 5 + ('filler ' * 2500) + 'topic marker two. ' * 5 + ('end ' * 700)
        picked = material_text.select_relevant(text, 'topic marker', 3200)
        self.assertLess(picked.index('marker one'), picked.index('marker two'))

    def test_every_file_of_several_gets_its_own_topic_relevant_share(self):
        combined = material_text.combine_texts([('a.txt', BOOK), ('b.txt', BOOK)], 40000, topic='to be')
        first, second = combined.split('=== b.txt ===')
        self.assertIn('Using the verb to be', first)
        self.assertIn('Using the verb to be', second)
        self.assertIn('=== a.txt ===', first)

    def test_combine_texts_is_unchanged_without_a_topic(self):
        self.assertEqual(material_text.combine_texts([('a.txt', BOOK)], 100), BOOK[:100])


class WriterPromptTests(SimpleTestCase):
    PLAN = ai_exam.default_plan(5)

    def payload(self, topic):
        with patch('apps.quizzes.llm.chat_json', return_value={'passage': '', 'questions': []}) as chat:
            ai_exam.generate_section(self.PLAN, 0, 'material', avoid_topics=[], topic=topic)
        return json.loads(chat.call_args.args[1])

    def test_the_topic_is_binding_and_the_book_itself_is_off_limits(self):
        for phrase in ('EVERY question must test that topic', 'NEVER write questions about the document itself',
                       'table of contents'):
            self.assertIn(phrase, ai_exam._WRITER_SYSTEM)

    def test_a_given_topic_becomes_the_section_focus(self):
        payload = self.payload('to be')
        self.assertEqual(payload['topic'], 'to be')
        self.assertIn('to be', payload['section_spec']['focus'])

    def test_no_topic_means_no_focus_hint(self):
        self.assertEqual(self.payload('')['section_spec']['focus'], '')
