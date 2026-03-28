import asyncio
import json
import os
import random
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

BOT_TOKEN = os.getenv("8759270411:AAGJFqOzJJV4BLkxOTtIotjp3vLppQfcckA")
DATA_FILE = Path("quiz_data_full.json")


def load_data():
    if not DATA_FILE.exists():
        raise FileNotFoundError("Рядом с ботом не найден quiz_data_full.json")
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


QUIZ = load_data()
bot = Bot(BOT_TOKEN)
dp = Dispatcher()

ADMIN_ID = 748815070
admin_mode = set()

user_state = {}
used_questions = {}


def build_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="➡️ Следующий вопрос", callback_data="next_question")
    kb.adjust(1)
    return kb.as_markup()


def format_question(item, user_id, number=None):
    title = f"🎯 Вопрос {number}" if number else "🎯 Вопрос"

    text = (
        f"{title}\n\n"
        f"{item['question']}\n\n"
        f"A) {item['options'][0]}\n"
        f"B) {item['options'][1]}\n"
        f"C) {item['options'][2]}\n"
        f"D) {item['options'][3]}"
    )

    if user_id in admin_mode:
        correct_letter = ["A", "B", "C", "D"][item["correct"] - 1]
        text += f"\n\n✅ Ответ: {correct_letter}) {item['correct_text']}"

    return text


def pick_question_for_user(user_id: int) -> int:
    if user_id not in used_questions:
        used_questions[user_id] = set()

    used = used_questions[user_id]
    all_indexes = list(range(len(QUIZ)))
    available = [i for i in all_indexes if i not in used]

    if not available:
        used.clear()
        available = all_indexes[:]

    idx = random.choice(available)
    used.add(idx)
    return idx


@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Привет.\n\n"
        "Команды:\n"
        "/quiz — случайный вопрос\n"
        "/next — следующий вопрос\n"
        "/admin — включить админ режим"
    )


@dp.message(Command("admin"))
async def admin_mode_on(message: Message):
    if message.from_user.id == ADMIN_ID:
        admin_mode.add(message.from_user.id)
        await message.answer("👑 Админ режим включен")
    else:
        await message.answer("❌ Нет доступа")


@dp.message(Command("quiz"))
async def cmd_quiz(message: Message):
    idx = pick_question_for_user(message.from_user.id)
    user_state[message.from_user.id] = idx
    await message.answer(
        format_question(QUIZ[idx], message.from_user.id, idx + 1),
        reply_markup=build_keyboard()
    )


@dp.message(Command("next"))
async def cmd_next(message: Message):
    idx = pick_question_for_user(message.from_user.id)
    user_state[message.from_user.id] = idx
    await message.answer(
        format_question(QUIZ[idx], message.from_user.id, idx + 1),
        reply_markup=build_keyboard()
    )


@dp.callback_query(F.data == "next_question")
async def cb_next_question(callback: CallbackQuery):
    idx = pick_question_for_user(callback.from_user.id)
    user_state[callback.from_user.id] = idx
    await callback.message.answer(
        format_question(QUIZ[idx], callback.from_user.id, idx + 1),
        reply_markup=build_keyboard()
    )
    await callback.answer()


async def main():
    if not BOT_TOKEN:
        raise RuntimeError("Переменная BOT_TOKEN не задана в Railway Variables")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
