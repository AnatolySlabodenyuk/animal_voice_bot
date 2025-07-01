from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message
from aiogram.filters import Command

from config_data.config import Config, load_config
from keyboards.admin_kb import admin_kb
from keyboards.voice_category_simple_kb import voice_category_simple_kb
from lexicon.base_commands_enum import BaseCommandsEnum
from lexicon.buttons_enum import ButtonsEnum
from database.database import add_audio_to_table
from database.database import get_top_users_stats

router = Router()

config: Config = load_config()

ADMIN_USER_ID = config.tg_bot.admin_user_id  # ЗАМЕНИ на свой Telegram user_id

state_file_id = None


class AudioUploadState(StatesGroup):
    waiting_for_name = State()
    waiting_for_category = State()


@router.message(Command(commands="admin"))
async def process_admin_command(message: Message):
    """
    Этот хэндлер срабатывает на команду /admin
    """
    await message.answer(
        text=BaseCommandsEnum.ADMIN.value,
        reply_markup=admin_kb
    )


@router.message(F.text == ButtonsEnum.AUDIO_UPLOAD.value)
async def process_audio_upload_button(message: Message):
    """
    Этот хэндлер срабатывает на кнопку загрузить звук
    """
    await message.answer(text=BaseCommandsEnum.AUDIO_UPLOAD.value)


@router.message(F.audio)
async def process_upload_audio_new(message: Message, state: FSMContext):
    """
    Этот хэндлер срабатывает на загрузку аудио
    """
    global state_file_id
    state_file_id = message.audio.file_id
    await message.answer(
        text=BaseCommandsEnum.SET_FILE_NAME.value,
        reply_markup=admin_kb
    )
    await state.set_state(AudioUploadState.waiting_for_name)


@router.message(AudioUploadState.waiting_for_name)
async def audio_name_chosen(message: Message, state: FSMContext):
    """
    Этот хэндлер ожидает ввода названия для файла
    """
    await state.update_data(waiting_for_name=message.text)
    await message.answer(
        text=BaseCommandsEnum.SET_FILE_CATEGORY.value,
        reply_markup=voice_category_simple_kb
    )
    await state.set_state(AudioUploadState.waiting_for_category)


@router.message(AudioUploadState.waiting_for_category)
async def audio_category_chosen(message: Message, state: FSMContext):
    """
    Этот хэндлер ожидает ввода категории для файла
    """
    global state_file_id
    await state.update_data(waiting_for_category=message.text)
    user_data = await state.get_data()
    await add_audio_to_table(
        file_name=user_data['waiting_for_name'],
        category=user_data['waiting_for_category'],
        file_id=state_file_id or ""
    )
    await message.answer(
        text=f"Аудиофайл сохранен с именем {user_data['waiting_for_name']}\n и категорией {user_data['waiting_for_category']}!",
        reply_markup=admin_kb
    )
    # Сброс состояния и сохранённых данных у пользователя
    state_file_id = None
    await state.clear()


@router.message(Command(commands="stats"))
async def process_stats_command(message: Message):
    """
    Этот хэндлер для вывода статистики
    """
    if message.from_user and message.from_user.id == int(ADMIN_USER_ID):
        stats = await get_top_users_stats()
        if not stats:
            await message.answer("Статистика пуста.")
            return
        text = "<b>Топ пользователей по запросам:</b>\n"
        for idx, (user_id, username, count, last) in enumerate(stats, 1):
            text += f"{idx}. <code>{username or user_id}</code> — <b>{count}</b> (посл. {last})\n"
        await message.answer(text, parse_mode="HTML")
    else:
        await message.answer("Нет доступа.")
