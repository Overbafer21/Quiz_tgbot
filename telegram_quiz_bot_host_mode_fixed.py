import asyncio
import json
import os
import random
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATA_FILE = Path("quiz_data_full.json")
ADMIN_ID = 748815070

if not BOT_TOKEN:
    raise RuntimeError("Переменная BOT_TOKEN не найдена в Railway Variables")

with open(DATA_FILE, "r", encoding="utf-8") as f:
    QUIZ = json.load(f)

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

admin_mode = set()
user_state = {}
used_questions_chat = {}
scores = {}


def get_letter(i: int) -> str:
    return ["A", "B", "C", "D"][i]


def build_admin_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="➡️ Следующий вопрос", callback_data="next")
    kb.adjust(1)
    return kb.as_markup()


def build_player_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="A", callback_data="ans_0")
    kb.button(text="B", callback_data="ans_1")
    kb.button(text="C", callback_data="ans_2")
    kb.button(text="D", callback_data="ans_3")
    kb.button(text="➡️ Следующий вопрос", callback_data="next")
    kb.adjust(4, 1)
    return kb.as_markup()


def format_question(item: dict, is_admin: bool) -> str:
    text = (
        f"🎯 Вопрос\n\n"
        f"{item['question']}\n\n"
        f"A) {item['options'][0]}\n"
        f"B) {item['options'][1]}\n"
        f"C) {item['options'][2]}\n"
        f"D) {item['options'][3]}"
    )

    if is_admin:
        correct_letter = get_letter(item["correct"] - 1)
        text += f"\n\n✅ Ответ: {correct_letter}) {item['correct_text']}"

    return text


def pick_question(chat_id: int) -> int:
    if chat_id not in used_questions_chat:
        used_questions_chat[chat_id] = set()

    used = used_questions_chat[chat_id]
    available = [i for i in range(len(QUIZ)) if i not in used]

    if not available:
        used.clear()
        available = list(range(len(QUIZ)))

    idx = random.choice(available)
    used.add(idx)
    return idx


async def send_current_question(target, user_id: int, chat_id: int):
    idx = pick_question(chat_id)
    user_state[chat_id] = idx
    item = QUIZ[idx]

    is_admin = user_id in admin_mode
    text = format_question(item, is_admin)

    if is_admin:
        await target.answer(text, reply_markup=build_admin_keyboard())
    else:
        await target.answer(text, reply_markup=build_player_keyboard())


@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Готов.\n\n"
        "/quiz — новый вопрос\n"
        "/admin — админ режим\n"
        "/exit_admin — выйти из админ режима\n"
        "/score — очки"
    )


@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id == ADMIN_ID:
        admin_mode.add(message.from_user.id)
        await message.answer("👑 Админ-режим включён")
    else:
        await message.answer("❌ Нет доступа")


@dp.message(Command("exit_admin"))
async def cmd_exit_admin(message: Message):
    admin_mode.discard(message.from_user.id)
    await message.answer("👤 Обычный режим")


@dp.message(Command("quiz"))
async def cmd_quiz(message: Message):
    await send_current_question(message, message.from_user.id, message.chat.id)


@dp.message(Command("score"))
async def cmd_score(message: Message):
    if not scores:
        await message.answer("Пока никто не набрал очков")
        return

    lines = ["🏆 Очки:\n"]
    for name, value in sorted(scores.items(), key=lambda x: -x[1]):
        lines.append(f"{name}: {value}")
    await message.answer("\n".join(lines))


@dp.callback_query(F.data.startswith("ans_"))
async def cb_answer(callback: CallbackQuery):
    # админу отвечать кнопками не нужно
    if callback.from_user.id in admin_mode:
        await callback.answer("Ты в админ-режиме")
        return

    idx = user_state.get(callback.message.chat.id)
    if idx is None:
        await callback.answer("Сначала вызови /quiz")
        return

    item = QUIZ[idx]
    picked = int(callback.data.split("_")[1])

    if picked == item["correct"] - 1:
        username = callback.from_user.first_name or "Игрок"
        scores[username] = scores.get(username, 0) + 1
        await callback.answer("Правильно!")
        await callback.message.answer("✅ Верно")
    else:
        right_letter = get_letter(item["correct"] - 1)
        await callback.answer("Неверно")
        await callback.message.answer(f"❌ Неверно. Правильный ответ: {right_letter}")

@dp.callback_query(F.data == "next")
async def cb_next(callback: CallbackQuery):
    await send_current_question(
        callback.message,
        callback.from_user.id,
        callback.message.chat.id
    )
    await callback.answer()


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
