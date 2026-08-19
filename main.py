import os
import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.utils import keyboard
from dotenv import load_dotenv
import aiosqlite

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN не найден в .env")

bot = Bot(token=TOKEN)
dp = Dispatcher()

DB_PATH = "training.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS one_off_trainings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                training_name TEXT NOT NULL,
                start_time TEXT NOT NULL
            )
        """)
        await db.commit()
    print("✅База данных готова")

async def add_one_off_training(user_id: int, date: str, name: str, time: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO one_off_trainings (user_id, date, training_name, start_time) VALUES (?, ?, ?, ?)""", (user_id, date, name, time)
        )

        await db.commit()  #commit - Сохранить изменения. Без этого запись не появится в базе.

@dp.message(Command("add"))
async def cmd_add(message: types.Message):
    args = message.text.split(maxsplit=3)

# split(maxsplit=3) разбивает строку на части. 3 - разделить на первые 3 раза.

    if len(args) < 4:
        await message.answer(
            "❌ Неверный формат.\n"
            "Используй: /add ГГГГ-ММ-ДД Название_тренировки Время\n"
            "Пример: /add 2026-08-25 Силовая 19:00"
        )
        return
   # Проверка формата даты и времени через datetime.strptime
    _, date, name, time = args

    try:
        datetime.strptime(date, "%Y-%m-%d")
        datetime.strptime(time, "%H:%M")
    except ValueError:
        await message.answer("❌ Дата должна быть в формате ГГГГ-ММ-ДД, время — ЧЧ:ММ (24 часа).")
        return

    user_id = message.from_user.id
    await add_one_off_training(user_id, date, name, time)

    await message.answer(f"✅ Тренировка сохранена: {name} на {date} в {time}")

@dp.message(Command("my_trainings"))
async def cmd_my_trainings(message: types.Message):
    user_id = message.from_user.id

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row  # Теперь можно обращаться к колонкам по имени, а не по индексу
        cursor = await db.execute(
            "SELECT id, date, training_name, start_time FROM one_off_trainings WHERE user_id = ? ORDER BY id",
            (user_id,)
        )
        rows = await cursor.fetchall()

    if not rows:
        await message.answer("У тебя пока нет запланированных тренировок")
        return

    text = "🗓 Твои тренировки:\n\n"
    for i, row in enumerate(rows, start=1):

        # enumerate(rows, start=1) - нумерация списка. берет каждую строку из базы данных и дает ей номер: 1, 2, 3
        # i - непосредственно номер.

        text += f"№{i}. 📅 {row['date']} | 🏋️ {row['training_name']} | ⏰ {row['start_time']}\n"
    await message.answer(text)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    welcome_text = (
       f"👋 Привет, {message.from_user.first_name}! Я твой трекер тренировок.\n\n"
        "Вот что я умею:\n\n"
        "📅 /my_trainings — посмотреть список своих тренировок (с номерами для удаления).\n"
        "➕ /add ГГГГ-ММ-ДД Название Время — добавить новую тренировку.\n"
        "🗑️ /delete <номер> — удалить тренировку по номеру из списка.\n"
        "✏️ /edit <номер> ГГГГ-ММ-ДД Название Время — изменить данные тренировки.\n\n"
        "💡 Подсказка: формат даты — 2026-08-25, время — 19:00 (24 часа)."
    )
    await message.answer(welcome_text)

@dp.message(Command("delete"))
async def cmd_delete(message: types.Message):
    args = message.text.split()
    if len(args) != 2:
        await message.answer("❌ Используй: /delete <номер>\n Номер смотри в списке /my_trainings")
        return

    try:
        idx = int(args[1])
    except ValueError:
        await message.answer("❌ Номер должен быть числом, например: /delete 1")
        return
    user_id = message.from_user.id

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT id FROM one_off_trainings WHERE user_id = ? ORDER BY id", (user_id,)
        )
        rows = await cursor.fetchall()

        if not rows:
            await message.answer("У тебя нет тренировок, нечего удалять.")
            return
        if idx < 1 or idx > len(rows):
            await message.answer(f"❌ Такого номера нет. Найдено тренировок: {len(rows)}")
            return
        target_id = rows[idx - 1]["id"]
        await db.execute("DELETE FROM one_off_trainings WHERE id = ?", (target_id,))
        await db.commit()
    await message.answer(f"✅ Тренировка №{idx} успешно удалена!")

async def main():
    print("Bot Started...")
    await init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())


