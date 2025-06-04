import sqlite3
from datetime import datetime

# Функция для подключения к базе данных
def connect_db(db_name='mood_base.db'):
    conn = sqlite3.connect(db_name, check_same_thread=False)
    return conn

# Функция для создания таблицы, если ее еще нет
def create_table(conn):
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS moods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            mood TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    ''')
    conn.commit()

# Функция для добавления записи о настроении
def add_mood(conn, user_id, mood):
    cursor = conn.cursor()
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute('''
        INSERT INTO moods (user_id, mood, timestamp)
        VALUES (?, ?, ?)
    ''', (user_id, mood, timestamp))
    conn.commit()

# Пример использования
if __name__ == '__main__':
    conn = connect_db()
    create_table(conn)
    # # Пример добавления записи
    # add_mood(conn, user_id=123456789, mood='отличное')
    # conn.close()