"""Doska real-time broadcast — polling o'rniga WebSocket.

Service qatlami (add_stroke / erase_strokes / add_sheet) har o'zgarishni
`board_<lesson_id>` guruhiga tarqatadi — REST orqali kelganmi, WS orqalimi,
farqi yo'q: hamma ulangan ishtirokchi bir zumda ko'radi.
"""
from asgiref.sync import async_to_sync


def group_name(lesson_id) -> str:
    return f'board_{lesson_id}'


def _send(lesson_id, event: dict) -> None:
    from channels.layers import get_channel_layer

    layer = get_channel_layer()
    if layer is None:
        return
    async_to_sync(layer.group_send)(group_name(lesson_id), {
        'type': 'board.event',
        'event': event,
    })


def broadcast_stroke(lesson_id, sheet_index: int, stroke: dict) -> None:
    _send(lesson_id, {'type': 'stroke', 'sheet': sheet_index, 'stroke': stroke})


def broadcast_update(lesson_id, sheet_index: int, stroke: dict) -> None:
    """Mavjud element o'zgardi (matn tahrirlandi, ko'chirildi, rangi/o'lchami o'zgardi) — mijoz `id` bo'yicha to'liq
    elementni almashtiradi."""
    _send(lesson_id, {'type': 'stroke_updated', 'sheet': sheet_index, 'stroke': stroke})


def broadcast_erase(lesson_id, sheet_index: int, stroke_ids: list, by: str, reason: str) -> None:
    _send(lesson_id, {
        'type': 'erase', 'sheet': sheet_index,
        'stroke_ids': stroke_ids, 'by': by, 'reason': reason,
    })


def broadcast_sheet(lesson_id, index: int, title: str = '') -> None:
    _send(lesson_id, {'type': 'sheet', 'index': index, 'title': title})


def broadcast_sheet_renamed(lesson_id, index: int, title: str) -> None:
    _send(lesson_id, {'type': 'sheet_renamed', 'index': index, 'title': title})


def broadcast_focus(lesson_id, student_id: str, name: str, kind: str) -> None:
    """O'quvchi dars oynasidan chiqdi/qaytdi — o'qituvchiga darhol ko'rinishi
    uchun (frontend faqat is_teacher=true bo'lganda ko'rsatadi)."""
    _send(lesson_id, {'type': 'focus', 'student_id': student_id, 'name': name, 'kind': kind})


def broadcast_board_granted(lesson_id, student_id: str) -> None:
    """O'qituvchi doskaga chizish ruxsatini berdi — shu o'quvchining o'zi
    darhol (sahifani yangilamasdan) chiza olishini bilishi uchun."""
    _send(lesson_id, {'type': 'board_granted', 'student_id': student_id})


def broadcast_board_revoked(lesson_id, student_id: str) -> None:
    """O'qituvchi doskaga chizish ruxsatini qaytarib oldi — o'quvchi chizish asboblarini o'chirishi uchun."""
    _send(lesson_id, {'type': 'board_revoked', 'student_id': student_id})


def broadcast_mic_request(lesson_id, student_id: str, name: str) -> None:
    """O'quvchi mikrofon so'radi — o'qituvchiga darhol ko'rinishi uchun
    (frontend faqat is_teacher=true bo'lganda "qo'l ko'tarildi" belgisini
    ko'rsatadi)."""
    _send(lesson_id, {'type': 'mic_request', 'student_id': student_id, 'name': name})


def broadcast_mic_granted(lesson_id, student_id: str) -> None:
    """O'qituvchi mikrofonga ruxsat berdi — hammaga tarqatiladi: shu
    o'quvchining o'zi (mikrofon tugmasini yoqish uchun) va o'qituvchi
    (kutayotgan so'rovlar ro'yxatidan olib tashlash uchun) o'zi filtrlaydi."""
    _send(lesson_id, {'type': 'mic_granted', 'student_id': student_id})


def broadcast_mic_denied(lesson_id, student_id: str) -> None:
    """O'qituvchi so'rovni rad etdi — o'quvchining o'zi "so'rash" tugmasini
    qayta yoqishi, o'qituvchi esa kutish ro'yxatidan olib tashlashi uchun."""
    _send(lesson_id, {'type': 'mic_denied', 'student_id': student_id})


def broadcast_mic_revoked(lesson_id, student_id: str) -> None:
    """O'quvchining mikrofon RUXSATI olindi (hammani ovozsiz qilish, o'quvchining o'zi o'chirishi yoki ochiq rejim o'chirilishi) —
    o'quvchi interfeysi "So'rash" holatiga qaytadi, o'qituvchi paneli yangilanadi."""
    _send(lesson_id, {'type': 'mic_revoked', 'student_id': student_id})


def broadcast_camera_revoked(lesson_id, student_id: str) -> None:
    _send(lesson_id, {'type': 'camera_revoked', 'student_id': student_id})


def broadcast_media_mode(lesson_id, open_mic: bool, open_camera: bool) -> None:
    """"Hammaga mikrofon/kamera ochiq" almashtirgichlari o'zgardi."""
    _send(lesson_id, {'type': 'media_mode', 'open_mic': open_mic, 'open_camera': open_camera})


def broadcast_current_sheet(lesson_id, index: int) -> None:
    """O'qituvchi boshqa sahifaga o'tdi — mobil mijoz doska kartasida "Doska · N-sahifa" ni yangilaydi."""
    _send(lesson_id, {'type': 'current_sheet', 'sheet': index})


def broadcast_mic_request_cancelled(lesson_id, student_id: str) -> None:
    """O'quvchi o'z so'rovini bekor qildi — o'qituvchi kutish ro'yxatidan olib tashlaydi."""
    _send(lesson_id, {'type': 'mic_request_cancelled', 'student_id': student_id})


def broadcast_camera_request_cancelled(lesson_id, student_id: str) -> None:
    _send(lesson_id, {'type': 'camera_request_cancelled', 'student_id': student_id})


def broadcast_camera_request(lesson_id, student_id: str, name: str) -> None:
    """O'quvchi kamera so'radi — `broadcast_mic_request` bilan bir xil naqsh."""
    _send(lesson_id, {'type': 'camera_request', 'student_id': student_id, 'name': name})


def broadcast_camera_granted(lesson_id, student_id: str) -> None:
    _send(lesson_id, {'type': 'camera_granted', 'student_id': student_id})


def broadcast_camera_denied(lesson_id, student_id: str) -> None:
    _send(lesson_id, {'type': 'camera_denied', 'student_id': student_id})
