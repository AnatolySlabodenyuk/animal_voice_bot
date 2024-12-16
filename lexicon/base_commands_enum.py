import enum


class BaseCommandsEnum(enum.Enum):
    START = "Привет!\n\nЯ бот с голосами животных!\n\n"
    HELP = "Здесь будет инструкция..."
    ADMIN = "Добро пожаловать в админку!🌈"
    AUDIO_UPLOAD = "Отправь аудио со звуком животного"
    SET_ANIMAL_NAME = "Пожалуйста, введите название животного"
    ANIMAL_CHOOSE_BUTTON = "Это список животных. Выбери любое!"
    SEARCH_IN_WEB_BUTTON = "Какой звук хочешь найти?"
    OTHER_ANSWER = "Извини, увы, это сообщение мне непонятно..."
