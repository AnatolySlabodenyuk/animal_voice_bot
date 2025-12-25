from aiogram import Router
from aiogram.types import Message

from lexicon.base_commands_enum import BaseCommandsEnum

router = Router()


@router.message()
async def send_answer(message: Message):
    """
    Хэндлер для сообщений, которые не попали в другие хэндлеры
    """
    await message.answer(
        text=BaseCommandsEnum.OTHER_ANSWER.value
    )
