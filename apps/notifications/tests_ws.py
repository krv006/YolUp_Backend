"""`/ws/notifications/` autentifikatsiya — `accept()`dan keyin `close(4401)`
kerakligini tekshiradi (2026-09-30 production'da topilgan haqiqiy xato:
`close()` `accept()`dan OLDIN chaqirilsa, ASGI server ulanishni butunlay
rad etadi — HTTP 403 — brauzer maxsus kodni hech qachon ko'rmaydi, frontend
"4401 kelsa tokenni yangila" mantig'ini ishga tushira olmaydi)."""
from channels.testing import WebsocketCommunicator
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework.test import APITestCase

from apps.accounts.models import User
from root.asgi import application


class NotificationWebsocketAuthTests(APITestCase):
    async def test_valid_token_is_accepted(self):
        from channels.db import database_sync_to_async

        user = await database_sync_to_async(User.objects.create_user)(
            username='ws_notif_ok', password='x', role=User.Role.STUDENT,
        )
        token = str(AccessToken.for_user(user))
        comm = WebsocketCommunicator(application, f'/ws/notifications/?token={token}')
        connected, _ = await comm.connect()
        self.assertTrue(connected)
        await comm.disconnect()

    async def test_missing_token_accepted_then_closed_with_4401(self):
        comm = WebsocketCommunicator(application, '/ws/notifications/')
        connected, _ = await comm.connect()
        self.assertTrue(connected)
        closed = await comm.receive_output(timeout=3)
        self.assertEqual(closed['type'], 'websocket.close')
        self.assertEqual(closed['code'], 4401)
        await comm.disconnect()

    async def test_invalid_token_accepted_then_closed_with_4401(self):
        comm = WebsocketCommunicator(application, '/ws/notifications/?token=garbage')
        connected, _ = await comm.connect()
        self.assertTrue(connected)
        closed = await comm.receive_output(timeout=3)
        self.assertEqual(closed['type'], 'websocket.close')
        self.assertEqual(closed['code'], 4401)
        await comm.disconnect()
