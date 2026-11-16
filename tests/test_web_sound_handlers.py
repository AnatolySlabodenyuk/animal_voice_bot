import asyncio
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.methods import SendAudio
from aiogram.types import BufferedInputFile, Message

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

TEST_ENV = {
    "BOT_TOKEN": "123456:TEST_TOKEN_FOR_UNIT_TESTS_ONLY",
    "BOT_ADMIN_USER_ID": "1", "SEARCH_RESULT_COUNT": "5",
    "DATABASE_PATH": "/tmp/audio-hunter-unused-test.sqlite",
    "TOP_USER_REQUESTS_COUNT": "5", "FEEDBACK_MESSAGE": "test",
    "WEBAPP_URL": "https://example.test", "FREESOUND_API_KEY": "",
}
with patch.dict(os.environ, TEST_ENV):
    from handlers import user_handlers as handlers

from database.web_sound_cache import WebSoundCache
from keyboards.web_sound_kb import WebSoundCallback
from services.web_sound_search import SearchResults, SoundSearchError, WebSound


class WebSoundHandlerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.cache = WebSoundCache(str(Path(self.directory.name) / "test.sqlite"), 123456)
        await self.cache.initialize()
        self.storage = MemoryStorage()
        self.state = FSMContext(self.storage, StorageKey(bot_id=123456, chat_id=1, user_id=1))
        self.bot = SimpleNamespace(send_chat_action=AsyncMock(), edit_message_text=AsyncMock())
        self.message = MagicMock(spec=Message,
            text="лай собаки", from_user=SimpleNamespace(id=1, username="test"),
            bot=self.bot, chat=SimpleNamespace(id=1), answer=AsyncMock(),
            answer_rich=AsyncMock(return_value=SimpleNamespace(message_id=42)),
            answer_audio=AsyncMock(return_value=SimpleNamespace(audio=SimpleNamespace(file_id="new-id"))),
        )
        self.sound = WebSound(
            "freesound:42", "<Dog & bark>", "https://cdn.freesound.org/42.mp3",
            "Freesound", "https://freesound.org/people/recorder/sounds/42/",
            "recorder", "Attribution",
        )
        self.service = SimpleNamespace(
            search=AsyncMock(return_value=SearchResults([self.sound], [])),
            download=AsyncMock(return_value=b"ID3test"),
        )
        self.stats = patch.object(handlers, "increment_user_request_count", AsyncMock())
        self.stats.start()

    async def asyncTearDown(self):
        self.stats.stop()
        await self.storage.close()
        self.directory.cleanup()

    async def search(self):
        await self.state.set_state(handlers.SearchInNetState.waiting_for_key_word)
        await handlers.search_audio(self.message, self.state, self.service)

    async def test_catalog_pagination_and_playback_use_short_callbacks(self):
        category = next(iter(handlers.CATEGORY_TITLES))
        names = [f"{i:02d} " + "длинное название " * 6 for i in range(9)]
        self.message.edit_text = AsyncMock()
        callback = SimpleNamespace(
            from_user=self.message.from_user, message=self.message, answer=AsyncMock(),
        )
        with patch.object(handlers, "get_audio_file_name_from_table", AsyncMock(return_value=names)):
            await handlers.show_category(self.message, category, 0)
            blocks = self.message.edit_text.call_args.kwargs["rich_message"].blocks
            callback.data = blocks[-2].buttons[0].callback_data
            await handlers.navigate_category_page(callback)
            blocks = self.message.edit_text.call_args.kwargs["rich_message"].blocks
            callback.data = blocks[1].buttons[0].callback_data
            self.assertLessEqual(len(callback.data.encode()), 64)
            self.assertEqual(blocks[-1].buttons[0].callback_data, "menu:catalog")
            self.message.answer_photo = AsyncMock()
            with (
                patch.object(handlers, "get_audio_file_id_from_table", AsyncMock(return_value="audio-id")),
                patch.object(handlers, "get_image_file_id_from_table", AsyncMock(return_value="photo-id")),
            ):
                await handlers.play_catalog_sound(callback)
            self.message.answer_audio.assert_awaited_once_with(audio="audio-id", reply_markup=None)
            self.message.answer_rich.assert_not_awaited()
            photo = self.message.answer_photo.call_args.kwargs
            self.assertEqual(photo["photo"], "photo-id")
            other, home = photo["reply_markup"].inline_keyboard[0]
            self.assertEqual(other.text, "Другой звук")
            self.assertEqual(home.text, "Главное меню")
            callback.data = other.callback_data
            await handlers.navigate_from_photo(callback, self.state)
            returned = self.message.answer_rich.call_args.kwargs["rich_message"]
            self.assertEqual(returned.blocks, blocks)
            self.assertEqual(returned.blocks[-1].buttons[0].text, "Выбрать категорию")
            self.message.chat.type = "private"
            callback.data = home.callback_data
            await handlers.navigate_from_photo(callback, self.state)
            main = self.message.answer_rich.call_args.kwargs["rich_message"]
            self.assertEqual(main.blocks, handlers.build_rich_menu(handlers.home_screen(self.message)).blocks)

    async def test_search_sends_results_in_a_new_message(self):
        await handlers.process_search_in_web_button(self.message, self.state)
        await self.search()
        self.assertEqual(self.message.answer_rich.await_count, 2)
        self.bot.edit_message_text.assert_not_awaited()
        result = self.message.answer_rich.call_args.kwargs["rich_message"]
        self.assertEqual(result.blocks[-1].buttons[0].callback_data, "menu:search")

    async def select(self, token=None, index=0, state=None):
        data = await self.state.get_data()
        callback = SimpleNamespace(
            from_user=self.message.from_user, message=self.message, answer=AsyncMock(),
        )
        await handlers.send_web_sound(
            callback, WebSoundCallback(token=token or data.get("web_search_token", "old"), index=index),
            state or self.state, self.service, self.cache,
        )
        return callback

    async def test_search_lists_buttons_and_downloads_only_selected_result(self):
        await self.search()
        self.message.answer_audio.assert_not_awaited()
        self.service.download.assert_not_awaited()
        self.assertIsNone(await self.state.get_state())
        rich = self.message.answer_rich.call_args.kwargs["rich_message"]
        callback_data = WebSoundCallback.unpack(rich.blocks[1].buttons[0].callback_data)
        self.assertEqual(callback_data.index, 0)
        await self.select(callback_data.token)
        payload = self.message.answer_audio.call_args.kwargs
        self.assertIsInstance(payload["audio"], BufferedInputFile)
        self.assertNotIn("caption", payload)
        back, home = payload["reply_markup"].inline_keyboard[0]
        self.assertEqual((back.text, home.text), ("Назад", "Главное меню"))
        self.assertEqual(home.callback_data, "photo-home")
        callback = SimpleNamespace(data=back.callback_data, message=self.message, answer=AsyncMock())
        await handlers.return_to_web_results(callback, self.state)
        results = self.message.answer_rich.call_args.kwargs["rich_message"]
        self.assertIn(self.sound.page_url, results.blocks[0].text)
        self.assertEqual(results.blocks[1].buttons[0].callback_data, callback_data.pack())
        self.assertEqual(await self.cache.get("freesound:42"), "new-id")

    async def test_cached_file_is_sent_without_download(self):
        await self.search()
        await self.cache.put("freesound:42", "cached-id")
        await self.select()
        self.assertEqual(self.message.answer_audio.call_args.kwargs["audio"], "cached-id")
        self.assertNotIn("caption", self.message.answer_audio.call_args.kwargs)
        self.assertEqual(len(self.message.answer_audio.call_args.kwargs["reply_markup"].inline_keyboard[0]), 2)
        self.service.download.assert_not_awaited()

    async def test_invalid_cached_id_is_replaced(self):
        await self.search()
        await self.cache.put("freesound:42", "invalid-id")
        self.message.answer_audio.side_effect = [
            TelegramBadRequest(method=SendAudio(chat_id=1, audio="invalid-id"), message="wrong file identifier"),
            SimpleNamespace(audio=SimpleNamespace(file_id="replaced-id")),
        ]
        await self.select()
        self.assertEqual(await self.cache.get("freesound:42"), "replaced-id")
        self.assertIsInstance(self.message.answer_audio.call_args.kwargs["audio"], BufferedInputFile)

    async def test_empty_and_unavailable_searches_end_waiting_state(self):
        for failed in ([], ["Zvukogram"]):
            with self.subTest(failed=failed):
                self.service.search.return_value = SearchResults([], failed)
                await self.search()
                self.assertIsNone(await self.state.get_state())
                self.assertNotIn("web_search_results", await self.state.get_data())
        rich = self.message.answer_rich.call_args.kwargs["rich_message"]
        self.assertIn("недоступ", rich.blocks[0].text.lower())

    async def test_non_text_and_blank_input_keep_waiting_for_valid_query(self):
        for text in (None, "   "):
            self.message.text = text
            await self.search()
            self.assertEqual(await self.state.get_state(), handlers.SearchInNetState.waiting_for_key_word.state)
        self.service.search.assert_not_awaited()

    async def test_old_buttons_and_another_users_buttons_cannot_send_audio(self):
        await self.search()
        await self.select(token="outdated")
        other_state = FSMContext(self.storage, StorageKey(bot_id=123456, chat_id=1, user_id=2))
        await self.select(state=other_state)
        await self.select(index=-1)
        await self.select(index=100)
        self.message.answer_audio.assert_not_awaited()

    async def test_expired_results_cannot_send_audio(self):
        await self.search()
        await self.state.update_data(web_search_expires=time.time() - 1)
        await self.select()
        self.message.answer_audio.assert_not_awaited()

    async def test_download_failure_is_reported_and_buttons_remain_usable(self):
        await self.search()
        self.service.download.side_effect = SoundSearchError("Не удалось скачать звук.")
        await self.select()
        self.assertIn("скачать", self.message.answer.call_args.args[0])
        self.assertIsNone(await self.cache.get("freesound:42"))
        self.service.download.side_effect = None
        await self.select()
        self.assertEqual(await self.cache.get("freesound:42"), "new-id")

    async def test_new_search_invalidates_old_results(self):
        await self.search()
        old_token = (await self.state.get_data())["web_search_token"]
        await self.search()
        await self.select(token=old_token)
        self.message.answer_audio.assert_not_awaited()

    async def test_in_flight_search_cannot_overwrite_new_search_state(self):
        started = asyncio.Event()
        release = asyncio.Event()

        async def slow_search(query):
            started.set()
            await release.wait()
            return SearchResults([self.sound], [])

        self.service.search.side_effect = slow_search
        task = asyncio.create_task(self.search())
        await started.wait()
        await handlers.process_search_in_web_button(self.message, self.state)
        release.set()
        await task
        self.assertEqual(await self.state.get_state(), handlers.SearchInNetState.waiting_for_key_word.state)
        self.assertNotIn("web_search_results", await self.state.get_data())
        self.message.answer_rich.assert_awaited_once()

    async def test_search_waiting_for_statistics_cannot_overwrite_new_search(self):
        started = asyncio.Event()
        release = asyncio.Event()

        async def slow_statistics(*args):
            if not started.is_set():
                started.set()
                await release.wait()

        with patch.object(handlers, "increment_user_request_count", side_effect=slow_statistics):
            task = asyncio.create_task(self.search())
            await started.wait()
            await handlers.process_search_in_web_button(self.message, self.state)
            release.set()
            await task
        self.assertEqual(await self.state.get_state(), handlers.SearchInNetState.waiting_for_key_word.state)
        self.assertNotIn("web_search_results", await self.state.get_data())
