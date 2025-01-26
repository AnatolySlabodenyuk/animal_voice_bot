from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from lexicon.buttons_enum import ButtonsEnum

# ------- Создаем клавиатуру через ReplyKeyboardBuilder -------
# Создаем кнопки
button_restart: KeyboardButton = KeyboardButton(
    text=ButtonsEnum.RESTART_BUTTON.value
)

voice_category_choose: KeyboardButton = KeyboardButton(
    text=ButtonsEnum.VOICE_CATEGORY_CHOOSE_BUTTON.value
)

button_help: KeyboardButton = KeyboardButton(
    text=ButtonsEnum.HELP_BUTTON.value
)

button_search_in_web: KeyboardButton = KeyboardButton(
    text=ButtonsEnum.SEARCH_IN_WEB.value
)

# Инициализируем билдер для клавиатуры с кнопками:
base_kb_builder = ReplyKeyboardBuilder()

# Добавляем кнопки в билдер с аргументом width=1 (количество кнопок в ряду)
base_kb_builder.row(
    button_restart,
    voice_category_choose,
    button_help,
    button_search_in_web,
    width=1
)

# Создаем клавиатуру с кнопками:
base_kb: ReplyKeyboardMarkup = base_kb_builder.as_markup(
    # one_time_keyboard=True,
    resize_keyboard=True
)
