import sqlite3
import aiosqlite
from contextlib import closing

DATABASE_NAME = "database/file_database.db"
table_name = "files_information"


async def create_table():
    async with aiosqlite.connect(DATABASE_NAME) as connection:
        await connection.execute(f'''
            CREATE TABLE IF NOT EXISTS {table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT NOT NULL,
            file_id TEXT NOT NULL
            )
        ''')
        await connection.commit()


async def get_file_id_from_table(file_name: str):
    async with aiosqlite.connect(DATABASE_NAME) as connection:
        cursor = await connection.execute(f'''
            SELECT file_id 
            FROM {table_name} 
            WHERE file_name = ?
        ''', (file_name,))
        result = await cursor.fetchone()
        return result


async def get_file_name_from_table(id: int):
    async with aiosqlite.connect(DATABASE_NAME) as connection:
        cursor = await connection.execute(f'''
            SELECT file_name 
            FROM {table_name} 
            WHERE id = ?
        ''', (id,))
        result = await cursor.fetchone()
        return result


async def add_audio_to_table(file_name, file_id):
    async with aiosqlite.connect(DATABASE_NAME) as connection:
        await connection.execute(f'''
            INSERT INTO {table_name} (file_name, file_id)
            VALUES (?, ?)
        ''', (file_name, file_id))
        await connection.commit()
