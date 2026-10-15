"""Savollar banki (yengil variant): AI yaratgan har bir savol o'qituvchi + imtihon bo'yicha eslab qolinadi.

Hozirgi foydasi: shu o'qituvchi shu imtihondan yangi test yaratganda AI'ga "bu savollar allaqachon bor" deb
beriladi (`avoid_questions`) - testlar bir-birini takrorlamaydi. To'liq savol (javob kaliti bilan) `payload` da
saqlanadi, shuning uchun keyinchalik tayyor savollarni qayta ishlatish ham mumkin. Bank hech qachon test
yaratishni to'xtatmasligi kerak: barcha xatolar jim yutiladi (log bilan)."""
import hashlib
import json
import logging
import re

from .models import BankQuestion

logger = logging.getLogger(__name__)

AVOID_LIMIT = 40  # AI'ga ko'rsatiladigan oxirgi savollar soni
AVOID_CHARS = 140


def exam_key(job) -> str:
    return (job.exam_name or job.topic or '').strip().lower()[:120]


def digest(text: str) -> str:
    """Matn bir xil bo'lsa (harf registri, bo'sh joy va tinish belgilaridan qat'i nazar) - bir xil savol."""
    normal = re.sub(r'[\W_]+', ' ', str(text).lower()).strip()
    return hashlib.sha1(normal.encode('utf-8')).hexdigest()


def recent_texts(job) -> list:
    """Shu o'qituvchining shu imtihondagi oxirgi savollari (qisqartirilgan) - AI takrorlamasligi uchun."""
    try:
        rows = BankQuestion.objects.filter(teacher=job.teacher, exam_key=exam_key(job)) \
            .order_by('-created_at').values_list('text', flat=True)[:AVOID_LIMIT]
        return [text[:AVOID_CHARS] for text in rows]
    except Exception:  # noqa: BLE001 - bank yordamchi, test yaratishga xalaqit bermasin
        logger.exception("Savollar bankini o'qib bo'lmadi")
        return []


def _clean(question: dict, instruction: str) -> str:
    text = str(question.get('text') or '')
    prefix = f'{instruction}\n\n' if instruction else ''
    return text[len(prefix):] if prefix and text.startswith(prefix) else text


def remember(job, plan: dict, sections: dict) -> int:
    """Tayyor test savollarini bankka yozadi (takrorlar qo'shilmaydi). Qaytaradi: yangi qo'shilganlar soni."""
    try:
        key, rows, seen = exam_key(job), [], set()
        for index, section_plan in enumerate(plan['sections']):
            section = sections.get(str(index)) or {}
            for question in section.get('questions', []):
                block = question.get('block')
                blocks = section_plan['blocks']
                instruction = blocks[block]['instruction'] if isinstance(block, int) and block < len(blocks) else ''
                text = _clean(question, instruction).strip()
                fingerprint = digest(text)
                if not text or fingerprint in seen:
                    continue
                seen.add(fingerprint)
                payload = {k: v for k, v in question.items() if k not in ('block', 'group', 'order')}
                payload['text'] = text
                rows.append(BankQuestion(
                    teacher=job.teacher, exam_key=key, subject=job.subject, kind=str(question.get('type', ''))[:20],
                    text=text, digest=fingerprint, payload=json.loads(json.dumps(payload, default=str)),
                ))
        before = BankQuestion.objects.filter(teacher=job.teacher, exam_key=key).count()
        BankQuestion.objects.bulk_create(rows, ignore_conflicts=True)
        return BankQuestion.objects.filter(teacher=job.teacher, exam_key=key).count() - before
    except Exception:  # noqa: BLE001
        logger.exception("Savollarni bankka yozib bo'lmadi")
        return 0
