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

QUIZ = json.load(open(DATA_FILE, encoding="utf-8"))

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

admin_mode = set()
user_state = {}
used_questions_chat = {}
scores = {}


def get_letter(i):
    return ["A", "B", "C", "D"][i]


def build_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="A", callback_data="ans_0")
    kb.button(text="B", callback_data="ans_1")
    kb.button(text="C", callback_data="ans_2")
    kb.button(text="D", callback_data="ans_3")
    kb.button(text="➡️ Следующий", callback_data="next")
    kb.adjust(4, 1)
    return kb.as_markup()


def format_q(item, uid):
    text = (
        f"🎯 {item['question']}\n\n"
        f"A) {item['options'][0]}\n"
        f"B) {item['options'][1]}\n"
        f"C) {item['options'][2]}\n"
        f"D) {item['options'][3]}"
    )

    if uid in admin_mode:
        text += f"\n\n✅ {get_letter(item['correct']-1)}) {item['correct_text']}"

    return text


def pick(chat_id):
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


@dp.message(Command("start"))
async def start(m: Message):
    await m.answer("готов\n/quiz /admin /exit_admin /score")


@dp.message(Command("admin"))
async def admin(m: Message):
    if m.from_user.id == ADMIN_ID:
        admin_mode.add(m.from_user.id)
        await m.answer("👑 админ режим включен")
    else:
        await m.answer("❌ нет доступа")


@dp.message(Command("exit_admin"))
async def exit_admin(m: Message):
    admin_mode.discard(m.from_user.id)
    await m.answer("👤 обычный режим")


@dp.message(Command("quiz"))
async def quiz(m: Message):
    idx = pick(m.chat.id)
    user_state[m.chat.id] = idx

    # 👑 админ — БЕЗ кнопок
    if m.from_user.id in admin_mode:
        await m.answer(format_q(QUIZ[idx], m.from_user.id))
    else:
        await m.answer(
            format_q(QUIZ[idx], m.from_user.id),
            reply_markup=build_keyboard()
        )


@dp.message(Command("score"))
async def score(m: Message):
    if not scores:
        return await m.answer("пусто")

    text = "🏆\n"
    for k, v in sorted(scores.items(), key=lambda x: -x[1]):
        text += f"{k}: {v}\n"

    await m.answer(text)


@dp.callback_query(F.data.startswith("ans_"))
async def answer(c: CallbackQuery):
    idx = user_state.get(c.message.chat.id)
    if idx is None:
        return await c.answer()

    q = QUIZ[idx]
    ans = int(c.data.split("_")[1])

    if ans == q["correct"] - 1:
        scores[c.from_user.first_name] = scores.get(c.from_user.first_name, 0) + 1
        await c.message.answer("✅ правильно")
    else:
        await c.message.answer("❌ мимо")

    await c.answer()


@dp.callback_query(F.data == "next")
async def next_q(c: CallbackQuery):
    idx = pick(c.message.chat.id)
    user_state[c.message.chat.id] = idx

    if c.from_user.id in admin_mode:
        await c.message.answer(format_q(QUIZ[idx], c.from_user.id))
    else:
        await c.message.answer(
            format_q(QUIZ[idx], c.from_user.id),
            reply_markup=build_keyboard()
        )

    await c.answer()


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
