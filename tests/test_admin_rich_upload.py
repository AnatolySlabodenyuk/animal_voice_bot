import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message

from handlers import admin_handlers as admin


class AdminUploadMenuTests(unittest.IsolatedAsyncioTestCase):
    async def test_stats_and_feedback_keep_admin_menu_and_check_permissions(self):
        menu = MagicMock(spec=Message, message_id=42, edit_text=AsyncMock())
        callback = SimpleNamespace(
            from_user=SimpleNamespace(id=2), message=menu, answer=AsyncMock(), data=admin.ADMIN_STATS,
            bot=SimpleNamespace(send_message=AsyncMock()),
        )
        with (
            patch.object(admin, "ADMIN_USER_ID", "1"),
            patch.object(admin, "get_user_stats_page", AsyncMock(return_value=(9, 1, 0, 2, [(1, "Alice", 5, "2026-11-15 12:00:00")]))) as stats,
            patch.object(admin, "get_all_users", AsyncMock(return_value=[(3, "Bob")])) as users,
        ):
            await admin.process_stats_menu(callback)
            await admin.process_send_feedback_menu(callback)
            stats.assert_not_awaited()
            users.assert_not_awaited()
            menu.edit_text.assert_not_awaited()
            callback.from_user.id = 1
            await admin.process_stats_menu(callback)
            self.assertIn("Alice", menu.edit_text.call_args.kwargs["rich_message"].blocks[0].text)
            rendered = menu.edit_text.call_args.kwargs["rich_message"]
            self.assertIn("15.11.2026 15:00", rendered.blocks[0].text)
            self.assertEqual(rendered.blocks[2].buttons[0].callback_data, "admin:stats:active:1")
            callback.data = "admin:stats:requests:1"
            await admin.process_stats_menu(callback)
            stats.assert_awaited_with("requests", 1)
            await admin.process_send_feedback_menu(callback)
            callback.bot.send_message.assert_awaited_once_with(chat_id=3, text=admin.feedback_message)
            self.assertEqual(menu.edit_text.call_args.kwargs["rich_message"].blocks[-1].buttons[0].callback_data, admin.ADMIN_MENU)

    async def test_audio_and_photo_workflows_keep_original_menu(self):
        for kind in ("audio", "image"):
            with self.subTest(kind=kind), patch.object(admin, "ADMIN_USER_ID", "1"):
                storage = MemoryStorage()
                state = FSMContext(storage, StorageKey(bot_id=1, chat_id=1, user_id=1))
                actor = SimpleNamespace(id=1)
                menu = MagicMock(spec=Message, message_id=42, edit_text=AsyncMock())
                callback = SimpleNamespace(
                    from_user=actor, message=menu, answer=AsyncMock(),
                    data=admin.ADMIN_AUDIO if kind == "audio" else admin.ADMIN_IMAGE,
                )
                await admin.process_upload_menu(callback, state)
                outgoing = AsyncMock()
                upload = SimpleNamespace(
                    from_user=actor, text="Тестовый звук", chat=SimpleNamespace(id=1),
                    bot=SimpleNamespace(edit_message_text=outgoing),
                    audio=SimpleNamespace(file_id="file"),
                    photo=[SimpleNamespace(file_id="file")],
                )
                if kind == "audio":
                    await admin.process_upload_audio_new(upload, state)
                    await admin.audio_name_chosen(upload, state)
                    callback.data = admin.ADMIN_AUDIO_CATEGORY + "animals"
                else:
                    await admin.process_upload_image_new(upload, state)
                    await admin.image_name_chosen(upload, state)
                    callback.data = admin.ADMIN_IMAGE_CATEGORY + "animals"
                self.assertEqual([c.kwargs["message_id"] for c in outgoing.await_args_list], [42, 42])
                with patch.object(admin, f"add_{kind}_to_table", new_callable=AsyncMock) as save:
                    callback.message = MagicMock(spec=Message, message_id=41)
                    await admin.save_upload(callback, state, kind)
                    save.assert_not_awaited()
                    callback.message = menu
                    await admin.save_upload(callback, state, kind)
                    save.assert_awaited_once()
                self.assertEqual(menu.edit_text.await_count, 2)
                self.assertIsNone(await state.get_state())
                await storage.close()
