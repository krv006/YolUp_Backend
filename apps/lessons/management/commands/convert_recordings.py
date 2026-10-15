"""Dars yozuvlarini iOS ochadigan formatga (MP4: H.264 + AAC) o'giradi.

    python manage.py convert_recordings [--limit 1] [--retry-failed]

Eski yozuvlar ham, yangilari ham shu buyruq bilan o'giriladi (eskisi oldin). Production'da `transcoder` xizmati uni
doimiy sikl bilan chaqiradi, bir vaqtda bitta yozuv. Asl WebM o'chirilmaydi.
"""
from django.core.management.base import BaseCommand

from apps.lessons import transcode


class Command(BaseCommand):
    help = "Dars yozuvlarini iOS ochadigan MP4 ga o'giradi (navbat bilan, bitta-bitta)."

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=1, help="Bir chaqiruvda ko'pi bilan nechta yozuv (standart 1)")
        parser.add_argument('--retry-failed', action='store_true', help='Avval xato bilan tugaganlarini ham qayta urinish')

    def handle(self, *args, **options):
        released = transcode.release_stale()
        if released:
            self.stdout.write(f'{released} ta qotib qolgan yozuv navbatga qaytarildi')
        for recording in transcode.next_pending(retry_failed=options['retry_failed'], limit=options['limit']):
            result = transcode.convert(recording.pk)
            self.stdout.write(f'{recording.pk}: {result}')
