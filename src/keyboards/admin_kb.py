from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from lexicon.buttons_enum import ButtonsEnum

# ------- Создаем клавиатуру через ReplyKeyboardBuilder -------
# Создаем кнопки
button_audio_upload: KeyboardButton = KeyboardButton(
    text=ButtonsEnum.AUDIO_UPLOAD.value
)

# Инициализируем билдер для клавиатуры с кнопками:
admin_kb_builder = ReplyKeyboardBuilder()

# Добавляем кнопки в билдер с аргументом width=1 (количество кнопок в ряду)
admin_kb_builder.row(
    button_audio_upload,
    width=1
)

# Создаем клавиатуру с кнопками:
admin_kb: ReplyKeyboardMarkup = admin_kb_builder.as_markup(
    # one_time_keyboard=True,
    resize_keyboard=True
)
