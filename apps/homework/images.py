"""Uy vazifasi rasmlari: AI ga berishdan oldin qayta kodlash (JPEG, to'g'ri aylantirilgan, kichraytirilgan) va fayllar ichidan rasm olish.

- Telefon rasmi EXIF "aylantirish" belgisi bilan saqlanadi: uni hisobga olmasak AI rasmni yonboshdan ko'radi (`open_image`).
- iPhone `.heic` — yuklashda JPEG'ga o'tkaziladi (`heic_to_jpeg`), shunda o'qituvchi brauzerda ham ocha oladi.
- PDF va Word ichidagi rasmlar (qo'lyozma suratlari, skanerlangan sahifalar) AI ga beriladi (`pdf_images`, `docx_images`).
  Kichik rasmlar (logo, ikonka — `MIN_EMBEDDED_SIDE` dan kichik) olinmaydi.
"""
import io
import logging
import re
import zipfile
from pathlib import PurePosixPath

logger = logging.getLogger('apps')

IMAGE_SIDE = 2000          # rasm uzun tomoni (px): kattasi kichraytiriladi
IMAGE_SIDE_MANY = 1400     # rasm ko'p bo'lsa (MANY_IMAGES dan ortiq) har biri shunga kichraytiriladi — AI narxi oshib ketmasin
MANY_IMAGES = 5
MIN_EMBEDDED_SIDE = 300    # fayl ichidagi rasm: qisqa tomoni shundan kichik bo'lsa e'tiborsiz (logo, ikonka)
PER_PAGE = 2               # PDF'ning bitta sahifasidan eng ko'pi bilan shuncha rasm (eng kattalari)
MAX_COLLECTED = 40         # bitta topshiriqdan yig'iladigan rasmlarning mutlaq chegarasi (xotira)
MAX_PDF_PAGES = 60
HEIC_EXTENSIONS = {'.heic', '.heif'}
# Rasmning token narxi (OpenAI "high detail", gpt-4o-mini — eng qimmat hisob, shuning uchun boshqa modellar uchun ham xavfsiz taxmin):
# 2048 px kvadratga sig'diriladi, qisqa tomoni 768 dan oshsa 768 ga keltiriladi, so'ng 512 px bo'laklar soni x 5667 + 2833.
IMAGE_BASE_TOKENS, IMAGE_TILE_TOKENS, TILE = 2833, 5667, 512
_DOCX_MEDIA = re.compile(r'\.(png|jpe?g|webp|gif|bmp|tiff?)$', re.IGNORECASE)


class ImageError(Exception):
    """Rasmni o'qib bo'lmadi (buzuq fayl, qo'llab-quvvatlanmaydigan format)."""


def _register_heif() -> None:
    try:
        from pillow_heif import register_heif_opener
    except ImportError as exc:  # kutubxona o'rnatilmagan
        raise ImageError('HEIC qo\'llab-quvvatlanmaydi.') from exc
    register_heif_opener()


def open_image(data: bytes, *, heic: bool = False):
    """Baytlardan PIL rasmi; EXIF aylantirish qo'llangan. O'qib bo'lmasa `ImageError`."""
    from PIL import Image, ImageOps, UnidentifiedImageError

    try:
        if heic:
            _register_heif()
        image = Image.open(io.BytesIO(data))
        image.load()
        return ImageOps.exif_transpose(image)
    except ImageError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
        raise ImageError("Rasm faylini o'qib bo'lmadi.") from exc


def to_jpeg(image, side: int = IMAGE_SIDE, quality: int = 85) -> tuple:
    """(mime, bayt): RGB JPEG, uzun tomoni `side` dan oshmaydi."""
    from PIL import Image

    if image.mode not in ('RGB', 'L'):
        if 'A' in image.getbands():  # shaffof fon qora bo'lib ketmasin
            background = Image.new('RGB', image.size, 'white')
            background.paste(image.convert('RGBA'), mask=image.convert('RGBA').split()[-1])
            image = background
        else:
            image = image.convert('RGB')
    image = image.copy()
    image.thumbnail((side, side), Image.LANCZOS)
    buffer = io.BytesIO()
    image.convert('RGB').save(buffer, 'JPEG', quality=quality)
    return 'image/jpeg', buffer.getvalue()


def shrink(images: list, side: int = IMAGE_SIDE_MANY) -> list:
    """Allaqachon JPEG qilingan [(mime, bayt)] ni kichikroq o'lchamga tushiradi (rasm ko'p bo'lganda)."""
    out = []
    for mime, data in images:
        try:
            out.append(to_jpeg(open_image(data), side=side))
        except ImageError:
            out.append((mime, data))
    return out


def heic_to_jpeg(data: bytes) -> bytes:
    """iPhone rasmi (HEIC/HEIF) -> JPEG (yuklash uchun, sifat yuqori). O'qib bo'lmasa `ImageError`."""
    return to_jpeg(open_image(data, heic=True), side=6000, quality=90)[1]


def _usable(image) -> bool:
    return min(image.size) >= MIN_EMBEDDED_SIDE


def pdf_images(data: bytes, *, limit: int = MAX_COLLECTED) -> list:
    """PDF sahifalaridagi katta rasmlar (har sahifadan eng kattalari), sahifa tartibida: [(mime, bayt)]."""
    from pypdf import PdfReader

    found = []
    try:
        reader = PdfReader(io.BytesIO(data))
        for page in reader.pages[:MAX_PDF_PAGES]:
            if len(found) >= limit:
                break
            candidates = []
            for item in list(page.images)[:8]:
                try:
                    image = item.image
                except Exception:  # noqa: BLE001 — bitta rasm dekodlanmasa qolganlarini olamiz
                    continue
                if image is not None and _usable(image):
                    candidates.append(image)
            candidates.sort(key=lambda im: im.size[0] * im.size[1], reverse=True)
            for image in candidates[:PER_PAGE]:
                found.append(to_jpeg(image))
    except Exception as exc:  # noqa: BLE001 — g'alati PDF: topilganini beramiz
        logger.info("PDF ichidagi rasmlarni ajratib bo'lmadi: %s", exc)
    return found[:limit]


def docx_images(data: bytes, *, limit: int = MAX_COLLECTED) -> list:
    """Word (.docx) ichiga qo'yilgan rasmlar: [(mime, bayt)]."""
    found = []
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            names = sorted(
                (n for n in archive.namelist() if n.startswith('word/media/') and _DOCX_MEDIA.search(n)),
                key=lambda n: [int(p) if p.isdigit() else p for p in re.split(r'(\d+)', PurePosixPath(n).name)],
            )
            for name in names:
                if len(found) >= limit:
                    break
                if archive.getinfo(name).file_size > 30 * 1024 * 1024:
                    continue
                try:
                    image = open_image(archive.read(name))
                except ImageError:
                    continue
                if _usable(image):
                    found.append(to_jpeg(image))
    except (zipfile.BadZipFile, KeyError, OSError) as exc:
        logger.info("DOCX ichidagi rasmlarni ajratib bo'lmadi: %s", exc)
    return found


def estimate_tokens(size: tuple) -> int:
    """Rasm (eni, bo'yi px) AI so'rovida qancha token olishi (OpenAI hujjatidagi formula; 1536x1536 -> 25 501)."""
    import math

    width, height = size
    if max(width, height) > 2048:
        scale = 2048 / max(width, height)
        width, height = width * scale, height * scale
    if min(width, height) > 768:
        scale = 768 / min(width, height)
        width, height = width * scale, height * scale
    tiles = math.ceil(width / TILE) * math.ceil(height / TILE)
    return IMAGE_BASE_TOKENS + IMAGE_TILE_TOKENS * max(tiles, 1)


def image_tokens(images: list) -> int:
    """[(mime, bayt)] ning jami token narxi."""
    from PIL import Image

    total = 0
    for _mime, data in images:
        try:
            total += estimate_tokens(Image.open(io.BytesIO(data)).size)
        except Exception:  # noqa: BLE001 — o'lchamni bilib bo'lmasa o'rtacha sahifa narxi
            total += IMAGE_BASE_TOKENS + 4 * IMAGE_TILE_TOKENS
    return total


def fit_budget(images: list, budget: int) -> tuple:
    """Rasmlarni tartib bilan token byudjetiga sig'adiganini qoldiradi: (qolganlari, tashlanganlari soni). Birinchi rasm har doim qoladi.
    Birinchi sig'masdan keyingi hammasi tashlanadi (sahifalar tartibi buzilmasin)."""
    kept, used = [], 0
    for index, image in enumerate(images):
        cost = image_tokens([image])
        if kept and used + cost > budget:
            return kept, len(images) - index
        kept.append(image)
        used += cost
    return kept, 0
