from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import os
import random
import logging
from aiogram import Bot
from config_data.config import Config, load_config
from database.database import (
    get_random_sound,
    get_random_names,
    get_image_file_id_from_table,
)

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
        audio_url = f"https://api.telegram.org/file/bot{config.tg_bot.token}/{audio_file.file_path}"
    except Exception as e:
        logger.error(
            f"Error getting audio link for sound '{correct_name}' (ID: {audio_file_id}): {e}"
        )
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
                image_url = f"https://api.telegram.org/file/bot{config.tg_bot.token}/{img_file.file_path}"
            except Exception as e:
                logger.error(f"Error getting image link for {name}: {e}")

        options.append(
            {"name": name, "image_url": image_url, "is_correct": (name == correct_name)}
        )

    logger.debug(f"Generated options: {[opt['name'] for opt in options]}")
    return {"voice_url": audio_url, "options": options}
