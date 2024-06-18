from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from lexicon.buttons_enum import InlineButtonsEnum, CallbackDataEnum
from database.database import get_file_name_from_table
from aiogram.filters.callback_data import CallbackData


class AnimalsCallbackFactory(CallbackData, prefix="animals"):
    button_id: int


# Функция для формирования инлайн-клавиатуры на лету
async def create_inline_kb(width: int, button_ids: list[int]) -> InlineKeyboardMarkup:
    # Инициализируем билдер
    kb_builder = InlineKeyboardBuilder()
    # Инициализируем список для кнопок
    buttons: list[InlineKeyboardButton] = []

    # Заполняем список кнопками из идентификаторов button_ids
    for button_id in button_ids:
        buttons.append(
            InlineKeyboardButton(
                text=await get_file_name_from_table(button_id),
                callback_data=AnimalsCallbackFactory(
                    button_id=button_id
                ).pack()
            )
        )

    # Распаковываем список с кнопками в билдер методом row c параметром width
    kb_builder.row(*buttons, width=width)

    # Возвращаем объект инлайн-клавиатуры
    return kb_builder.as_markup()
