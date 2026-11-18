"""AI tekshiruvi sarfi: nechta topshiriq baholandi, necha token ketdi, o'rtacha va eng qimmatlari.

    python manage.py homework_ai_usage [--days 30] [--price-in 0.15] [--price-out 0.60]

Narx (USD, 1 million token uchun) HOZIRGI OpenAI tarifidan olinadi — bu yerda qotirilmagan, `--price-in/--price-out` yoki
`OPENAI_PRICE_IN_PER_M` / `OPENAI_PRICE_OUT_PER_M` muhit o'zgaruvchilari bilan beriladi; berilmasa faqat tokenlar chiqadi.
Sarf `Submission.ai_result['usage']` da saqlanadi (shu o'zgarishdan keyingi tekshiruvlar uchun; eskilarida yo'q).
"""
import os
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.homework.models import Submission


def _price(option, env):
    raw = option if option is not None else os.getenv(env, '')
    try:
        return float(raw) if raw not in (None, '') else None
    except ValueError:
        return None


class Command(BaseCommand):
    help = "Uy vazifasi AI tekshiruvi token sarfi (va narxi, agar tarif berilsa)."

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=30)
        parser.add_argument('--price-in', type=float, default=None, help='USD / 1M kirish tokeni')
        parser.add_argument('--price-out', type=float, default=None, help='USD / 1M chiqish tokeni')
        parser.add_argument('--top', type=int, default=5)

    def handle(self, *args, **options):
        since = timezone.now() - timedelta(days=options['days'])
        rows = []
        total = Submission.objects.filter(created_at__gte=since).count()
        for submission in Submission.objects.filter(created_at__gte=since).exclude(ai_result__isnull=True).iterator():
            usage = submission.ai_result.get('usage') if isinstance(submission.ai_result, dict) else None
            if isinstance(usage, dict) and usage.get('total_tokens'):
                rows.append((submission, usage))
        self.stdout.write(f"Oxirgi {options['days']} kun: {total} ta topshiriq, shundan sarfi yozilgani: {len(rows)} ta.")
        if not rows:
            self.stdout.write("Sarf hali yozilmagan (yozish faqat shu o'zgarishdan keyingi tekshiruvlarda boshlanadi).")
            return
        prompt = sum(u.get('prompt_tokens', 0) for _s, u in rows)
        completion = sum(u.get('completion_tokens', 0) for _s, u in rows)
        total_tokens = sum(u.get('total_tokens', 0) for _s, u in rows)
        calls = sum(u.get('calls', 0) for _s, u in rows)
        n = len(rows)
        self.stdout.write(
            f'Jami: {total_tokens:,} token (kirish {prompt:,}, chiqish {completion:,}), {calls} ta AI chaqiruvi '
            f'(qayta urinishlar bilan).')
        self.stdout.write(f'Bitta topshiriqqa o\'rtacha: {total_tokens // n:,} token, {calls / n:.2f} chaqiruv.')
        price_in, price_out = _price(options['price_in'], 'OPENAI_PRICE_IN_PER_M'), _price(options['price_out'], 'OPENAI_PRICE_OUT_PER_M')
        if price_in is not None and price_out is not None and (prompt or completion):
            cost = prompt / 1e6 * price_in + completion / 1e6 * price_out
            self.stdout.write(f'Taxminiy narx: ${cost:.4f} jami, ${cost / n:.5f} bitta topshiriqqa (tarif: kirish ${price_in}/1M, chiqish ${price_out}/1M).')
        else:
            self.stdout.write("Narxni ko'rish uchun tarifni bering: --price-in <USD/1M> --price-out <USD/1M>.")
        self.stdout.write('Eng ko\'p sarflaganlar:')
        for submission, usage in sorted(rows, key=lambda r: r[1].get('total_tokens', 0), reverse=True)[:options['top']]:
            kind = (submission.original_name.rsplit('.', 1)[-1].lower() if submission.original_name else 'matn')
            self.stdout.write(f"  {usage['total_tokens']:>8,} token · {submission.created_at:%Y-%m-%d} · {kind} · {submission.id}")
