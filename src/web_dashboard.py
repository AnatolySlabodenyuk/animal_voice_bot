from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import os
import random
from aiogram import Bot
from config_data.config import Config, load_config
from database.database import (
    get_random_sound,
    get_random_names,
    get_image_file_id_from_table,
)

# Загружаем конфиг и инициализируем бота для получения ссылок на файлы
config: Config = load_config()
bot = Bot(token=config.tg_bot.token)

app = FastAPI()


@app.get("/game", response_class=HTMLResponse)
async def game_page():
    """
    Страница мини-приложения
    """
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
    sound = await get_random_sound()
    if not sound:
        return {"error": "No sounds found"}

    correct_name, category, audio_file_id = sound

    # Получаем ссылку на аудио
    try:
        audio_file = await bot.get_file(audio_file_id)
        audio_url = f"https://api.telegram.org/file/bot{config.tg_bot.token}/{audio_file.file_path}"
    except Exception as e:
        print(f"Error getting audio link: {e}")
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
                print(f"Error getting image link for {name}: {e}")

        options.append(
            {"name": name, "image_url": image_url, "is_correct": (name == correct_name)}
        )

    return {"voice_url": audio_url, "options": options}
