from aiogram import F, Router
from aiogram.types import Message
from aiogram.filters import Command
from keyboards.base_kb import base_kb
from keyboards.admin_kb import admin_kb
from lexicon.base_commands_enum import BaseCommandsEnum
from lexicon.buttons_enum import ButtonsEnum
from database.database import add_audio_to_table

# Инициализируем роутер уровня модуля
router = Router()


# Этот хэндлер срабатывает на команду /admin
@router.message(Command(commands="admin"))
async def process_admin_command(message: Message):
    await message.answer(
        text=BaseCommandsEnum.ADMIN.value,
        reply_markup=admin_kb
    )


# Этот хэндлер срабатывает на кнопку загрузить звук
@router.message(F.text == ButtonsEnum.AUDIO_UPLOAD.value)
async def process_audio_upload_button(message: Message):
    await message.answer(text=BaseCommandsEnum.AUDIO_UPLOAD.value)


# State for handling name input
class Form:
    state_file_id = None


# Этот хэндлер срабатывает загрузку аудио
@router.message(F.audio)
async def process_upload_audio(message: Message):
    file_id = message.audio.file_id
    await message.reply(text=BaseCommandsEnum.SET_ANIMAL_NAME.value)
    Form.state_file_id = file_id


# Этот хэндлер срабатывает на задание имени для аудио
@router.message(lambda message: Form.state_file_id is not None)
async def process_set_file_name(message: Message):
    file_name = message.text
    file_id = Form.state_file_id
    await add_audio_to_table(file_name, file_id)
    Form.state_file_id = None
    await message.answer(
        text=f"Аудиофайл сохранен с именем {file_name}!",
        reply_markup=base_kb
    )
