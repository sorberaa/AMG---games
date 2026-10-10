from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

import data
from data import fmt
from kb import main_menu_kb
from utils import safe_edit, send_menu

router = Router(name="menu")


def menu_text(p: dict) -> str:
    gif_tag = f"<a href='{data.AMG_GIFS['welcome']}'>&#8205;</a>"
    return (
        f"{gif_tag}🏎 <b>AMG RACING</b>\n\n"
        f"👤 {p['first_name']} · ур. <b>{p['level']}</b>\n"
        f"💰 ${fmt(p['money'])} · 🪙 {fmt(p['coins'])} · ⚡ {p['energy']}/{p['max_energy']}\n\n"
        "Выбери раздел:"
    )


WELCOME = (
    f"<a href='{data.AMG_GIFS['welcome']}'>&#8205;</a>"
    "🏎 <b>AMG RACING</b> 🏎\n\n"
    "Добро пожаловать в мир уличных гонок Mercedes-AMG!\n\n"
    "👥 <b>ВСЕ ИГРЫ И ЗАЕЗДЫ ПРОВОДЯТСЯ В КОМАНДЕ (В ГРУППАХ)!</b>\n"
    "Добавь бота в свой групповой чат с друзьями, чтобы устраивать заезды, бросать вызовы на дуэли и побеждать боссов.\n\n"
    "<b>В личке с ботом ты:</b>\n"
    "🚗 Настраиваешь гараж, тюнингуешь и красишь болиды\n"
    "🧰 Открываешь сундуки и кейсы AMG\n"
    "🪙 Выводишь монеты и меняешь их на кэш\n"
    "🎁 Забираешь ежедневные бонусы\n"
    "👤 Следишь за профилем и достижениями\n\n"
    "💰 Стартовый капитал: <b>$50 000</b>\n"
    "🚗 Первая машина: <b>Mercedes C180</b>"
)


HELP = (
    "❓ <b>Правила и Режимы AMG Racing</b>\n\n"
    "👥 <b>КОМАНДНЫЙ РЕЖИМ (в группах чата):</b>\n"
    "Все игры и соревнования проходят только в группах!\n"
    "• 🏁 /race — уличные гонки с динамическими обгонами\n"
    "• ⚔️ /duel [ставка] — дуэли со ставками в чате\n"
    "• 👾 /boss — командный рейд на босса всем чатом\n"
    "• 🏆 /tournament — Гран-при турнир чата\n"
    "• 🚓 /chase — погоня от полиции всей бандой\n"
    "• 🚦 /drag — драг-рейсинг 402 метра\n"
    "• 👑 /royale — битва на выбывание\n"
    "• 🎰 /wheel — Колесо Фортуны раз в сутки\n"
    "• 📦 /airdrop — перехват контейнера с лутом\n\n"
    "📱 <b>ЛИЧНЫЙ КАБИНЕТ (в личке с ботом):</b>\n"
    "• /garage — гараж и покраска болидов\n"
    "• /tuning — прокачка узлов (двигатель, нитро, турбина)\n"
    "• /shop — покупка новых авто в автосалоне\n"
    "• /cases — открытие сундуков и кейсов AMG\n"
    "• /cshop — магазин бонусов и вывод монет\n"
    "• /withdraw [кол-во] [реквизиты] — вывод золотых монет\n"
    "• /daily — ежедневный подарок\n"
    "• /profile — статистика и достижения"
)


@router.message(CommandStart())
async def cmd_start(message: Message, player: dict):
    await message.answer(WELCOME)
    await send_menu(message, message.from_user.id, menu_text(player), main_menu_kb())


@router.message(Command("menu"))
async def cmd_menu(message: Message, player: dict):
    await send_menu(message, message.from_user.id, menu_text(player), main_menu_kb())


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(HELP)


@router.callback_query(F.data == "menu")
async def cb_menu(cb: CallbackQuery, player: dict):
    await cb.answer()
    await safe_edit(cb, menu_text(player), main_menu_kb())


@router.callback_query(F.data == "help")
async def cb_help(cb: CallbackQuery):
    await cb.answer()
    from kb import back_kb
    await safe_edit(cb, HELP, back_kb())


@router.callback_query(F.data == "group_info")
async def cb_group_info(cb: CallbackQuery):
    await cb.answer()
    bot_info = await cb.bot.get_me()
    from aiogram.types import InlineKeyboardButton as Btn, InlineKeyboardMarkup
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [Btn(text="➕ Добавить бота в группу / команду", url=f"https://t.me/{bot_info.username}?startgroup=true")],
        [Btn(text="◀️ В главное меню", callback_data="menu")],
    ])
    gif_tag = f"<a href='{data.AMG_GIFS['race']}'>&#8205;</a>"
    await safe_edit(
        cb,
        f"{gif_tag}👥 <b>КОМАНДНЫЙ РЕЖИМ AMG RACING</b>\n\n"
        "⚡ <b>Все заезды и игры проводятся исключительно в группах и командах!</b>\n\n"
        "<b>В командных чатах доступны:</b>\n"
        "• 🏁 <b>Уличные гонки</b> и лесенка соперников (/race)\n"
        "• ⚔️ <b>PvP Дуэли со ставками</b> на $ и 🪙 (/duel)\n"
        "• 👾 <b>Рейды на Боссов</b> с общим HP всего чата (/boss)\n"
        "• 🏆 <b>Гран-при турниры</b> на стартовой решетке (/tournament)\n"
        "• 🚓 <b>Погони от полиции</b> всей бандой (/chase)\n"
        "• 🚦 <b>Драг-рейсинг 402 метра</b> на реакцию (/drag)\n"
        "• 👑 <b>Королевская битва</b> на выбывание (/royale)\n"
        "• 🎰 <b>Колесо Фортуны</b> и сходки (/wheel, /adventure)\n"
        "• 📦 <b>Аирдропы</b> и перехват контейнеров (/airdrop)\n\n"
        "В личке с ботом ты настраиваешь гараж, тюнингуешь и красишь авто, открываешь сундуки и выводишь монеты!\n\n"
        "👉 <b>Добавь бота в свою группу прямо сейчас:</b>",
        kb
    )


@router.callback_query(F.data == "noop")
async def cb_noop(cb: CallbackQuery):
    await cb.answer("Уже на максимуме!")

