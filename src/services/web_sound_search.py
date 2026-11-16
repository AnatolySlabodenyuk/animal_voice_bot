import asyncio
import logging
from dataclasses import dataclass
from hashlib import sha256
from itertools import zip_longest
from urllib.parse import urlencode, urljoin, urlsplit

import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# A small local dictionary keeps common Russian searches free of translation APIs.
FREESOUND_QUERIES = {
    "собака": "dog", "лай": "dog bark", "лай собаки": "dog bark",
    "кошка": "cat", "мяуканье": "cat meow", "мяуканье кошки": "cat meow",
    "корова": "cow", "мычание": "cow moo", "лошадь": "horse",
    "ржание": "horse neigh", "лев": "lion", "рычание": "growl",
    "волк": "wolf", "вой волка": "wolf howl", "птицы": "birds",
    "пение птиц": "birds singing", "сова": "owl", "лягушка": "frog",
    "дождь": "rain", "шум дождя": "rain", "гроза": "thunderstorm",
    "гром": "thunder", "ветер": "wind", "море": "sea waves",
    "волны": "waves", "река": "river", "огонь": "fire crackling",
    "машина": "car", "мотор": "engine", "поезд": "train",
    "самолет": "airplane", "вертолет": "helicopter", "сирена": "siren",
    "дверь": "door", "скрип двери": "door creak", "шаги": "footsteps",
    "колокол": "bell", "звонок": "bell", "аплодисменты": "applause",
}


class SoundSearchError(Exception):
    """An unavailable source or an unusable audio download."""


@dataclass
class WebSound:
    key: str
    title: str
    audio_url: str
    source: str
    page_url: str
    author: str = ""
    license: str = ""


@dataclass
class SearchResults:
    sounds: list[WebSound]
    failed_sources: list[str]


class WebSoundSearch:
    ZVUKOGRAM_URL = "https://zvukogram.com/"
    FREESOUND_URL = "https://freesound.org/apiv2/search/"
    MAX_AUDIO_BYTES = 20 * 1024 * 1024
    MAX_SEARCH_BYTES = 2 * 1024 * 1024

    def __init__(self, session: aiohttp.ClientSession, result_count: int,
                 freesound_api_key: str = "", source: str = "both"):
        if source not in ("both", "freesound", "zvukogram"):
            raise ValueError("WEB_SOUND_SOURCE must be both, freesound or zvukogram")
        self.session = session
        self.result_count = max(1, min(result_count, 20))
        self.freesound_api_key = freesound_api_key
        self.source = source

    async def search(self, query: str) -> SearchResults:
        if self.source == "freesound" and not self.freesound_api_key:
            return SearchResults([], ["Freesound"])
        providers = []
        if self.source in ("both", "zvukogram"):
            providers.append(("Zvukogram", self._search_zvukogram(query)))
        if self.source in ("both", "freesound") and self.freesound_api_key:
            providers.append(("Freesound", self._search_freesound(query)))
        responses = await asyncio.gather(
            *(request for _, request in providers), return_exceptions=True
        )
        successful = []
        failed = []
        for (name, _), response in zip(providers, responses):
            if isinstance(response, Exception):
                # Do not log URLs/headers: they can include credentials or user queries.
                logger.warning("Sound source %s failed (%s)", name, type(response).__name__)
                failed.append(name)
            else:
                successful.append(response)
        # Interleave sources so a full first source cannot hide the second one.
        sounds = []
        seen = set()
        for row in zip_longest(*successful):
            for sound in row:
                if sound is not None and sound.key not in seen:
                    sounds.append(sound)
                    seen.add(sound.key)
        return SearchResults(sounds[:self.result_count], failed)

    async def _read_limited(self, response: aiohttp.ClientResponse, limit: int) -> bytes:
        response.raise_for_status()
        if response.content_length is not None and response.content_length > limit:
            raise SoundSearchError("Файл слишком большой.")
        content = bytearray()
        async for chunk in response.content.iter_chunked(64 * 1024):
            if len(content) + len(chunk) > limit:
                raise SoundSearchError("Файл слишком большой.")
            content.extend(chunk)
        return bytes(content)

    async def _search_zvukogram(self, query: str) -> list[WebSound]:
        async with self.session.get(
            self.ZVUKOGRAM_URL, params={"r": "search", "s": query}
        ) as response:
            content = await self._read_limited(response, self.MAX_SEARCH_BYTES)
        return await asyncio.to_thread(self._parse_zvukogram, content, query)

    def _parse_zvukogram(self, content: bytes, query: str) -> list[WebSound]:
        soup = BeautifulSoup(content, "html.parser")
        blocks = soup.select("div.onetrack.accordion")
        sounds = []
        page_url = self.ZVUKOGRAM_URL + "?" + urlencode({"r": "search", "s": query})
        for block in blocks:
            title = block.select_one(".waveTitle")
            track = block.get("data-track")
            if title is None or not title.get_text(strip=True) or not track:
                continue
            audio_url = urljoin(self.ZVUKOGRAM_URL, track)
            if urlsplit(audio_url).scheme not in ("http", "https"):
                continue
            sounds.append(WebSound(
                key="zvukogram:" + sha256(audio_url.encode()).hexdigest(),
                title=title.get_text(" ", strip=True), audio_url=audio_url,
                source="Zvukogram", page_url=page_url,
            ))
            if len(sounds) >= self.result_count:
                break
        if blocks and not sounds:
            raise SoundSearchError("Не удалось прочитать результаты Zvukogram.")
        return sounds

    async def _search_freesound(self, query: str) -> list[WebSound]:
        normalized = " ".join(query.casefold().replace("ё", "е").split())
        async with self.session.get(
            self.FREESOUND_URL,
            params={
                "query": FREESOUND_QUERIES.get(normalized, query),
                "fields": "id,name,previews,url,username,license",
                "page_size": self.result_count,
                "group_by_pack": 1,
                "sort": "score",
            },
            headers={"Authorization": f"Token {self.freesound_api_key}"},
        ) as response:
            response.raise_for_status()
            data = await response.json()
        sounds = []
        for item in data["results"]:
            preview = item.get("previews", {}).get("preview-hq-mp3")
            if not preview or not item.get("name"):
                continue
            sounds.append(WebSound(
                key=f"freesound:{item['id']}", title=item["name"], audio_url=preview,
                source="Freesound", page_url=item["url"],
                author=item.get("username", ""), license=item.get("license", ""),
            ))
        return sounds

    async def download(self, sound: WebSound) -> bytes:
        try:
            async with self.session.get(sound.audio_url) as response:
                response.raise_for_status()
                content_type = response.content_type
                if not (content_type.startswith("audio/") or content_type in (
                    "application/octet-stream", "binary/octet-stream"
                )):
                    raise SoundSearchError("Источник вернул страницу вместо аудио.")
                content = await self._read_limited(response, self.MAX_AUDIO_BYTES)
                if not content:
                    raise SoundSearchError("Источник вернул пустой файл.")
                return content
        except (aiohttp.ClientError, asyncio.TimeoutError) as error:
            raise SoundSearchError("Не удалось скачать звук. Попробуйте другой результат.") from error
