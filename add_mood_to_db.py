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

def add_user_notification(conn, time: str, user_id: int, time_zone="МСК"):
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO users (user_id, notification_time, time_zone)
        VALUES (?, ?, ?)
    ''', (user_id, time, time_zone))
    conn.commit()

def check_user_in_table(conn, user_id: int):
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, notification_time, time_zone FROM users')
    rows = cursor.fetchall()
    users_list = []
    if rows == []:
        return False
    else: 
        for i in rows:
            users_list.append(i[0])
    return users_list


def get_all_moods(conn):
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, mood, timestamp, mood_id FROM moods')
    rows = cursor.fetchall()
    return rows

def update_time_notification(conn, user_id, new_time: str):
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE users SET notification_time = ? WHERE user_id = ?',
        (new_time, user_id)
    )
    conn.commit()

def update_time_zone(conn, user_id, new_timezone: str):
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE users SET time_zone = ? WHERE user_id = ?',
        (new_timezone, user_id)
    )
    conn.commit()

def get_time_zone(conn, user_id: int):
    """Извлекает значения врмеенного пояса пользователя"""
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, notification_time, time_zone FROM users')
    rows = cursor.fetchall()
    for i in rows:
        if i[0] == user_id: return i[2]


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

