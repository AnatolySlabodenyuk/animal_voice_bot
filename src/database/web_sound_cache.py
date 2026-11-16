import aiosqlite


class WebSoundCache:
    """Persistent Telegram file IDs; IDs cannot be shared between bots."""

    def __init__(self, database_path: str, bot_id: int):
        self.database_path = database_path
        self.bot_id = bot_id

    async def initialize(self):
        async with aiosqlite.connect(self.database_path) as connection:
            await connection.execute('''
                CREATE TABLE IF NOT EXISTS web_sound_cache (
                    bot_id INTEGER NOT NULL,
                    sound_key TEXT NOT NULL,
                    file_id TEXT NOT NULL,
                    PRIMARY KEY (bot_id, sound_key)
                )
            ''')
            await connection.commit()

    async def get(self, sound_key: str) -> str | None:
        async with aiosqlite.connect(self.database_path) as connection:
            async with connection.execute(
                "SELECT file_id FROM web_sound_cache WHERE bot_id = ? AND sound_key = ?",
                (self.bot_id, sound_key),
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None

    async def put(self, sound_key: str, file_id: str):
        async with aiosqlite.connect(self.database_path) as connection:
            await connection.execute('''
                INSERT INTO web_sound_cache (bot_id, sound_key, file_id)
                VALUES (?, ?, ?)
                ON CONFLICT(bot_id, sound_key) DO UPDATE SET file_id = excluded.file_id
            ''', (self.bot_id, sound_key, file_id))
            await connection.commit()

    async def delete(self, sound_key: str):
        async with aiosqlite.connect(self.database_path) as connection:
            await connection.execute(
                "DELETE FROM web_sound_cache WHERE bot_id = ? AND sound_key = ?",
                (self.bot_id, sound_key),
            )
            await connection.commit()
