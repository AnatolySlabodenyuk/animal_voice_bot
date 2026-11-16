import asyncio
import logging

import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config_data.config import Config, load_config
from database.database import (create_images_table, create_sounds_table,
                               create_user_stats_table)
from database.web_sound_cache import WebSoundCache
from handlers import admin_handlers, other_handlers, user_handlers
from keyboards.set_menu import set_main_menu
from services.web_sound_search import WebSoundSearch

# Инициализируем логгер
logger = logging.getLogger(__name__)


# Функция конфигурирования и запуска бота
async def main():
    # Конфигурируем логирование
    logging.basicConfig(
        level=logging.INFO,
        format="%(filename)s:%(lineno)d #%(levelname)-8s "
               "[%(asctime)s] - %(name)s - %(message)s")

    # Выводим в консоль информацию о начале запуска бота
    logger.info("Starting bot")

    # Загружаем конфиг в переменную config
    config: Config = load_config()

    await create_sounds_table()
    await create_images_table()
    await create_user_stats_table()

    # Инициализируем бот и диспетчер
    async with Bot(
        token=config.tg_bot.token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    ) as bot, aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=30, connect=5, sock_read=15),
        connector=aiohttp.TCPConnector(limit=10, limit_per_host=5),
    ) as session:
        web_sound_cache = WebSoundCache(config.tg_bot.database_path, bot.id)
        await web_sound_cache.initialize()
        web_sound_search = WebSoundSearch(
            session, int(config.tg_bot.search_result_count),
            config.tg_bot.freesound_api_key,
            source=config.tg_bot.web_sound_source,
        )
        dp = Dispatcher()

        # Настраиваем кнопку Menu
        await set_main_menu(bot)

        # Регистриуем роутеры в диспетчере
        dp.include_router(admin_handlers.router)
        dp.include_router(user_handlers.router)
        dp.include_router(other_handlers.router)

        # Пропускаем накопившиеся апдейты и запускаем polling
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(
            bot, close_bot_session=False,
            web_sound_search=web_sound_search, web_sound_cache=web_sound_cache,
        )


if __name__ == "__main__":
    asyncio.run(main())
