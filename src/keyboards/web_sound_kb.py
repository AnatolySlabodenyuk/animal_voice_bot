from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services.web_sound_search import WebSound


class WebSoundCallback(CallbackData, prefix="web_sound"):
    token: str
    index: int


def create_web_sound_kb(sounds: list[WebSound], token: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for index, sound in enumerate(sounds):
        builder.button(
            text=f"{index + 1}. {sound.title[:55]} · {sound.source}",
            callback_data=WebSoundCallback(token=token, index=index),
        )
    builder.adjust(1)
    return builder.as_markup()
