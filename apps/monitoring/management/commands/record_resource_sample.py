"""Backend konteynerining CPU/RAM holatini o'lchab, `ResourceSample`ga yozadi.

    python manage.py record_resource_sample

Docker socket ATAYLAB ulanmagan (xavfsizlik sababli admin bilan kelishilgan)
— shuning uchun bu buyruq FAQAT o'zi ishga tushirilgan konteynerning holatini
ko'ra oladi. docker-compose.prod.yml'da `cron` konteynerida EMAS, `backend`
konteynerining o'z `command`'i ichida background sikl sifatida ishga
tushiriladi — aks holda deyarli bo'sh turadigan `cron` konteynerining
statistikasi yozilib, backend'ning haqiqiy yukini aks ettirmas edi.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.monitoring import services


class Command(BaseCommand):
    help = "Backend konteynerining joriy CPU/RAM holatini yozib qo'yadi (davriy monitoring uchun)."

    def handle(self, *args, **options):
        sample = services.record_sample()
        local_time = timezone.localtime(sample.created_at)
        self.stdout.write(self.style.SUCCESS(
            f'CPU {sample.cpu_percent}% · RAM {sample.memory_percent}% ({local_time:%H:%M:%S})'
        ))
