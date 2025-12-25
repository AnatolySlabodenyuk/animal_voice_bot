import asyncio
import random

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from config_data.config import Config, load_config
from database.database import (add_audio_to_table, add_image_to_table,
                               get_all_users, get_random_names,
                               get_random_sound, get_top_users_stats,
                               increment_user_request_count)
from keyboards.admin_kb import admin_kb
from keyboards.voice_category_simple_kb import voice_category_simple_kb
from keyboards.voice_inline_kb import (GameCallbackFactory,
                                       create_game_inline_kb)
from lexicon.base_commands_enum import BaseCommandsEnum
from lexicon.buttons_enum import ButtonsEnum

router = Router()

config: Config = load_config()

ADMIN_USER_ID = config.tg_bot.admin_user_id  # ЗАМЕНИ на свой Telegram user_id
feedback_message = config.tg_bot.feedback_message


class UploadState(StatesGroup):
    waiting_for_audio_file_id = State()
    waiting_for_audio_name = State()
    waiting_for_audio_category = State()

    waiting_for_image_file_id = State()
    waiting_for_image_name = State()
    waiting_for_image_category = State()


@router.message(Command(commands="admin"))
async def process_admin_command(message: Message):
    """
    Этот хэндлер срабатывает на команду /admin
    """
    if message.from_user and message.from_user.id == int(ADMIN_USER_ID):
        await message.answer(
            text=BaseCommandsEnum.ADMIN.value,
            reply_markup=admin_kb
        )
    else:
        await message.answer(BaseCommandsEnum.ACCESS_DENIED.value)


# --- SOUNDS HANDLERS ---
@router.message(F.text == ButtonsEnum.AUDIO_UPLOAD.value)
async def process_audio_upload_button(message: Message, state: FSMContext):
    """
    Этот хэндлер срабатывает на кнопку загрузить звук
    """
    if message.from_user and message.from_user.id == int(ADMIN_USER_ID):
        await state.set_state(UploadState.waiting_for_audio_file_id)
        await message.answer(text=BaseCommandsEnum.AUDIO_UPLOAD.value)
    else:
        await message.answer(BaseCommandsEnum.ACCESS_DENIED.value)


@router.message(F.audio)
async def process_upload_audio_new(message: Message, state: FSMContext):
    """
    Этот хэндлер срабатывает на загрузку аудио
    """
    if message.from_user and message.from_user.id == int(ADMIN_USER_ID):
        await state.update_data(waiting_for_audio_file_id=message.audio.file_id)
        await message.answer(
            text=BaseCommandsEnum.SET_AUDIO_FILE_NAME.value,
            reply_markup=admin_kb
        )
        await state.set_state(UploadState.waiting_for_audio_name)
    else:
        await message.answer(BaseCommandsEnum.ACCESS_DENIED.value)


@router.message(UploadState.waiting_for_audio_name)
async def audio_name_chosen(message: Message, state: FSMContext):
    """
    Этот хэндлер ожидает ввода названия для аудио-файла
    """
    await state.update_data(waiting_for_audio_name=message.text)
    await message.answer(
        text=BaseCommandsEnum.SET_FILE_CATEGORY.value,
        reply_markup=voice_category_simple_kb
    )
    await state.set_state(UploadState.waiting_for_audio_category)


@router.message(UploadState.waiting_for_audio_category)
async def audio_category_chosen(message: Message, state: FSMContext):
    """
    Этот хэндлер ожидает ввода категории для аудио-файла
    """
    await state.update_data(waiting_for_audio_category=message.text)
    user_data = await state.get_data()
    await add_audio_to_table(
        file_name=user_data['waiting_for_audio_name'],
        category=user_data['waiting_for_audio_category'],
        file_id=user_data['waiting_for_audio_file_id'] or ""
    )
    await message.answer(
        text=f"Аудиофайл сохранен с именем {user_data['waiting_for_audio_name']}\n и категорией {user_data['waiting_for_audio_category']}!",
        reply_markup=admin_kb
    )
    await state.clear()


# --- IMAGES HANDLERS ---
@router.message(F.text == ButtonsEnum.IMAGE_UPLOAD.value)
async def process_image_upload_button(message: Message, state: FSMContext):
    """
    Этот хэндлер срабатывает на кнопку загрузить картинку
    """
    if message.from_user and message.from_user.id == int(ADMIN_USER_ID):
        await state.set_state(UploadState.waiting_for_image_file_id)
        await message.answer(text=BaseCommandsEnum.IMAGE_UPLOAD.value)
    else:
        await message.answer(BaseCommandsEnum.ACCESS_DENIED.value)


@router.message(F.photo)
async def process_upload_image_new(message: Message, state: FSMContext):
    """
    Этот хэндлер срабатывает на загрузку картинки
    """
    if message.from_user and message.from_user.id == int(ADMIN_USER_ID):
        await state.update_data(waiting_for_image_file_id=message.photo[-1].file_id)
        await message.answer(
            text=BaseCommandsEnum.SET_IMAGE_FILE_NAME.value,
            reply_markup=admin_kb
        )
        await state.set_state(UploadState.waiting_for_image_name)
    else:
        await message.answer(BaseCommandsEnum.ACCESS_DENIED.value)


@router.message(UploadState.waiting_for_image_name)
async def image_name_chosen(message: Message, state: FSMContext):
    """
    Этот хэндлер ожидает ввода названия для картинки
    """
    await state.update_data(waiting_for_image_name=message.text)
    await message.answer(
        text=BaseCommandsEnum.SET_FILE_CATEGORY.value,
        reply_markup=voice_category_simple_kb
    )
    await state.set_state(UploadState.waiting_for_image_category)


@router.message(UploadState.waiting_for_image_category)
async def image_category_chosen(message: Message, state: FSMContext):
    """
    Этот хэндлер ожидает ввода категории для картинки
    """
    await state.update_data(waiting_for_image_category=message.text)
    user_data = await state.get_data()
    await add_image_to_table(
        file_name=user_data['waiting_for_image_name'],
        category=user_data['waiting_for_image_category'],
        file_id=user_data['waiting_for_image_file_id'] or ""
    )
    await message.answer(
        text=f"Картинка сохранена с именем {user_data['waiting_for_image_name']}\n и категорией {user_data['waiting_for_image_category']}!",
        reply_markup=admin_kb
    )
    await state.clear()


# --- STATS HANDLERS ---
@router.message(F.text == ButtonsEnum.GET_STATS.value)
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
        await message.answer(BaseCommandsEnum.ACCESS_DENIED.value)


async def send_feedback_to_all_users(bot, message: Message):
    """
    Отправить сообщение с предложением оставить обратную связь всем пользователям
    """
    if message.from_user and message.from_user.id == int(ADMIN_USER_ID):
        users = await get_all_users()

        if not users:
            await message.answer(BaseCommandsEnum.NO_USERS_FOUND.value)
            return

        success_count = 0
        error_count = 0

        for user_id, username in users:
            try:
                await bot.send_message(
                    chat_id=user_id,
                    text=feedback_message
                )
                success_count += 1
                # Небольшая задержка чтобы не превысить лимиты Telegram
                await asyncio.sleep(0.05)
            except Exception as e:
                error_count += 1
                print(f"Ошибка отправки пользователю {user_id}: {e}")

        await message.answer(
            f"{BaseCommandsEnum.FEEDBACK_SENT.value}\n"
            f"✅ Успешно отправлено: {success_count}\n"
            f"❌ Ошибок: {error_count}"
        )
    else:
        await message.answer(BaseCommandsEnum.ACCESS_DENIED.value)


@router.message(F.text == ButtonsEnum.SEND_FEEDBACK.value)
async def process_send_feedback_button(message: Message):
    """
    Обработчик кнопки отправки обратной связи всем пользователям
    """
    await send_feedback_to_all_users(message.bot, message)


# --- GAME HANDLERS ---
@router.message(F.text == ButtonsEnum.GUESS_SOUND_BUTTON_OLD.value)
async def process_guess_sound_button(message: Message):
    """
    Этот хэндлер срабатывает на кнопку "Угадай Звук"
    """
    if message.from_user:
        await increment_user_request_count(
            message.from_user.id, message.from_user.username or ""
        )

    sound = await get_random_sound()
    if not sound:
        await message.answer("В базе пока нет звуков для игры.")
        return

    correct_name, category, file_id = sound
    decoys = await get_random_names(count=2, exclude_name=correct_name)

    options = [(correct_name, True)] + [(name, False) for name in decoys]
    random.shuffle(options)

    await message.answer_audio(audio=file_id, caption="🎧 Угадай, чей это звук?")

    await message.answer(
        text=BaseCommandsEnum.CHOOSE_ANSWER.value,
        reply_markup=await create_game_inline_kb(options, correct_answer=correct_name),
    )


@router.callback_query(GameCallbackFactory.filter())
async def process_game_answer(
        callback: CallbackQuery, callback_data: GameCallbackFactory
):
    """
    Этот хэндлер обрабатывает ответ в игре
    """
    if callback.from_user:
        await increment_user_request_count(
            callback.from_user.id, callback.from_user.username or ""
        )

    if callback_data.is_correct:
        await callback.message.edit_text(
            text=f"✅ Верно! Это {callback_data.answer}! 🎉🎉🎉"
        )
        await callback.message.answer("🎉")
    else:
        await callback.message.edit_text(
            text=f"❌ Увы, неверно. Правильный ответ - {callback_data.correct_answer}"
        )
        await callback.message.answer("🤷‍♂️")
    await callback.answer()
