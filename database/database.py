import aiosqlite

DATABASE_NAME = "database/file_database.db"
TABLE_NAME = "files_information"


async def create_table():
    async with aiosqlite.connect(DATABASE_NAME) as connection:
        await connection.execute(f'''
            CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT NOT NULL,
            file_id TEXT NOT NULL
            )
        ''')
        await connection.commit()


async def get_file_id_from_table(id: int) -> str:
    async with aiosqlite.connect(DATABASE_NAME) as connection:
        cursor = await connection.execute(f'''
            SELECT file_id 
            FROM {TABLE_NAME} 
            WHERE id = ?
        ''', (id,))
        result = await cursor.fetchone()
        return result[0] if result else None


async def get_file_name_from_table(id: int) -> str:
    async with aiosqlite.connect(DATABASE_NAME) as connection:
        cursor = await connection.execute(f'''
            SELECT file_name 
            FROM {TABLE_NAME} 
            WHERE id = ?
        ''', (id,))
        result = await cursor.fetchone()
        return result[0] if result else None


async def get_button_ids() -> list[int]:
    async with aiosqlite.connect(DATABASE_NAME) as connection:
        cursor = await connection.execute(f'''
            SELECT id 
            FROM {TABLE_NAME}
        ''')
        result = await cursor.fetchall()
        return [row[0] for row in result]


async def add_audio_to_table(file_name, file_id):
    async with aiosqlite.connect(DATABASE_NAME) as connection:
        await connection.execute(f'''
            INSERT INTO {TABLE_NAME} (file_name, file_id)
            VALUES (?, ?)
        ''', (file_name, file_id))
        await connection.commit()
