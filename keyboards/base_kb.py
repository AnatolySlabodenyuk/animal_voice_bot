from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from lexicon.buttons_enum import Buttons


# ------- Создаем клавиатуру через ReplyKeyboardBuilder -------
# Создаем кнопки
button_restart: KeyboardButton = KeyboardButton(
    text=Buttons.RESTART_BUTTON.value
)

button_animal_choose: KeyboardButton = KeyboardButton(
    text=Buttons.ANIMAL_CHOOSE_BUTTON.value
)

button_help: KeyboardButton = KeyboardButton(
    text=Buttons.HELP_BUTTON.value
)

# Инициализируем билдер для клавиатуры с кнопками:
base_kb_builder = ReplyKeyboardBuilder()

# Добавляем кнопки в билдер с аргументом width=1 (количество кнопок в ряду)
base_kb_builder.row(button_restart, button_animal_choose, button_help, width=1)

# Создаем клавиатуру с кнопками:
base_kb: ReplyKeyboardMarkup = base_kb_builder.as_markup(
    # one_time_keyboard=True,
    resize_keyboard=True
)
