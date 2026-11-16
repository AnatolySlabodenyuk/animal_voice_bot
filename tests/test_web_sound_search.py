import asyncio
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

import aiohttp
from aiohttp import web

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from database.web_sound_cache import WebSoundCache
from services.web_sound_search import SoundSearchError, WebSound, WebSoundSearch


class WebSoundSearchTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.requests = []
        self.html = '''
            <div class="onetrack accordion" data-track="/audio/dog.mp3">
                <div class="waveTitle">Лай &amp; собака</div>
            </div>
            <div class="onetrack accordion" data-track="https://example.test/cat.mp3">
                <div class="waveTitle">Кошка</div>
            </div>
            <div class="onetrack accordion" data-track="/broken.mp3"></div>
        '''
        self.status = 200
        self.freesound_status = 200
        self.api_data = {"count": 1, "next": None, "previous": None, "results": [{
            "id": 42, "name": "Dog bark", "username": "recorder",
            "license": "Attribution", "url": "https://freesound.org/people/recorder/sounds/42/",
            "previews": {"preview-hq-mp3": "https://cdn.freesound.org/previews/42.mp3"},
        }]}
        app = web.Application()
        app.router.add_get("/", self.zvukogram)
        app.router.add_get("/api/", self.freesound)
        app.router.add_get("/audio/dog.mp3", self.audio)
        app.router.add_get("/large.mp3", self.large_audio)
        app.router.add_get("/not-audio.mp3", self.not_audio)
        self.runner = web.AppRunner(app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, "127.0.0.1", 0)
        await site.start()
        port = site._server.sockets[0].getsockname()[1]
        self.base = f"http://127.0.0.1:{port}/"
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=1))
        self.service = WebSoundSearch(self.session, result_count=5)
        self.service.ZVUKOGRAM_URL = self.base
        self.service.FREESOUND_URL = self.base + "api/"

    async def asyncTearDown(self):
        await self.session.close()
        await self.runner.cleanup()

    async def zvukogram(self, request):
        self.requests.append(("zvukogram", dict(request.query), request.headers.get("Authorization")))
        return web.Response(text=self.html, status=self.status, content_type="text/html")

    async def freesound(self, request):
        self.requests.append(("freesound", dict(request.query), request.headers.get("Authorization")))
        return web.json_response(self.api_data, status=self.freesound_status)

    async def audio(self, request):
        return web.Response(body=b"ID3test-audio", content_type="audio/mpeg")

    async def large_audio(self, request):
        response = web.StreamResponse(headers={"Content-Type": "audio/mpeg"})
        await response.prepare(request)
        await response.write(b"x" * 100)
        await response.write_eof()
        return response

    async def not_audio(self, request):
        return web.Response(text="<html>blocked</html>", content_type="text/html")

    async def test_query_special_characters_are_not_url_parameters(self):
        result = await self.service.search("лай & дождь #1")
        self.assertEqual(self.requests[0][1], {"r": "search", "s": "лай & дождь #1"})
        self.assertEqual([item.title for item in result.sounds], ["Лай & собака", "Кошка"])
        self.assertEqual(result.sounds[0].audio_url, self.base + "audio/dog.mp3")
        self.assertEqual(result.sounds[1].audio_url, "https://example.test/cat.mp3")

    async def test_freesound_translation_metadata_and_no_token_leak(self):
        self.service.freesound_api_key = "test-only-key"
        result = await self.service.search("ЛАЙ   СОБАКИ")
        api_request = next(request for request in self.requests if request[0] == "freesound")
        self.assertEqual(api_request[1]["query"], "dog bark")
        self.assertEqual(api_request[2], "Token test-only-key")
        self.assertIsNone(next(request for request in self.requests if request[0] == "zvukogram")[2])
        sound = next(sound for sound in result.sounds if sound.source == "Freesound")
        self.assertEqual(sound.author, "recorder")
        self.assertEqual(sound.license, "Attribution")
        self.assertEqual(sound.key, "freesound:42")

    async def test_both_sources_are_represented_with_global_limit(self):
        self.service.freesound_api_key = "test-only-key"
        self.service.result_count = 2
        result = await self.service.search("dog")
        self.assertEqual(len(result.sounds), 2)
        self.assertEqual({sound.source for sound in result.sounds}, {"Zvukogram", "Freesound"})

    async def test_freesound_only_does_not_request_zvukogram(self):
        self.service.source = "freesound"
        self.service.freesound_api_key = "test-only-key"
        result = await self.service.search("лай собаки")
        self.assertEqual([sound.source for sound in result.sounds], ["Freesound"])
        self.assertEqual([request[0] for request in self.requests], ["freesound"])

    async def test_zvukogram_only_does_not_request_freesound_even_with_key(self):
        self.service.source = "zvukogram"
        self.service.freesound_api_key = "test-only-key"
        result = await self.service.search("dog")
        self.assertEqual({sound.source for sound in result.sounds}, {"Zvukogram"})
        self.assertEqual([request[0] for request in self.requests], ["zvukogram"])

    async def test_freesound_only_without_key_reports_failure_without_fallback(self):
        self.service.source = "freesound"
        result = await self.service.search("dog")
        self.assertEqual(result.sounds, [])
        self.assertEqual(result.failed_sources, ["Freesound"])
        self.assertEqual(self.requests, [])

    async def test_failing_source_does_not_discard_working_source(self):
        self.service.freesound_api_key = "test-only-key"
        self.status = 503
        result = await self.service.search("dog")
        self.assertEqual([sound.key for sound in result.sounds], ["freesound:42"])
        self.assertEqual(result.failed_sources, ["Zvukogram"])

    async def test_all_sources_failing_is_distinct_from_empty_results(self):
        self.status = 503
        result = await self.service.search("dog")
        self.assertEqual(result.sounds, [])
        self.assertEqual(result.failed_sources, ["Zvukogram"])
        self.status = 200
        self.html = "<html>Нет результатов</html>"
        result = await self.service.search("dog")
        self.assertEqual(result.sounds, [])
        self.assertEqual(result.failed_sources, [])

    async def test_missing_track_fields_do_not_crash_search(self):
        self.html = '<div class="onetrack accordion"></div>'
        result = await self.service.search("dog")
        self.assertEqual(result.sounds, [])
        self.assertEqual(result.failed_sources, ["Zvukogram"])

    async def test_download_audio_and_reject_html(self):
        sound = WebSound("test:1", "Собака", self.base + "audio/dog.mp3", "Zvukogram", self.base)
        self.assertEqual(await self.service.download(sound), b"ID3test-audio")
        sound.audio_url = self.base + "not-audio.mp3"
        with self.assertRaises(SoundSearchError):
            await self.service.download(sound)

    async def test_download_size_limit_applies_without_content_length(self):
        self.service.MAX_AUDIO_BYTES = 50
        sound = WebSound("test:1", "Большой файл", self.base + "large.mp3", "Zvukogram", self.base)
        with self.assertRaises(SoundSearchError):
            await self.service.download(sound)

    async def test_timeout_becomes_source_failure(self):
        self.service.session = MagicMock()
        self.service.session.get.side_effect = asyncio.TimeoutError
        result = await self.service.search("dog")
        self.assertEqual(result.failed_sources, ["Zvukogram"])


class WebSoundCacheTests(unittest.IsolatedAsyncioTestCase):
    async def test_cache_survives_recreation_and_is_scoped_to_bot(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "cache.sqlite")
            cache = WebSoundCache(path, bot_id=1)
            await cache.initialize()
            await cache.put("freesound:42", "telegram-file-id")
            self.assertEqual(await WebSoundCache(path, bot_id=1).get("freesound:42"), "telegram-file-id")
            self.assertIsNone(await WebSoundCache(path, bot_id=2).get("freesound:42"))
            await cache.put("freesound:42", "updated-file-id")
            self.assertEqual(await cache.get("freesound:42"), "updated-file-id")
            await cache.delete("freesound:42")
            self.assertIsNone(await cache.get("freesound:42"))
