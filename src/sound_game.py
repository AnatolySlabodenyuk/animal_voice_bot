import logging
import os
import random
import secrets
import time
import mimetypes
from io import BytesIO

from aiogram import Bot
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from config_data.config import Config, load_config
from database.database import (get_image_file_id_from_table, get_random_names,
                               get_random_sound)

# Инициализируем логгер
logger = logging.getLogger(__name__)

# Конфигурируем логирование
logging.basicConfig(
    level=logging.INFO,
    format="%(filename)s:%(lineno)d #%(levelname)-8s "
           "[%(asctime)s] - %(name)s - %(message)s",
)

# Загружаем конфиг и инициализируем бота для получения ссылок на файлы
config: Config = load_config()
bot = Bot(token=config.tg_bot.token)

app = FastAPI()

# Opaque, short-lived references keep Telegram credentials server-side.
media_files: dict[str, tuple[str, float]] = {}


def register_media(file_path: str) -> str:
    now = time.monotonic()
    for key, (_, expiry) in list(media_files.items()):
        if expiry <= now:
            del media_files[key]
    while len(media_files) >= 2048:
        del media_files[next(iter(media_files))]
    key = secrets.token_urlsafe(24)
    media_files[key] = (file_path, now + 3600)
    return key


@app.get('/api/media/{key}')
async def get_media(key: str):
    item = media_files.get(key)
    if item is None or item[1] <= time.monotonic():
        media_files.pop(key, None)
        raise HTTPException(status_code=404, detail='Media unavailable; reload the question')
    file_path, _ = item
    destination = BytesIO()
    try:
        await bot.download_file(file_path, destination=destination)
    except Exception:
        logger.warning('Unable to retrieve media from Telegram')
        raise HTTPException(status_code=502, detail='Media temporarily unavailable') from None
    content = destination.getvalue()
    content_type = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
    if content.startswith(b'\xff\xd8\xff'):
        content_type = 'image/jpeg'
    elif content.startswith(b'\x89PNG\r\n\x1a\n'):
        content_type = 'image/png'
    elif content.startswith(b'OggS'):
        content_type = 'audio/ogg'
    elif content.startswith(b'ID3') or (len(content) > 1 and content[0] == 255 and content[1] & 224 == 224):
        content_type = 'audio/mpeg'
    elif content.startswith(b'RIFF') and content[8:12] == b'WEBP':
        content_type = 'image/webp'
    elif file_path.lower().endswith(('.ogg', '.oga')):
        content_type = 'audio/ogg'
    return Response(content=content,
                    media_type=content_type,
                    headers={'Cache-Control': 'private, max-age=300',
                             'X-Content-Type-Options': 'nosniff'})

# Подключаем статические файлы
app.mount(
    "/static",
    StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")),
    name="static",
)


@app.get("/")
async def root():
    """
    Перенаправление на страницу игры или приветствие
    """
    from fastapi.responses import RedirectResponse

    logger.debug("Redirecting to /game")
    return RedirectResponse(url="/game")


@app.get("/favicon.ico")
async def favicon():
    """
    Отдаем реальную иконку сайта
    """
    from fastapi.responses import FileResponse

    file_path = os.path.join(os.path.dirname(__file__), "static", "favicon.png")
    logger.debug(f"Serving favicon from {file_path}")
    return FileResponse(file_path)


@app.get("/game", response_class=HTMLResponse)
async def game_page():
    """
    Страница мини-приложения
    """
    logger.debug("Serving game page")
    file_path = os.path.join(os.path.dirname(__file__), "templates", "game.html")
    if not os.path.exists(file_path):
        return HTMLResponse("Template not found", status_code=404)

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    return HTMLResponse(content)


@app.get("/api/get_question")
async def get_question():
    """
    API для получения вопроса для игры
    """
    logger.debug("Start processing get_question")
    sound = await get_random_sound()
    if not sound:
        logger.warning("No sounds found in database")
        return {"error": "No sounds found"}

    correct_name, category, audio_file_id = sound
    logger.debug(f"Selected target sound: {correct_name} (ID: {audio_file_id})")

    # Получаем ссылку на аудио
    try:
        audio_file = await bot.get_file(audio_file_id)
        audio_url = f"/api/media/{register_media(audio_file.file_path)}"
    except Exception:
        logger.warning('Unable to retrieve audio metadata from Telegram')
        audio_url = ""

    # Выбираем неправильные ответы
    decoys = await get_random_names(count=2, exclude_name=correct_name)

    # Формируем список вариантов
    names = [correct_name] + decoys
    random.shuffle(names)

    options = []
    for name in names:
        image_file_id = await get_image_file_id_from_table(name)
        image_url = ""
        if image_file_id:
            try:
                # Получаем ссылку на картинку
                # Важно: телеграм ссылки живут 1 час
                img_file = await bot.get_file(image_file_id)
                image_url = f"/api/media/{register_media(img_file.file_path)}"
            except Exception:
                logger.warning('Unable to retrieve image metadata from Telegram')

        options.append(
            {"name": name, "image_url": image_url, "is_correct": (name == correct_name)}
        )

    logger.debug(f"Generated options: {[opt['name'] for opt in options]}")
    return {"voice_url": audio_url, "options": options}
