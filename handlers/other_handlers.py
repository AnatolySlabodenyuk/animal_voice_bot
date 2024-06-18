from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from lexicon.base_commands_enum import BaseCommandsEnum

# Инициализируем роутер уровня модуля
router = Router()


# Хэндлер для сообщений, которые не попали в другие хэндлеры
@router.message()
async def send_answer(message: Message):
    await message.answer(
        text=BaseCommandsEnum.OTHER_ANSWER.value
    )
