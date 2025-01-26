import aiosqlite

DATABASE_NAME = "database/sounds_database.db"
TABLE_NAME = "sounds_information"


async def create_table():
    async with aiosqlite.connect(DATABASE_NAME) as connection:
        await connection.execute(f'''
            CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT NOT NULL,
            category TEXT NOT NULL,
            file_id TEXT NOT NULL
            )
        ''')
        await connection.commit()


async def get_audio_file_id_from_table(file_name: str) -> str:
    async with aiosqlite.connect(DATABASE_NAME) as connection:
        cursor = await connection.execute(f'''
            SELECT file_id 
            FROM {TABLE_NAME} 
            WHERE file_name = ?
        ''', (file_name,))
        result = await cursor.fetchone()
        return result[0] if result else None


async def get_file_name_from_table(category: str) -> list[str]:
    async with aiosqlite.connect(DATABASE_NAME) as connection:
        cursor = await connection.execute(f'''
            SELECT file_name 
            FROM {TABLE_NAME}
            WHERE category = ?
        ''', (category,))
        result = await cursor.fetchall()
        return [row[0] for row in result]


async def add_audio_to_table(file_name: str, category: str, file_id: str):
    async with aiosqlite.connect(DATABASE_NAME) as connection:
        await connection.execute(f'''
            INSERT INTO {TABLE_NAME} (file_name, category, file_id)
            VALUES (?, ?, ?)
        ''', (file_name, category, file_id))
        await connection.commit()
