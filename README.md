# Telegram бот для поиска звуков

Этот проект — это телеграм-бот, созданный с использованием библиотеки [aiogram](https://docs.aiogram.dev/). Бот позволяет находить звуки животных и работает в двух режимах:  
1. **Режим поиска по локальной базе данных**  
2. **Режим поиска в интернете (сайт [zvukogram](https://zvukogram.com/))**  

Кроме того, пользователи могут загружать свои звуки в локальную базу данных для дальнейшего использования.  

---

## 📜 Основные возможности  
- **Поиск звуков животных**  
  - Быстрый поиск в локальной базе данных (возможность выбрать из сущесвующих).  
  - Поиск звуков на сайте zvukogram (поиск по любым ключевым словам)
- **Управление базой данных**  
  - Возможность загрузки собственных звуков в локальную базу данных.  

---

## 🛠️ Установка и запуск  

### Требования  
- Python 3.12 или выше  

### Установка  
1. Клонировать репозиторий:  
   ```bash
   git clone https://github.com/ваш-пользователь/ваш-репозиторий.git
   cd ваш-репозиторий
   ```

2. Создать файл .env с токеном бота
    ```bash
    BOT_TOKEN=Your_token
    ```

3. Установить зависимости и запустить файл main
    ```bash
    pip install -r requirements.txt
    python main.py
    ```

## 📚 Использование
1. Выбор из локальной базы звуков:
Выберете в боте название животного, чтобы получить соответствующий звук.

1. Загрузка звуков:
Отправьте файл в бот с описанием, чтобы добавить его в локальную базу данных.

1. Режим поиска:
Укажите в поиске необходимый звук для поиска в сети

