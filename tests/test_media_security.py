import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import sound_game as game


class MediaSecurityTests(unittest.IsolatedAsyncioTestCase):
    async def test_question_does_not_expose_bot_token(self):
        with patch.object(game, 'get_random_sound', AsyncMock(return_value=('Cat', 'animals', 'audio_id'))), patch.object(game, 'get_random_names', AsyncMock(return_value=['Dog', 'Bird'])), patch.object(game, 'get_image_file_id_from_table', AsyncMock(return_value='image_id')), patch.object(game.bot, 'get_file', AsyncMock(return_value=SimpleNamespace(file_path='photos/example.jpg'))):
            data = await game.get_question()
        self.assertFalse(game.config.tg_bot.token in str(data), 'API response exposes the bot token')
        self.assertTrue(data['voice_url'].startswith('/api/media/'))
        self.assertTrue(all(item['image_url'].startswith('/api/media/') for item in data['options']))

    async def test_media_returns_content_without_redirect(self):
        async def download(path, destination):
            destination.write(b'fake-audio-content')
        key = game.register_media('voice/sample.ogg')
        with patch.object(game.bot, 'download_file', side_effect=download):
            response = await game.get_media(key)
        self.assertEqual(response.body, b'fake-audio-content')
        self.assertNotIn('location', response.headers)
        self.assertEqual(response.media_type, 'audio/ogg')

    async def test_unknown_media_is_rejected(self):
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as error:
            await game.get_media('unknown-key')
        self.assertEqual(error.exception.status_code, 404)

    async def test_extensionless_photo_has_image_content_type(self):
        async def download(path, destination):
            destination.write(b'\xff\xd8\xffexample')
        key = game.register_media('photos/file')
        with patch.object(game.bot, 'download_file', side_effect=download):
            response = await game.get_media(key)
        self.assertEqual(response.media_type, 'image/jpeg')


if __name__ == '__main__':
    unittest.main()
