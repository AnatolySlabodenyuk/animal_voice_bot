import aiosqlite
from config_data.config import Config, load_config

config: Config = load_config()

DATABASE_NAME = config.tg_bot.database_path

SOUNDS_TABLE_NAME = "sounds_information"
IMAGES_TABLE_NAME = "images_information"

USER_STATS_TABLE = "user_stats"
TOP_USER_REQUESTS_COUNT = int(config.tg_bot.top_user_requests_count)


# --- OPTIMIZE ---
async def create_media_table(table_name, database_name=DATABASE_NAME):
    async with aiosqlite.connect(database_name) as connection:
        await connection.execute(f'''
            CREATE TABLE IF NOT EXISTS {table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT NOT NULL,
            category TEXT NOT NULL,
            file_id TEXT NOT NULL
            )
        ''')
        await connection.commit()


async def add_to_media_table(file_name: str, category: str, file_id: str, table_name, database_name=DATABASE_NAME):
    async with aiosqlite.connect(database_name) as connection:
        await connection.execute(f'''
            INSERT INTO {table_name} (file_name, category, file_id)
            VALUES (?, ?, ?)
        ''', (file_name, category, file_id))
        await connection.commit()


# --- SOUNDS INF ---
async def create_sounds_table():
    await create_media_table(table_name=SOUNDS_TABLE_NAME)


async def get_audio_file_id_from_table(file_name: str) -> str | None:
    async with aiosqlite.connect(DATABASE_NAME) as connection:
        cursor = await connection.execute(f'''
            SELECT file_id 
            FROM {SOUNDS_TABLE_NAME} 
            WHERE file_name = ?
        ''', (file_name,))
        result = await cursor.fetchone()
        return result[0] if result else None


async def get_audio_file_name_from_table(category: str) -> list[str]:
    async with aiosqlite.connect(DATABASE_NAME) as connection:
        cursor = await connection.execute(f'''
            SELECT file_name 
            FROM {SOUNDS_TABLE_NAME}
            WHERE category = ?
        ''', (category,))
        result = await cursor.fetchall()
        return [row[0] for row in result]


async def add_audio_to_table(file_name: str, category: str, file_id: str):
    await add_to_media_table(
        file_name=file_name,
        category=category,
        file_id=file_id,
        table_name=SOUNDS_TABLE_NAME
    )


# --- IMAGES INF ---
async def create_images_table():
    await create_media_table(table_name=IMAGES_TABLE_NAME)


async def get_image_file_id_from_table(file_name: str) -> str | None:
    async with aiosqlite.connect(DATABASE_NAME) as connection:
        cursor = await connection.execute(f'''
            SELECT file_id 
            FROM {IMAGES_TABLE_NAME} 
            WHERE file_name = ?
        ''', (file_name,))
        result = await cursor.fetchone()
        return result[0] if result else None


async def add_image_to_table(file_name: str, category: str, file_id: str):
    await add_to_media_table(
        file_name=file_name,
        category=category,
        file_id=file_id,
        table_name=IMAGES_TABLE_NAME
    )


# --- USER STATS ---
async def create_user_stats_table():
    async with aiosqlite.connect(DATABASE_NAME) as connection:
        await connection.execute(f'''
            CREATE TABLE IF NOT EXISTS {USER_STATS_TABLE} (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                requests_count INTEGER DEFAULT 0,
                last_request TIMESTAMP
            )
        ''')
        await connection.commit()


async def increment_user_request_count(user_id: int, username: str):
    async with aiosqlite.connect(DATABASE_NAME) as connection:
        await connection.execute(f'''
            INSERT INTO {USER_STATS_TABLE} (user_id, username, requests_count, last_request)
            VALUES (?, ?, 1, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                requests_count = requests_count + 1,
                username = excluded.username,
                last_request = CURRENT_TIMESTAMP
        ''', (user_id, username))
        await connection.commit()


async def get_top_users_stats(limit: int = 50):
    async with aiosqlite.connect(DATABASE_NAME) as connection:
        cursor = await connection.execute(f'''
            SELECT user_id, username, requests_count, last_request
            FROM {USER_STATS_TABLE}
            WHERE requests_count >= {TOP_USER_REQUESTS_COUNT}
            ORDER BY requests_count DESC, last_request DESC
            LIMIT ?
        ''', (limit,))
        return await cursor.fetchall()


async def get_all_users():
    """Получить всех пользователей из базы данных"""
    async with aiosqlite.connect(DATABASE_NAME) as connection:
        cursor = await connection.execute(f'''
            SELECT user_id, username
            FROM {USER_STATS_TABLE}
        ''')
        return await cursor.fetchall()
