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


def broadcast_erase(lesson_id, sheet_index: int, stroke_ids: list, by: str, reason: str) -> None:
    _send(lesson_id, {
        'type': 'erase', 'sheet': sheet_index,
        'stroke_ids': stroke_ids, 'by': by, 'reason': reason,
    })


def broadcast_sheet(lesson_id, index: int) -> None:
    _send(lesson_id, {'type': 'sheet', 'index': index})


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


def broadcast_camera_request(lesson_id, student_id: str, name: str) -> None:
    """O'quvchi kamera so'radi — `broadcast_mic_request` bilan bir xil naqsh."""
    _send(lesson_id, {'type': 'camera_request', 'student_id': student_id, 'name': name})


def broadcast_camera_granted(lesson_id, student_id: str) -> None:
    _send(lesson_id, {'type': 'camera_granted', 'student_id': student_id})


def broadcast_camera_denied(lesson_id, student_id: str) -> None:
    _send(lesson_id, {'type': 'camera_denied', 'student_id': student_id})
