"""Monitoring views — yupqa qatlam. Faqat admin (`audit.view`, apps.analytics
dashboard bilan bir xil ruxsat) ko'radi."""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import RequirePerm

from . import selectors
from .serializers import ResourceSampleSerializer


class ResourceCurrentView(APIView):
    """Eng so'nggi yozilgan namuna — real vaqtda psutil ishga tushirish
    o'rniga (har so'rovda 1 soniya kutish shart bo'lmasin), oxirgi siklning
    natijasi qaytariladi.

    DIQQAT: hali birorta namuna yo'q bo'lsa `204 No Content` qaytadi — DRF
    `Response(None)`ni JSON `null` sifatida EMAS, bo'sh (Content-Type'siz)
    tanachalik javob sifatida render qiladi, shuning uchun 200+`null`
    o'rniga to'g'ri HTTP semantikasi (204) ishlatiladi."""

    permission_classes = [RequirePerm('audit.view')]

    def get(self, request):
        sample = selectors.latest_sample()
        if sample is None:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(ResourceSampleSerializer(sample).data)


class ResourceHistoryView(APIView):
    """`?hours=24` (standart) — vaqt qatori + shu davrdagi eng band lahza (peak)."""

    permission_classes = [RequirePerm('audit.view')]

    def get(self, request):
        try:
            hours = int(request.query_params.get('hours', 24))
        except ValueError:
            hours = 24
        hours = max(1, min(hours, 24 * 30))  # 1 soatdan 30 kungacha

        samples = selectors.history(hours=hours)
        peak = selectors.peak_sample(hours=hours)
        return Response({
            'hours': hours,
            'samples': ResourceSampleSerializer(samples, many=True).data,
            'peak': ResourceSampleSerializer(peak).data if peak else None,
        })
