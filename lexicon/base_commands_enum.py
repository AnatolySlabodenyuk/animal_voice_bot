import enum


class BaseCommandsEnum(enum.Enum):
    START = "Привет!\n\nЯ эхо-бот для демонстрации работы роутеров!\n\n"
    HELP = "Здесь будет инструкция..."
    AUDIO_UPLOAD = "Отправь аудио со звуком животного"
    ANIMAL_CHOOSE_BUTTON = "Это список животных. Выбери любое!"
    OTHER_ANSWER = "Извини, увы, это сообщение мне непонятно..."
