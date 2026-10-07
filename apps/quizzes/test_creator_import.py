"""Test-creator (RJalol/Test-creator) JSON eksportini import qilish.

JSON — Test-creator'ning eng aniq eksport formati (Word/Excel'dan farqli, matn
qayta ishlanmaydi). O'qituvchi nusxasi (`mode=teacher`) har savolda to'g'ri variantlar
(`correct_options`) va javobni (`correct_answer`) o'z ichiga oladi; talaba nusxasida
javoblar yo'q — savollar javobsiz qoralamaga tushadi va `warnings`da belgilanadi.

Qaytaradi: `docx_import.parse_docx_questions` bilan bir xil preview strukturasi.
"""
import json
import re

MAX_QUESTION_POINTS = 100


def _points(value):
    try:
        return min(MAX_QUESTION_POINTS, max(1, int(round(float(value)))))
    except (TypeError, ValueError):
        return None


def _answer_strings(answer) -> list:
    """`correct_answer` (Test-creator'da JSONB — shakli savol turiga bog'liq) -> javob matnlari ro'yxati."""
    if answer is None:
        return []
    if isinstance(answer, dict):
        for key in ('answers', 'accepted_answers', 'value', 'text', 'answer', 'correct', 'label'):
            if key in answer:
                return _answer_strings(answer[key])
        return []
    if isinstance(answer, (list, tuple)):
        found = []
        for item in answer:
            found.extend(_answer_strings(item))
        return found
    text = str(answer).strip()
    return [text] if text else []


def _non_option_question(row: dict, text: str, order: int):
    """Variantsiz savol (qisqa javob, son, to'g'ri/noto'g'ri) -> bizning turlarga."""
    qtype = str(row.get('question_type') or '').lower()
    answers = _answer_strings(row.get('correct_answer'))
    lowered = {a.lower() for a in answers}
    question = {'text': text, 'order': order}

    if 'true' in qtype or 'bool' in qtype or (answers and lowered <= {'true', 'false', "to'g'ri", "noto'g'ri"}):
        if answers:
            question.update(type='true_false', correct_bool=lowered <= {'true', "to'g'ri"})
            return question, True
        return {**question, 'type': 'true_false', 'correct_bool': True}, False

    def is_number(value):
        try:
            float(value.replace(',', '.').replace(' ', ''))
            return True
        except ValueError:
            return False

    if answers and ('numer' in qtype or 'number' in qtype or all(is_number(a) for a in answers)):
        question.update(type='numeric', accepted_answers=answers, tolerance=0)
        return question, True
    question.update(type='text', accepted_answers=answers, case_sensitive=False)
    return question, bool(answers)


def parse_test_creator_json(file_obj) -> dict:
    data = file_obj.read() if hasattr(file_obj, 'read') else file_obj
    if isinstance(data, (bytes, bytearray)):
        data = bytes(data).decode('utf-8-sig')
    payload = json.loads(data)
    if isinstance(payload, list):
        rows, title, version = payload, '', None
    elif isinstance(payload, dict) and isinstance(payload.get('questions'), list):
        rows, title, version = payload['questions'], str(payload.get('title') or ''), payload.get('version')
    else:
        raise ValueError("Test-creator JSON'ida 'questions' ro'yxati topilmadi.")

    rows = sorted((r for r in rows if isinstance(r, dict)), key=lambda r: r.get('order') or 0)
    questions, warnings = [], []
    for row in rows:
        text = str(row.get('question_text') or '').strip()
        if not text:
            continue
        order = len(questions)
        options = row.get('options') or []
        if options:
            correct = {str(label).strip().upper() for label in (row.get('correct_options') or [])}
            question = {
                'text': text, 'order': order,
                'options': [
                    {'text': str(o.get('text') or '').strip(),
                     'is_correct': str(o.get('label') or '').strip().upper() in correct, 'order': i}
                    for i, o in enumerate(options)
                ],
            }
            if len(correct) > 1:
                question['type'] = 'multiple'
            hits = sum(1 for o in question['options'] if o['is_correct'])
            if len(options) < 2:
                warnings.append({'question_number': order + 1, 'reason': 'not_enough_options'})
            elif hits != 1 and not (question.get('type') == 'multiple' and hits >= 2):
                warnings.append({'question_number': order + 1, 'reason': 'answer_not_detected'})
        else:
            question, has_answer = _non_option_question(row, text, order)
            if not has_answer:
                warnings.append({'question_number': order + 1, 'reason': 'answer_not_detected'})
        points = _points(row.get('points'))
        if points is not None:
            question['points'] = points
        questions.append(question)

    description = f'Test-creator eksporti (versiya {version})' if version else ''
    return {'title': title[:200], 'description': description, 'questions': questions, 'warnings': warnings}


def is_json(filename: str) -> bool:
    return bool(re.search(r'\.json$', filename or '', re.IGNORECASE))
