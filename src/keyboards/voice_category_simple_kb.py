from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from lexicon.voice_types_enum import VoiceCategoryEnum

# ------- Создаем клавиатуру через ReplyKeyboardBuilder -------
# Создаем кнопки
button_animals: KeyboardButton = KeyboardButton(
    text=VoiceCategoryEnum.animals.value
)

button_transport: KeyboardButton = KeyboardButton(
    text=VoiceCategoryEnum.transport.value
)

button_objects: KeyboardButton = KeyboardButton(
    text=VoiceCategoryEnum.objects.value
)

# Инициализируем билдер для клавиатуры с кнопками:
voice_category_simple_kb_builder = ReplyKeyboardBuilder()

# Добавляем кнопки в билдер с аргументом width=1 (количество кнопок в ряду)
voice_category_simple_kb_builder.row(
    button_animals,
    button_transport,
    button_objects,
    width=1
)

# Создаем клавиатуру с кнопками:
voice_category_simple_kb: ReplyKeyboardMarkup = voice_category_simple_kb_builder.as_markup(
    # one_time_keyboard=True,
    resize_keyboard=True
)
