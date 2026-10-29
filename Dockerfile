FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# ffmpeg — brauzerdan (chunked upload) kelgan video+audio yozuvlarini
# birlashtirish uchun (-c copy, qayta kodlashsiz). mkvtoolnix (mkvmerge) —
# tarmoq uzilib-ulanganda ko'p segmentga bo'lingan WebM fayllarni QAYTA
# KODLAMASDAN (CPU tejash rejasiga mos) to'g'irlash uchun. gettext — `locale/`
# ostidagi `.po` tarjima fayllarini (`manage.py compilemessages`) `.mo`ga
# aylantirish uchun (2026-09-06, ko'p tillik qo'llab-quvvatlash).
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg mkvtoolnix gettext \
    && rm -rf /var/lib/apt/lists/*

# constraints.txt — har buildda bir xil versiyalar (qotirilmagan `>=` tufayli kutilmagan yangilanish bo'lmasin)
COPY requirements.txt constraints.txt ./
RUN pip install --no-cache-dir -r requirements.txt -c constraints.txt

COPY . .

# `.mo` fayllar ataylab gitignore qilingan (har doim `.po`dan qayta
# hosil bo'ladi) — shuning uchun build vaqtida shu yerda kompilyatsiya
# qilinadi. `DJANGO_ENV` bu bosqichda hali yo'q (faqat runtime'da
# beriladi) — standart `dev` sozlamalari ishlatiladi, bu komandaga
# yetarli (DB/sekretga muhtoj emas, faqat fayl tizimi bilan ishlaydi).
RUN python manage.py compilemessages

EXPOSE 8000

CMD ["gunicorn", "root.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60"]
