from aiogram import F, Router
from aiogram.client.session import aiohttp
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart
from keyboards.base_kb import base_kb
from keyboards.admin_kb import admin_kb
from keyboards.inline_kb_new import AnimalsCallbackFactory, create_inline_kb
from lexicon.base_commands_enum import BaseCommandsEnum
from lexicon.buttons_enum import ButtonsEnum
from database.database import get_file_id_from_table, add_audio_to_table, get_button_ids, \
    get_file_name_from_table
from bs4 import BeautifulSoup

# Инициализируем роутер уровня модуля
router = Router()


# Этот хэндлер срабатывает на команду /start
@router.message(CommandStart())
async def process_start_command(message: Message):
    await message.answer(
        text=BaseCommandsEnum.START.value,
        reply_markup=base_kb
    )


# Этот хэндлер срабатывает на кнопку restart_button
@router.message(F.text == ButtonsEnum.RESTART_BUTTON.value)
async def process_restart_button(message: Message):
    await message.answer(
        text=BaseCommandsEnum.START.value,
        reply_markup=base_kb
    )


# Этот хэндлер срабатывает на команду /help
@router.message(Command(commands="help"))
async def process_help_command(message: Message):
    await message.answer(
        text=BaseCommandsEnum.HELP.value,
        reply_markup=base_kb
    )


# Этот хэндлер срабатывает на кнопку help_button
@router.message(F.text == ButtonsEnum.HELP_BUTTON.value)
async def process_help_button(message: Message):
    await message.answer(
        text=BaseCommandsEnum.HELP.value,
        reply_markup=base_kb
    )


# Этот хэндлер срабатывает на кнопку выбрать животное
@router.message(F.text == ButtonsEnum.ANIMAL_CHOOSE_BUTTON.value)
async def process_animal_choose_button(message: Message):
    button_ids = await get_button_ids()
    inline_kb = await create_inline_kb(width=1, button_ids=button_ids)
    await message.answer(
        text=BaseCommandsEnum.ANIMAL_CHOOSE_BUTTON.value,
        reply_markup=inline_kb
    )


# Универсальная функция для обработки нажатий на инлайн-кнопки с животными
async def process_button_press(callback: CallbackQuery, animal_id: int, animal_name: str):
    file_id = await get_file_id_from_table(animal_id)
    await callback.answer(f"Так говорит Мистер {animal_name}")
    await callback.message.answer_audio(audio=file_id)


# Этот хэндлер будет срабатывать на нажатие любой инлайн кнопки
# и отправлять в чат форматированный ответ с данными из callback_data
@router.callback_query(AnimalsCallbackFactory.filter())
async def process_animal_press(
        callback: CallbackQuery,
        callback_data: AnimalsCallbackFactory
):
    await process_button_press(
        callback=callback,
        animal_id=callback_data.button_id,
        animal_name=await get_file_name_from_table(callback_data.button_id),
    )


# Этот хэндлер срабатывает на кнопку найти в интернете
@router.message(F.text == ButtonsEnum.SEARCH_IN_WEB.value)
async def process_search_in_web_button(message: Message):
    await message.answer(text=BaseCommandsEnum.SEARCH_IN_WEB_BUTTON.value)


@router.message(
    # F.text == "Поезд"
)
async def search_audio(message: Message):
    BASE_URL = "https://zvukogram.com/?r=search&s="
    query = message.text.strip()
    search_url = BASE_URL + query

    async with aiohttp.ClientSession() as session:
        async with session.get(search_url, ssl=False) as response:
            if response.status == 200:
                html_content = await response.text()
                soup = BeautifulSoup(html_content, "html.parser")

                # Находим блоки с треками
                audio_blocks = soup.find_all(
                    "div", class_="onetrack accordion")

                if not audio_blocks:
                    await message.reply("К сожалению, ничего не найдено.")
                    return

                # Ограничиваем количество отправляемых треков
                for block in audio_blocks[:3]:
                    try:
                        # Извлекаем данные
                        title = block.find(
                            "div", class_="waveTitle").text.strip()
                        mp3_link = block.find(
                            "a", class_="dwdButtn", text="mp3")["href"]

                        # Формируем полный URL
                        full_mp3_url = "https://zvukogram.com" + mp3_link

                        await message.answer_audio(
                            audio=full_mp3_url,
                            caption=f"🎵 {title}"
                        )

                    except Exception as e:
                        await message.reply(f"Ошибка при обработке трека: {e}")
            else:
                await message.reply(f"Ошибка {response.status}: Не удалось подключиться к сайту.")
