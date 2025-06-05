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
            timestamp TEXT NOT NULL,
            mood_id INTEGER NOT NULL
        )
    ''')
    conn.commit()

# Функция для добавления записи о настроении
def add_mood(conn, user_id, mood, mood_id):
    cursor = conn.cursor()
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute('''
        INSERT INTO moods (user_id, mood, timestamp, mood_id)
        VALUES (?, ?, ?, ?)
    ''', (user_id, mood, timestamp, mood_id))
    conn.commit()

def get_all_moods(conn):
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, mood, timestamp, mood_id FROM moods')
    rows = cursor.fetchall()
    return rows

# Пример использования
# if __name__ == '__main__':
#     conn = connect_db()
#     create_table(conn)
#     all_moods = get_all_moods(conn)
#     for record in all_moods:
#         print(f'Mood: {record[1]}, Mood ID: {record[3]}')
#     conn.close()
    # # Пример добавления записи
    # add_mood(conn, user_id=123456789, mood='отличное')
    # conn.close()