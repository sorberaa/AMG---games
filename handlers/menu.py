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
    from utils import is_salt_boosted
    salt_indicator = " · 🧂 <b>СОЛЬ (+25% 🚀)</b>" if is_salt_boosted(p) else ""
    return (
        f"{gif_tag}🏎 <b>AMG RACING</b>\n\n"
        f"👤 {p['first_name']} · ур. <b>{p['level']}</b>\n"
        f"🪙 <b>{fmt(p['coins'])} монет</b> · ⚡ {p['energy']}/{p['max_energy']}{salt_indicator}\n\n"
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
    "🪙 Зарабатываешь монеты и прокачиваешь автопарк\n"
    "🎁 Забираешь ежедневные бонусы\n"
    "👤 Следишь за профилем и достижениями\n\n"
    "🪙 Стартовый капитал: <b>500 монет</b>\n"
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
    "• /cshop — магазин бонусов и сундуков\n"
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


@router.callback_query(F.data == "salt_boost")
async def cb_salt_boost(cb: CallbackQuery, player: dict):
    await cb.answer()
    from datetime import datetime
    import db
    from utils import is_salt_boosted
    from aiogram.types import InlineKeyboardButton as Btn, InlineKeyboardMarkup

    active = is_salt_boosted(player)
    time_left = ""
    if active:
        try:
            exp = datetime.strptime(player["salt_boost_until"], db.TS_FMT)
            mins = max(1, int((exp - datetime.utcnow()).total_seconds() // 60))
            time_left = f"\n\n⚡ <b>ЭФФЕКТ УЖЕ АКТИВЕН:</b> осталось <b>{mins} мин.</b> (+25% скорости)"
        except Exception:
            pass

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [Btn(text="💥 БАХНУТЬ СОЛИ (10 🪙)", callback_data="salt_boost:buy")],
        [Btn(text="🌐 Перейти на сайт amglive.to", url="https://amglive.to")],
        [Btn(text="◀️ В главное меню", callback_data="menu")],
    ])

    gif_tag = f"<a href='{data.AMG_GIFS['burnout']}'>&#8205;</a>"
    await safe_edit(
        cb,
        f"{gif_tag}🧂 <b>ЭКСКЛЮЗИВНЫЙ ДОПИНГ: БАХНУТЬ СОЛИ!</b>\n\n"
        "Заряди свой AMG нереальным безумным ускорением прямо с автобана!\n\n"
        "⚡ <b>ЧТО ДАЁТ ЭТОТ БОНУС:</b>\n"
        "• 🚀 <b>+25% К МАКСИМАЛЬНОЙ СКОРОСТИ</b> во всех заездах и дуэлях!\n"
        "• ⏱ Длительность действия эффекта: <b>10 минут</b>\n"
        "• 🌐 Доступ к закрытой платформе: <a href='https://amglive.to'>amglive.to</a>\n"
        "• 💰 Стоимость активации: всего <b>10 🪙 монет</b>\n\n"
        "Опережай соперников на прямых и оставляй их далеко позади в клубах дыма!{time_left}",
        kb
    )


@router.callback_query(F.data == "salt_boost:buy")
async def cb_salt_boost_buy(cb: CallbackQuery, player: dict):
    from datetime import datetime, timedelta
    import db
    from utils import is_salt_boosted

    uid = cb.from_user.id
    cost = 10

    p = await db.get_player(uid)
    if not p or p["coins"] < cost:
        return await cb.answer(f"❌ Недостаточно монет! Нужно {cost} 🪙 монет.", show_alert=True)

    if not await db.spend_coins(uid, cost, reason="Бахнуть соли (+25% скорости)"):
        return await cb.answer("❌ Ошибка списания монет.", show_alert=True)

    # Добавляем 10 минут (если уже был активен, продлеваем на 10 минут)
    now = datetime.utcnow()
    if is_salt_boosted(p):
        try:
            curr_exp = datetime.strptime(p["salt_boost_until"], db.TS_FMT)
            new_exp = curr_exp + timedelta(minutes=10)
        except Exception:
            new_exp = now + timedelta(minutes=10)
    else:
        new_exp = now + timedelta(minutes=10)

    until_str = new_exp.strftime(db.TS_FMT)
    await db.update_player(uid, salt_boost_until=until_str)
    p_updated = await db.get_player(uid)

    await cb.answer("💥 СОЛЬ ПРИНЯТА! +25% к скорости на 10 минут!", show_alert=True)
    await cb_salt_boost(cb, p_updated)

