from dataclasses import dataclass
from environs import Env


@dataclass
class TgBot:
    token: str  # Токен для доступа к телеграм-боту
    admin_user_id: str
    search_result_count: str
    database_path: str
    top_user_requests_count: str
    feedback_message: str
    webapp_url: str


@dataclass
class Config:
    tg_bot: TgBot


def load_config(path: str | None = None) -> Config:
    env: Env = Env()
    env.read_env(path)
    return Config(
        tg_bot=TgBot(
            token=env("BOT_TOKEN"),
            admin_user_id=env("BOT_ADMIN_USER_ID"),
            search_result_count=env("SEARCH_RESULT_COUNT"),
            database_path=env("DATABASE_PATH"),
            top_user_requests_count=env("TOP_USER_REQUESTS_COUNT"),
            feedback_message=env("FEEDBACK_MESSAGE"),
            webapp_url=env("WEBAPP_URL")

        )
    )
