#!/usr/bin/env python3
"""
Shadowveil: Last Ember — Telegram Bot
Запуск: python bot.py
"""

import os
import json
import logging
from datetime import datetime

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    WebAppInfo, MenuButtonWebApp
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# ── CONFIG ──────────────────────────────────────────────
BOT_TOKEN  = os.getenv("BOT_TOKEN", "8627491732:AAFCqfpks8QHZBo3lJQEVw_a08Y4l0ZvpJE")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://curkinilian-gif.github.io/Spike_God/")
# ────────────────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
log = logging.getLogger(__name__)

# ── SIMPLE IN-MEMORY LEADERBOARD (замени на БД для продакшна) ──
leaderboard: dict[int, dict] = {}


# ════════════════════════════════════════════════════════
#  HANDLERS
# ════════════════════════════════════════════════════════

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Главное меню бота."""
    user = update.effective_user
    name = user.first_name or "Путник"

    # Кнопка для открытия Mini App
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            text="⚔️  Открыть игру",
            web_app=WebAppInfo(url=WEBAPP_URL)
        )
    ], [
        InlineKeyboardButton("🏆 Таблица лидеров", callback_data="leaderboard"),
        InlineKeyboardButton("❓ Помощь",           callback_data="help"),
    ]])

    text = (
        f"🌑 *Shadowveil: Last Ember*\n\n"
        f"Приветствую тебя, *{name}*.\n\n"
        f"Вечные Тени поглощают мир. Только кристалл Эмбера "
        f"способен остановить тьму — но он спрятан в сердце "
        f"Пещеры, которую стерегут чудовища.\n\n"
        f"_Выбери героя и начни своё путешествие._"
    )

    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=kb
    )

    # Устанавливаем кнопку меню → WebApp
    await ctx.bot.set_chat_menu_button(
        chat_id=update.effective_chat.id,
        menu_button=MenuButtonWebApp(
            text="⚔️ Играть",
            web_app=WebAppInfo(url=WEBAPP_URL)
        )
    )


async def cmd_play(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Быстрый запуск игры."""
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("⚔️  Начать игру", web_app=WebAppInfo(url=WEBAPP_URL))
    ]])
    await update.message.reply_text(
        "🌑 *Тьма зовёт тебя...*\n\nНажми кнопку ниже, чтобы открыть игру.",
        parse_mode="Markdown",
        reply_markup=kb
    )


async def cmd_top(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Таблица лидеров."""
    await send_leaderboard(update.message.reply_text)


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await send_help(update.message.reply_text)


async def callback_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Обработка inline-кнопок."""
    q = update.callback_query
    await q.answer()

    if q.data == "leaderboard":
        await send_leaderboard(q.message.reply_text)
    elif q.data == "help":
        await send_help(q.message.reply_text)
    elif q.data == "play":
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("⚔️  Играть", web_app=WebAppInfo(url=WEBAPP_URL))
        ]])
        await q.message.reply_text(
            "🌑 Открываю врата...",
            reply_markup=kb
        )


async def webapp_data_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    Получаем данные от Mini App через sendData().
    Игра отправляет JSON: { result, turns, kills, xp, hero }
    """
    user = update.effective_user
    raw  = update.effective_message.web_app_data.data

    try:
        data = json.loads(raw)
    except Exception:
        log.warning("Bad webapp data from %s: %s", user.id, raw)
        return

    result = data.get("result", "lose")
    turns  = data.get("turns",  0)
    kills  = data.get("kills",  0)
    xp     = data.get("xp",    0)

    log.info("Game ended | user=%s result=%s xp=%s kills=%s turns=%s",
             user.id, result, xp, kills, turns)

    # Обновляем лидерборд
    prev = leaderboard.get(user.id, {})
    if result == "win" or xp > prev.get("xp", 0):
        leaderboard[user.id] = {
            "name":   user.first_name or "Неизвестный",
            "result": result,
            "xp":     xp,
            "kills":  kills,
            "turns":  turns,
            "ts":     datetime.utcnow().isoformat(),
        }

    # Ответ боту
    if result == "win":
        msg = (
            "💎 *Кристалл Эмбера найден!*\n\n"
            f"Ты победил Теневого дракона и спас мир!\n\n"
            f"📊 *Итоги:*\n"
            f"• Ходов: `{turns}`\n"
            f"• Врагов: `{kills}`\n"
            f"• Опыт: `{xp} XP`\n\n"
            f"_Твой результат записан в таблицу лидеров._"
        )
    else:
        msg = (
            "💀 *Тьма поглотила тебя...*\n\n"
            f"Вечные Тени сомкнулись. Последняя искра угасла.\n\n"
            f"📊 *Результат:*\n"
            f"• Ходов: `{turns}`\n"
            f"• Врагов: `{kills}`\n"
            f"• Опыт: `{xp} XP`\n\n"
            f"_Смерть — не конец. Попробуй снова._"
        )

    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔄 Играть снова", web_app=WebAppInfo(url=WEBAPP_URL)),
        InlineKeyboardButton("🏆 Лидеры",       callback_data="leaderboard"),
    ]])

    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb)


# ════════════════════════════════════════════════════════
#  HELPERS
# ════════════════════════════════════════════════════════

async def send_leaderboard(reply_fn):
    if not leaderboard:
        await reply_fn(
            "🏆 *Таблица лидеров пуста*\n\n"
            "_Стань первым, кто найдёт кристалл Эмбера!_",
            parse_mode="Markdown"
        )
        return

    # Сортируем: победы сначала, потом по XP
    rows = sorted(
        leaderboard.values(),
        key=lambda r: (r["result"] == "win", r["xp"]),
        reverse=True
    )[:10]

    medals = ["🥇","🥈","🥉"] + ["⚔️"] * 10
    lines  = ["🏆 *Таблица лидеров — Top 10*\n"]

    for i, r in enumerate(rows):
        crown  = "💎" if r["result"] == "win" else "💀"
        lines.append(
            f"{medals[i]} {r['name']} {crown}\n"
            f"   XP: `{r['xp']}`  Врагов: `{r['kills']}`  Ходов: `{r['turns']}`"
        )

    await reply_fn("\n".join(lines), parse_mode="Markdown")


async def send_help(reply_fn):
    text = (
        "❓ *Shadowveil: Last Ember — Помощь*\n\n"
        "🎮 *Как играть:*\n"
        "1. Открой игру кнопкой *⚔️ Играть*\n"
        "2. Выбери одного из трёх героев\n"
        "3. Принимай решения — они влияют на исход\n"
        "4. Сражайся с врагами и собирай лут\n"
        "5. Найди кристалл в Пещере Эмбера\n\n"
        "⚔️ *Герои:*\n"
        "• *Кейра* — Воин (HP: 120, Сила: 18)\n"
        "• *Торис* — Маг (MP: 100, Магия: 20)\n"
        "• *Зара* — Лазутчик (Ловкость: 20)\n\n"
        "⚙️ *Команды:*\n"
        "/start — Главное меню\n"
        "/play  — Запустить игру\n"
        "/top   — Таблица лидеров\n"
        "/help  — Эта справка\n\n"
        "🎯 *RPG · 16+ · ~40 ч · 12 локаций*"
    )
    await reply_fn(text, parse_mode="Markdown")


# ════════════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════════════

def main():
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        log.error("❌ Установи BOT_TOKEN в переменную окружения или в bot.py")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("play",  cmd_play))
    app.add_handler(CommandHandler("top",   cmd_top))
    app.add_handler(CommandHandler("help",  cmd_help))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, webapp_data_handler))

    log.info("🌑 Shadowveil bot started. Polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
