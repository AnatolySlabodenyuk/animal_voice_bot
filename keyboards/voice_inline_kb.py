import asyncio

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData

from database.database import get_file_name_from_table
from lexicon.voice_types_enum import VoiceCategoryEnum


class AnimalsCallbackFactory(CallbackData, prefix="animals"):
    button_id: int


class VoiceTypesCallbackFactory(CallbackData, prefix="voice_type"):
    voice_type: str


class VoiceNamesCallbackFactory(CallbackData, prefix="voice_name"):
    voice_name: str


async def create_voice_category_inline_kb() -> InlineKeyboardMarkup:
    """
    Функция для формирования инлайн-клавиатуры с категориями звуков
    """
    voice_types_kb_builder = InlineKeyboardBuilder()
    voice_types_list = [product.value for product in VoiceCategoryEnum]

    for voice_type in voice_types_list:
        voice_types_kb_builder.button(
            text=voice_type,
            callback_data=VoiceTypesCallbackFactory(
                voice_type=voice_type
            )
        )

    voice_types_kb_builder.adjust(1)

    return voice_types_kb_builder.as_markup()


async def create_voice_names_inline_kb(voice_names_list: list[str]) -> InlineKeyboardMarkup:
    """
    Функция для формирования инлайн-клавиатуры с типом животного
    """
    voice_names_kp_builder = InlineKeyboardBuilder()

    for voice_name in voice_names_list:
        voice_names_kp_builder.button(
            text=voice_name,
            callback_data=VoiceNamesCallbackFactory(
                voice_name=voice_name
            )
        )

    voice_names_kp_builder.adjust(1)

    return voice_names_kp_builder.as_markup()


async def main():
    result = await create_voice_names_inline_kb(
        voice_names_list=await get_file_name_from_table(
            category=VoiceCategoryEnum.transport.value
        )
    )
    print(result)  # Выведите результат или обработайте его


if __name__ == '__main__':
    asyncio.run(main())
