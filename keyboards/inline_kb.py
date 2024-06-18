from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from lexicon.buttons_enum import InlineButtonsEnum, CallbackDataEnum

# ------- Создаем клавиатуру через ReplyKeyboardBuilder -------

# Создаем инлайн-кнопки с выбором животных
inline_button_cat: InlineKeyboardButton = InlineKeyboardButton(
    text=InlineButtonsEnum.CAT.value,
    callback_data=CallbackDataEnum.INLINE_BUTTON_CAT_PRESSED.value
)

inline_button_dog: InlineKeyboardButton = InlineKeyboardButton(
    text=InlineButtonsEnum.DOG.value,
    callback_data=CallbackDataEnum.INLINE_BUTTON_DOG_PRESSED.value
)

inline_button_сhewbacca: InlineKeyboardButton = InlineKeyboardButton(
    text=InlineButtonsEnum.CHEWBACCA.value,
    callback_data=CallbackDataEnum.INLINE_BUTTON_CHEWBACCA_PRESSED.value
)

# Инициализируем билдер для клавиатуры с инлайн-кнопками:
inline_kb_builder = InlineKeyboardBuilder()


# Добавляем кнопки в билдер с аргументом width=1 (количество кнопок в ряду)
inline_kb_builder.row(inline_button_cat, inline_button_dog,
                      inline_button_сhewbacca, width=1)

# Создаем клавиатуру с кнопками:
inline_kb: InlineKeyboardMarkup = inline_kb_builder.as_markup(
    # one_time_keyboard=True,
    resize_keyboard=True
)
