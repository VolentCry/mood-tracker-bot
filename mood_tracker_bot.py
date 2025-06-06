import logging
import asyncio
from datetime import datetime, time

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types.input_file import FSInputFile

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from dotenv import load_dotenv
import os

from add_mood_to_db import *
from plot_visualisaion import make_and_save_plot

# --- Конфигурация ---
load_dotenv("config.env")
BOT_TOKEN = os.getenv('TOKEN')
ADMIN_ID = os.getenv('ADMINID')

conn = connect_db()
conn2 = connect_db(db_name="users.db")


# --- Логирование ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Хранилище данных (в памяти) ---
# user_data = { user_id: {"moods": [(timestamp, mood_text)], "notification_time": "HH:MM"} }
user_data = {}
user_time_zone = None

# --- Машина состояния ---
class UserStates(StatesGroup):
    waiting_for_notification_time = State()

# --- Инициализация ---
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
bot = Bot(token=BOT_TOKEN)
scheduler = AsyncIOScheduler(timezone="Europe/Moscow")

# --- Клавиатуры ---
def get_main_menu_keyboard():
    buttons = [
        [InlineKeyboardButton(text="📝 Запись настроения", callback_data="record_mood")],
        [InlineKeyboardButton(text="⏰ Настройка времени", callback_data="set_notification_time")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_mood_selection_keyboard():
    buttons = [
        [InlineKeyboardButton(text="😊 Положительное", callback_data="mood_positive")],
        [InlineKeyboardButton(text="😩 Уставшее", callback_data="mood_tired")],
        [InlineKeyboardButton(text="😢 Грустное", callback_data="mood_sad")],
        [InlineKeyboardButton(text="😠 Злое", callback_data="mood_angry")],
        [InlineKeyboardButton(text="🤩 Восхитительное", callback_data="mood_delighted")],
        [InlineKeyboardButton(text="😖 Раздражённое", callback_data="mood_irritated")],
        [InlineKeyboardButton(text="🙂 Спокойное", callback_data="mood_calm")],
        [InlineKeyboardButton(text="⚡️ Энергичное", callback_data="mood_energetic")],
        [InlineKeyboardButton(text="😰 Тревожное", callback_data="mood_anxious")],
        [InlineKeyboardButton(text="🤯 Воодушевлённое", callback_data="mood_inspired")],
        [InlineKeyboardButton(text="🫠 Скучающее", callback_data="mood_bored")],
        [InlineKeyboardButton(text="🥰 Влюблённое", callback_data="mood_loving")],
        [InlineKeyboardButton(text="🥱 Безразличное", callback_data="mood_indifferent")],
        [InlineKeyboardButton(text="😱 Испуганное", callback_data="mood_scared")],
        [InlineKeyboardButton(text="😎 Гордое", callback_data="mood_proud")],
        [InlineKeyboardButton(text="😒 Завистливое", callback_data="mood_envious")],
        [InlineKeyboardButton(text="😓 Растерянное", callback_data="mood_confused")],
        [InlineKeyboardButton(text="😏 Игривое", callback_data="mood_playful")],
        [InlineKeyboardButton(text="🤔 Сосредоточенное", callback_data="mood_focused")],
        [InlineKeyboardButton(text="🤧 Болезненное", callback_data="mood_sick")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# --- Функции планировщика ---
async def send_mood_prompt(user_id: int):
    try:
        await bot.send_message(
            user_id,
            "👋 Привет! Давай зафиксируем твоё настроение на сегодня.", reply_markup=get_mood_selection_keyboard() # или так, если хотите сразу выбор
        )
        logger.info(f"Отправлено напоминание пользователю {user_id}")
    except Exception as e:
        logger.error(f"Не удалось отправить напоминание пользователю {user_id}: {e}")
        # Если пользователь заблокировал бота, то он удаляется из расписания
        if "bot was blocked by the user" in str(e).lower():
            remove_schedule(user_id)
            if user_id in user_data:
                del user_data[user_id]
            logger.info(f"Пользователь {user_id} заблокировал бота. Задание и данные удалены.")


def schedule_mood_prompt(user_id: int, time_str: str):
    """Планирует или перепланирует ежедневное напоминание для пользователя."""
    try:
        hour, minute = map(int, time_str.split(':'))
        job_id = f"mood_prompt_{user_id}"

        # Удаляем старое задание, если оно есть
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)
            logger.info(f"Старое задание {job_id} удалено.")

        # Добавляем новое задание
        scheduler.add_job(
            send_mood_prompt,
            trigger=CronTrigger(hour=hour, minute=minute, timezone="Europe/Moscow"), # Укажите ваш часовой пояс
            args=[user_id],
            id=job_id,
            replace_existing=True
        )
        logger.info(f"Задание {job_id} установлено на {time_str} для пользователя {user_id}")
        return True
    except ValueError:
        logger.error(f"Неверный формат времени: {time_str} для пользователя {user_id}")
        return False
    except Exception as e:
        logger.error(f"Ошибка при планировании задания для {user_id} на {time_str}: {e}")
        return False

def remove_schedule(user_id: int):
    job_id = f"mood_prompt_{user_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        logger.info(f"Задание {job_id} удалено для пользователя {user_id}.")

# --- Обработчики команд ---
@dp.message(CommandStart())
async def send_welcome(message: Message):
    user_id = message.from_user.id
    if user_id not in user_data:
        user_data[user_id] = {"moods": [], "notification_time": None}
    await message.answer(
        f"👋 Привет, {message.from_user.full_name}!\n"
        "Я твой личный дневник настроения. Давай зафиксируем твоё настроение на сегодня.",
        reply_markup=get_main_menu_keyboard()
    )

@dp.message(Command("menu"))
async def command_menu(message: Message):
    await message.answer(
        "Вот основное меню:",
        reply_markup=get_main_menu_keyboard()
    )

# --- Обработчики колбэков ---
@dp.callback_query(lambda c: c.data == "record_mood")
async def process_record_mood_callback(callback_query: CallbackQuery):
    await callback_query.message.edit_text(
        "Выбери какое у тебя сегодня настроение:",
        reply_markup=get_mood_selection_keyboard()
    )
    await callback_query.answer()

@dp.callback_query(lambda c: c.data.startswith("mood_"))
async def process_mood_selection_callback(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    mood_choice_code = callback_query.data.split("_")[1]

    mood_map = {
        "positive": "Положительное 😊",
        "tired": "Усталое 😩",
        "sad": "Грустное 😢",
        "angry": "Злое 😠",
        "delighted": "Восхитительное 🤩",
        "irritated": "Раздражённое 😖",
        "calm": "Спокойное 🙂",
        "energetic": "Энергичное ⚡️",
        "anxious": "Тревожное 😰",
        "inspired": "Воодушевлённое 🤯",
        "bored": "Скучающее 🫠",
        "loving": "Влюблённое 🥰",
        "indifferent": "Безразличное 🥱",
        "scared": "Испуганное 😱",
        "proud": "Гордое 😎",
        "envious": "Завистливое 😒",
        "confused": "Растерянное 😓",
        "playful": "Игривое 😏",
        "focused": "Сосредоточенное 🤔",
        "sick": "Болезненное 🤧"
    }
    mood_text = mood_map.get(mood_choice_code, "Неизвестное")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    mood_ID = list(mood_map.keys()).index(mood_choice_code)

    if user_id not in user_data:
        user_data[user_id] = {"moods": [], "notification_time": None}

    user_data[user_id]["moods"].append((timestamp, mood_text))
    add_mood(conn, user_id=user_id, mood=mood_text, mood_id=mood_ID)
    # conn.close()

    await callback_query.message.edit_text(
        f"Настроение '{mood_text}' записано!\nСпасибо! ✨",
        reply_markup=None # Убираем кнопки после выбора
    )
    await callback_query.answer(text=f"Записано: {mood_text}")
    logger.info(f"Пользователь {user_id} записал настроение: {mood_text}")

    # Опционально: вернуть главное меню через пару секунд
    await callback_query.message.answer(
        "Что дальше?",
        reply_markup=get_main_menu_keyboard()
    )


@dp.callback_query(lambda c: c.data == "set_notification_time")
async def process_set_time_callback(callback_query: CallbackQuery, state: FSMContext):
    await state.set_state(UserStates.waiting_for_notification_time)
    current_time_info = ""
    if user_data.get(callback_query.from_user.id, {}).get("notification_time"):
        current_time_info = f"\nТекущее установленное время: {user_data[callback_query.from_user.id]['notification_time']}"

    await callback_query.message.edit_text(
        "🕒 В какое время (в формате ЧЧ:ММ, например, 09:30 или 18:05) "
        "ты хотел бы получать напоминание о записи настроения?"
        f"{current_time_info}\n\nДля отмены введите /cancel.",
        reply_markup=None
    )
    await callback_query.answer()

# --- Обработчик ввода времени для уведомлений ---
@dp.message(UserStates.waiting_for_notification_time)
async def process_time_input(message: Message, state: FSMContext):
    user_id = message.from_user.id
    time_str = message.text.strip()

    if time_str.lower() == "/cancel":
        await state.clear()
        await message.answer("Настройка времени отменена.", reply_markup=get_main_menu_keyboard())
        return

    try:
        # Простая валидация формата времени
        parsed_time = time.fromisoformat(time_str) # HH:MM или HH:MM:SS
        valid_time_str = parsed_time.strftime("%H:%M") # Приводим к HH:MM
        user_time = valid_time_str # Время, котолрое отобразиться у юзера в сообщении

        plus_to_time = get_time_zone(conn2, user_id)

        # Перевод всего времени к Московскому
        if plus_to_time != 0 or plus_to_time != None:
            new_hour = int(valid_time_str[:2]) - int(eval(plus_to_time))
            if 0 <= new_hour <= 9: 
                valid_time_str = "0" + str(new_hour) + valid_time_str[2:]
            elif new_hour < 0: 
                new_hour = 24 - abs(new_hour)
                valid_time_str = str(new_hour) + valid_time_str[2:]
            else:
                valid_time_str = str(new_hour) + valid_time_str[2:]

        # Проверка на наличие пользователя в базе
        if check_user_in_table(conn=conn2, user_id=user_id) == False: # Ещё никого нет в базе
            add_user_notification(conn=conn2, user_id=user_id, time=valid_time_str, time_zone=user_time_zone)
        else:
            if user_id in check_user_in_table(conn=conn2, user_id=user_id): # Пользователь есть в базе
                update_time_notification(conn2, user_id, valid_time_str)
            else: # Пользователя нет в базе
                if user_time_zone == None:
                    add_user_notification(conn=conn2, user_id=user_id, time=valid_time_str)
                else:
                    add_user_notification(conn=conn2, user_id=user_id, time=valid_time_str, time_zone=user_time_zone)

        if schedule_mood_prompt(user_id, valid_time_str):
            await message.answer(
                f"Отлично! Я буду напоминать тебе записать настроение каждый день в {user_time}.",
                reply_markup=get_main_menu_keyboard()
            )
        else:
            await message.answer(
                "Произошла ошибка при установке времени. Пожалуйста, попробуйте еще раз.",
                reply_markup=get_main_menu_keyboard() # или кнопка "попробовать снова"
            )
        await state.clear()

    except ValueError:
        await message.answer(
            "❌ Неверный формат времени. Пожалуйста, введи время в формате ЧЧ:ММ (например, 08:00 или 21:30).\n"
            "Для отмены введите /cancel."
        )
    except Exception as e:
        logger.error(f"Ошибка при обработке времени {time_str} от {user_id}: {e}")
        await message.answer(
            "Что-то пошло не так. Попробуйте еще раз.",
            reply_markup=get_main_menu_keyboard()
        )
        await state.clear()

# --- Команда для просмотра сохраненных данных (для отладки) ---
@dp.message(Command("mydata"))
async def show_my_data(message: Message):
    all_moods = get_all_moods(conn)
    user_id = message.from_user.id
    if all_moods != []:
        data_str = f"Ваши данные:\n"
        # if user_data[user_id]["notification_time"]:
        #     data_str += f"Время уведомлений: {user_data[user_id]['notification_time']}\n"
        # else:
        #     data_str += "Время уведомлений: не установлено\n"

        data_str += "Записи настроения:\n"
        if all_moods != []:
            all_moods = get_all_moods(conn)
            five_moods = reversed(all_moods[-5:])
            for record in five_moods:
                data_str += f"  - {record[2]}: {record[1]}\n"
        else:
            data_str += "  Пока нет записей.\n"
        data_str += "Выше представлены 5 последних записей."
        await message.answer(data_str)
    else:
        await message.answer("У меня пока нет данных о вас.")

# --- Команда для просмотра отчёта настроения в виде картинки ---
@dp.message(Command("mood_plot"))
async def show_my_mood_plot(message: Message):
    year = str(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))[:4]
    months_list = ["Январь", 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
    month = months_list[int(str(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))[6:7]) - 1]
    path_to_plot = make_and_save_plot(message.from_user.id, month)
    photo = FSInputFile(path_to_plot)
    await bot.send_photo(message.chat.id, photo=photo, caption=f"Вот ваша диаграмма за {month} {year} год(а)")

def get_timezone_keyboard():
    timezones = [
        {'label': 'МСК (UTC+3)', 'offset': 0},
        {'label': 'МСК-1 (UTC+2)', 'offset': -1},
        {'label': 'МСК+1 (UTC+4)', 'offset': 1},
        {'label': 'МСК+2 (UTC+5)', 'offset': 2},
        {'label': 'МСК+3 (UTC+6)', 'offset': 3},
        {'label': 'МСК+4 (UTC+7)', 'offset': 4},
        {'label': 'МСК+5 (UTC+8)', 'offset': 5},
        {'label': 'МСК-2 (UTC+1)', 'offset': -2},
        {'label': 'МСК-3 (UTC+0)', 'offset': -3},
    ]
    keyboard = [ [InlineKeyboardButton(text=tz['label'], callback_data=f"timezone_{tz['offset']}")] for tz in timezones]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@dp.message(Command("set_timezone"))
async def send_timezone_keyboard(message: Message):
    await message.answer("Пожалуйста, выберите ваш часовой пояс относительно МСК:", reply_markup=get_timezone_keyboard())

@dp.callback_query(lambda c: c.data.startswith("timezone_"))
async def handle_timezone_choice(callback: CallbackQuery):
    global user_time_zone
    offset = int(callback.data.split("_")[1])
    user_time_zone = f"{offset:+d}"
    await callback.answer(f"Вы выбрали часовой пояс: МСК{offset:+d}")
    await callback.message.edit_text(f"Вы выбрали часовой пояс: МСК{offset:+d}")

    # Проверка на наличие пользователя в базе
    user_id = callback.from_user.id
    if check_user_in_table(conn=conn2, user_id=user_id) == False: # Ещё никого нет в базе
        pass
    else:
        if user_id in check_user_in_table(conn=conn2, user_id=user_id): # Пользователь есть в базе
            update_time_zone(conn2, user_id, user_time_zone)

# --- Главная функция ---
async def main():
    # Запуск планировщика
    scheduler.start()
    logger.info("Планировщик запущен.")

    # Запуск бота
    logger.info("Бот запускается...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())