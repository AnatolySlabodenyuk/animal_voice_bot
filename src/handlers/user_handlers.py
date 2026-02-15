import aiohttp
from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ChatAction
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from bs4 import BeautifulSoup

from config_data.config import Config, load_config
from database.database import (
    get_audio_file_id_from_table,
    get_audio_file_name_from_table,
    get_image_file_id_from_table,
    increment_user_request_count,
)
from keyboards.base_kb import base_kb
from keyboards.voice_inline_kb import (
    VoiceNamesCallbackFactory,
    VoiceTypesCallbackFactory,
    create_voice_category_inline_kb,
    create_voice_names_inline_kb,
)
from lexicon.base_commands_enum import BaseCommandsEnum
from lexicon.buttons_enum import ButtonsEnum
from lexicon.voice_types_enum import VoiceCategoryEnum

router = Router()

config: Config = load_config()

search_result_count = int(config.tg_bot.search_result_count)


class SearchInNetState(StatesGroup):
    waiting_for_key_word = State()


@router.message(CommandStart())
async def process_start_command(message: Message):
    """
    Этот хэндлер срабатывает на команду /start
    """
    if message.from_user:
        await increment_user_request_count(
            message.from_user.id, message.from_user.username or ""
        )
    await message.answer(text=BaseCommandsEnum.START.value, reply_markup=base_kb)


@router.message(F.text == ButtonsEnum.RESTART_BUTTON.value)
async def process_restart_button(message: Message):
    """
    Этот хэндлер срабатывает на кнопку restart_button
    """
    if message.from_user:
        await increment_user_request_count(
            message.from_user.id, message.from_user.username or ""
        )
    await message.answer(text=BaseCommandsEnum.START.value, reply_markup=base_kb)


@router.message(Command(commands="help"))
async def process_help_command(message: Message):
    """
    Этот хэндлер срабатывает на команду /help
    """
    if message.from_user:
        await increment_user_request_count(
            message.from_user.id, message.from_user.username or ""
        )
    await message.answer(text=BaseCommandsEnum.HELP.value, reply_markup=base_kb)


# Этот хэндлер срабатывает на кнопку help_button
@router.message(F.text == ButtonsEnum.HELP_BUTTON.value)
async def process_help_button(message: Message):
    """
    Этот хэндлер срабатывает на кнопку help_button
    """
    if message.from_user:
        await increment_user_request_count(
            message.from_user.id, message.from_user.username or ""
        )
    await message.answer(text=BaseCommandsEnum.HELP.value, reply_markup=base_kb)


@router.message(F.text == ButtonsEnum.VOICE_CATEGORY_CHOOSE_BUTTON.value)
async def process_voice_category_choose_button(message: Message):
    """
    Этот хэндлер срабатывает на кнопку выбрать категорию
    """
    if message.from_user:
        await increment_user_request_count(
            message.from_user.id, message.from_user.username or ""
        )
    await message.answer(
        text=BaseCommandsEnum.CHOOSE_CATEGORY.value,
        reply_markup=await create_voice_category_inline_kb(),
    )


@router.callback_query(VoiceTypesCallbackFactory.filter())
async def inline_products_button_press(
        callback: CallbackQuery, callback_data: VoiceTypesCallbackFactory
):
    """
    Этот хэндлер срабатывает на выбор категории
    """
    if callback.from_user:
        await increment_user_request_count(
            callback.from_user.id, callback.from_user.username or ""
        )
    if callback_data.voice_type == VoiceCategoryEnum.animals.value:
        if callback.message:
            await callback.message.answer(
                text=BaseCommandsEnum.CHOOSE_ANIMAL.value,
                reply_markup=await create_voice_names_inline_kb(
                    voice_names_list=await get_audio_file_name_from_table(
                        category=VoiceCategoryEnum.animals.value
                    )
                ),
            )
        await callback.answer()

    elif callback_data.voice_type == VoiceCategoryEnum.transport.value:
        if callback.message:
            await callback.message.answer(
                text=BaseCommandsEnum.CHOOSE_TRANSPORT.value,
                reply_markup=await create_voice_names_inline_kb(
                    voice_names_list=await get_audio_file_name_from_table(
                        category=VoiceCategoryEnum.transport.value
                    )
                ),
            )
        await callback.answer()

    elif callback_data.voice_type == VoiceCategoryEnum.objects.value:
        if callback.message:
            await callback.message.answer(
                text=BaseCommandsEnum.CHOOSE_OBJECT.value,
                reply_markup=await create_voice_names_inline_kb(
                    voice_names_list=await get_audio_file_name_from_table(
                        category=VoiceCategoryEnum.objects.value
                    )
                ),
            )
        await callback.answer()

    else:
        if callback.message:
            await callback.message.answer(text=BaseCommandsEnum.SOMETHING_WRONG.value)
        await callback.answer()


async def get_audio_file(callback: CallbackQuery, voice_name: str):
    """
    Универсальная функция для обработки нажатий на инлайн-кнопки с животными
    """
    audio_file_id = await get_audio_file_id_from_table(voice_name)
    image_file_id = await get_image_file_id_from_table(voice_name)
    await callback.answer(f"Так звучит {voice_name}")
    if callback.message and audio_file_id:
        await callback.message.bot.send_chat_action(
            chat_id=callback.message.chat.id, action=ChatAction.UPLOAD_VOICE
        )
        await callback.message.answer_audio(audio=audio_file_id)
        await callback.message.answer_photo(photo=image_file_id)


@router.callback_query(VoiceNamesCallbackFactory.filter())
async def process_voice_button_press(
        callback: CallbackQuery, callback_data: VoiceNamesCallbackFactory
):
    """
    Этот хэндлер будет срабатывать на нажатие любой инлайн кнопки
    и отправлять в чат форматированный ответ с данными из callback_data
    """
    if callback.from_user:
        await increment_user_request_count(
            callback.from_user.id, callback.from_user.username or ""
        )
    await get_audio_file(
        callback=callback,
        voice_name=callback_data.voice_name,
    )


@router.message(F.text == ButtonsEnum.SEARCH_IN_WEB.value)
async def process_search_in_web_button(message: Message, state: FSMContext):
    """
    Этот хэндлер срабатывает на кнопку найти в интернете
    """
    if message.from_user:
        await increment_user_request_count(
            message.from_user.id, message.from_user.username or ""
        )
    await message.answer(text=BaseCommandsEnum.SEARCH_IN_WEB_BUTTON.value)

    await state.set_state(SearchInNetState.waiting_for_key_word)


@router.message(SearchInNetState.waiting_for_key_word)
async def search_audio(message: Message, state: FSMContext):
    """
    Хэндлер для поиска аудио на Zvukogram.com
    """
    if message.from_user:
        await increment_user_request_count(
            message.from_user.id, message.from_user.username or ""
        )
    BASE_URL = "https://zvukogram.com/?r=search&s="
    query = (message.text or "").strip()
    await state.update_data(waiting_for_key_word=query)

    await message.bot.send_chat_action(
        chat_id=message.chat.id, action=ChatAction.UPLOAD_VOICE
    )

    search_url = BASE_URL + query

    async with aiohttp.ClientSession() as session:
        async with session.get(search_url, ssl=False) as response:
            if response.status == 200:
                html_content = await response.text()
                soup = BeautifulSoup(html_content, "html.parser")

                # Поиск элементов треков
                audio_blocks = soup.find_all("div", class_="onetrack accordion")

                if not audio_blocks:
                    await message.reply("К сожалению, ничего не найдено.")
                    return

                # Ограничиваем количество треков
                for block in audio_blocks[:search_result_count]:
                    try:
                        # Извлечение данных
                        title = block.find("div", class_="waveTitle").text.strip()
                        mp3_link = block["data-track"]
                        full_mp3_url = f"https://zvukogram.com{mp3_link}"

                        # Скачиваем файл перед отправкой
                        async with session.get(full_mp3_url, ssl=False) as audio_resp:
                            if audio_resp.status == 200:
                                audio_content = await audio_resp.read()
                                audio_file = BufferedInputFile(
                                    audio_content, filename=f"{title}.mp3"
                                )

                                # Отправка пользователю
                                await message.answer_audio(
                                    audio=audio_file, caption=f"🎵 {title}"
                                )

                    except Exception as e:
                        # await message.reply(f"Ошибка при обработке трека: {e}")
                        print(f"Ошибка при обработке трека: {e}")
            else:
                await message.reply(
                    f"Ошибка {response.status}: Не удалось подключиться к сайту."
                )

    await state.clear()
