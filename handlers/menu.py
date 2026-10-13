from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

import data
from data import fmt
from kb import back_kb, main_menu_kb
from utils import safe_edit, send_menu

router = Router(name="menu")


def menu_text(p: dict) -> str:
    gif_tag = f"<a href='{data.AMG_GIFS['welcome']}'>&#8205;</a>"
    import db
    from utils import is_salt_boosted
    vip_indicator = " 👑" if db.is_vip(p) else ""
    salt_indicator = " · 🧂 <b>СОЛЬ (+25% 🚀)</b>" if is_salt_boosted(p) else ""
    nitro_indicator = " · 🔥 <b>НИТРО (+15%)</b>" if db.is_nitro_boosted(p) else ""
    vip_status_line = "👑 <i>VIP-пилот AMG активен</i>\n" if db.is_vip(p) else ""
    return (
        f"{gif_tag}🏎 <b>MERCEDES-AMG MOTORSPORT</b> | <i>by A$k</i>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 Пилот: <b>{p['first_name']}</b>{vip_indicator}\n"
        f"📊 Уровень <b>{p['level']}</b> · ⭐ Репутация: <b>{p['reputation']}</b>\n"
        f"🪙 Баланс: <b>{fmt(p['coins'])} монет</b>\n"
        f"⚡ Энергия: <b>{p['energy']}/{p['max_energy']}</b>{salt_indicator}{nitro_indicator}\n"
        f"👑 Автор проекта: <b>A$k</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{vip_status_line}"
        "Выбери раздел гаража или заезда:"
    )



WELCOME = (
    f"<a href='{data.AMG_GIFS['welcome']}'>&#8205;</a>"
    "🏎 <b>AMG RACING BOT</b> 🏎\n"
    "👑 <b>Автор и создатель проекта:</b> <b>A$k</b>\n\n"
    "Добро пожаловать в мир уличных гонок Mercedes-AMG!\n\n"
    "🏁 <b>ГОНКИ И СОРЕВНОВАНИЯ:</b>\n"
    "• 🏎 Одиночные спринты за подарками прямо в боте (/race)\n"
    "• 👥 Командные заезды, дуэли, погони от полиции и рейды на боссов в группах!\n\n"
    "<b>В гараже и сервисе:</b>\n"
    "🚗 Собирай коллекцию легендарных AMG (/garage)\n"
    "🔧 Прокачивай чип-тюнинг, турбины, нитро (/tuning)\n"
    "🎨 Кастомная покраска кузова\n"
    "🧰 Открывай сундуки с ценным лутом (/cases)\n"
    "🪙 Зарабатывай монеты и обменивай призы (/cshop)\n\n"
    "🪙 Стартовый капитал: <b>500 монет</b>\n"
    "🚗 Первая машина: <b>Mercedes C180</b>\n\n"
    "👑 <i>Создатель и разработчик игры:</i> <b>A$k</b>"
)


HELP = (
    "❓ <b>Правила и Режимы AMG Racing</b>\n"
    "👑 <b>Создатель игры:</b> <b>A$k</b>\n\n"
    "👥 <b>КОМАНДНЫЙ РЕЖИМ (в группах чата):</b>\n"
    "Все игры и соревнования проходят только в группах!\n"
    "• 🏁 /race — уличные гонки с динамическими обгонами\n"
    "• ⚔️ /duel [ставка] — дуэли со ставками в чате\n"
    "• 👾 /boss — командный рейд на босса всем чатом\n"
    "• 🏆 /tournament — Гран-при турнир чата\n"
    "• 🚓 /chase — погоня от полиции всей бандой\n"
    "• 🚦 /drag — драг-рейсинг 402 метра\n"
    "• 👑 /royale — битва на выбывание\n"
    "• 🎰 /wheel — Колесо Фортуны раз в сутки (+доп. спины)\n"
    "• 📦 /airdrop — перехват контейнера с лутом\n"
    "• 🔥 /boost — запустить Счастливые часы (буст x2 наград чата)\n\n"
    "📱 <b>ЛИЧНЫЙ КАБИНЕТ (в личке с ботом):</b>\n"
    "• /garage — гараж и покраска болидов\n"
    "• /plate [номер] — установить блатной госномер на авто\n"
    "• /tuning — прокачка узлов (двигатель, нитро, турбина)\n"
    "• /shop — покупка новых авто в автосалоне\n"
    "• /stars — звёздный магазин Telegram Stars\n"
    "• /cases — открытие сундуков и кейсов AMG\n"
    "• /cshop — магазин бонусов и сундуков\n"
    "• /daily — ежедневный подарок\n"
    "• /profile — статистика и достижения\n"
    "• /author — информация об авторе (A$k)\n\n"
    "👑 <b>Основатель и владелец проекта:</b> <b>A$k</b>"
)

AUTHOR_TEXT = (
    f"<a href='{data.AMG_GIFS['welcome']}'>&#8205;</a>"
    "👑 <b>АВТОР И СОЗДАТЕЛЬ ПРОЕКТА AMG RACING</b> 👑\n\n"
    "🏎 <b>AMG Racing Bot</b> полностью придуман, создан и запущен под авторством:\n"
    "👉 <b>A$k</b> — идейный вдохновитель, основатель и создатель игры!\n\n"
    "🏆 Все механики уличных гонок, тюнинга Mercedes-AMG, рейдов на боссов, дуэлей и Stars-экономики созданы автором <b>A$k</b>.\n\n"
    "💬 <i>По вопросам сотрудничества, рекламы и предложений обращайтесь к автору проекта: <b>A$k</b>!</i>"
)


@router.message(CommandStart())
async def cmd_start(message: Message, player: dict):
    # Обработка диплинков оплаты и бустов
    text = message.text or ""
    parts = text.split(maxsplit=1)
    if len(parts) > 1:
        param = parts[1].strip()
        if param.startswith("boost_"):
            target_chat_id = param.replace("boost_", "")
            pack = data.STARS_PACKS.get("chat_boost_x2")
            if pack:
                from aiogram.types import LabeledPrice
                prices = [LabeledPrice(label=pack["title"], amount=pack["stars"])]
                return await message.answer_invoice(
                    title=pack["title"],
                    description=f"Активация Буста наград x2 для чата ID: {target_chat_id} на 2 часа!",
                    payload=f"stars:chat_boost:{target_chat_id}:{message.from_user.id}",
                    currency="XTR",
                    prices=prices,
                    provider_token="",
                    start_parameter=f"boost_{target_chat_id}"
                )
        elif param.startswith("stars_"):
            pack_id = param.replace("stars_", "")
            pack = data.STARS_PACKS.get(pack_id)
            if pack:
                from aiogram.types import LabeledPrice
                prices = [LabeledPrice(label=pack["title"], amount=pack["stars"])]
                return await message.answer_invoice(
                    title=pack["title"],
                    description=pack["short_desc"],
                    payload=f"stars:{pack_id}:{message.from_user.id}",
                    currency="XTR",
                    prices=prices,
                    provider_token="",
                    start_parameter=f"stars_{pack_id}"
                )

    await message.answer(WELCOME)
    await send_menu(message, message.from_user.id, menu_text(player), main_menu_kb())


@router.message(Command("menu"))
async def cmd_menu(message: Message, player: dict):
    await send_menu(message, message.from_user.id, menu_text(player), main_menu_kb())


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(HELP)


@router.message(Command("author", "creator", "about"))
async def cmd_author(message: Message):
    await message.answer(AUTHOR_TEXT, reply_markup=back_kb("menu", "🏠 В главное меню"))


@router.callback_query(F.data == "author_info")
async def cb_author_info(cb: CallbackQuery):
    await cb.answer()
    await safe_edit(cb, AUTHOR_TEXT, back_kb("menu", "🏠 В главное меню"))


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

    today = db.now_str()[:10]
    used_today = (player.get("last_salt_boost_date") == today)
    active = is_salt_boosted(player)
    time_left = ""
    if active:
        try:
            exp = datetime.strptime(player["salt_boost_until"], db.TS_FMT)
            mins = max(1, int((exp - datetime.utcnow()).total_seconds() // 60))
            time_left = f"\n\n⚡ <b>ЭФФЕКТ СЕЙЧАС АКТИВЕН:</b> осталось <b>{mins} мин.</b> (+25% скорости)"
        except Exception:
            pass

    if used_today and not active:
        daily_note = "\n\n⏳ <b>ЛИМИТ:</b> Ты уже использовал допинг сегодня! Следующая порция будет доступна завтра."
        action_btn = Btn(text="⏳ Использовано сегодня (1 раз в день)", callback_data="noop")
    elif active:
        daily_note = "\n\n⚡ <b>Действие в процессе!</b> Повторно бахнуть можно будет завтра."
        action_btn = Btn(text="⚡ Действует прямо сейчас (+25%)", callback_data="noop")
    else:
        daily_note = "\n\n✨ <b>Доступно для активации:</b> 1 раз в сутки."
        action_btn = Btn(text="💥 БАХНУТЬ СОЛИ (10 🪙)", callback_data="salt_boost:buy")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [action_btn],
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
        "• 🔒 Ограничение: <b>строго 1 раз в день!</b>\n"
        "• 🌐 Доступ к закрытой платформе: <a href='https://amglive.to'>amglive.to</a>\n"
        "• 💰 Стоимость активации: всего <b>10 🪙 монет</b>\n\n"
        "Опережай соперников на прямых и оставляй их далеко позади в клубах дыма!{time_left}{daily_note}",
        kb
    )


@router.callback_query(F.data == "salt_boost:buy")
async def cb_salt_boost_buy(cb: CallbackQuery, player: dict):
    from datetime import datetime, timedelta
    import db
    from utils import is_salt_boosted

    uid = cb.from_user.id
    cost = 10
    today = db.now_str()[:10]

    p = await db.get_player(uid)
    if not p:
        return await cb.answer("Игрок не найден", show_alert=True)

    if p.get("last_salt_boost_date") == today:
        return await cb.answer("⏳ Ты уже бахал соли сегодня! Допинг доступен только 1 раз в день.", show_alert=True)

    if p["coins"] < cost:
        return await cb.answer(f"❌ Недостаточно монет! Нужно {cost} 🪙 монет.", show_alert=True)

    if not await db.spend_coins(uid, cost, reason="Бахнуть соли (+25% скорости)"):
        return await cb.answer("❌ Ошибка списания монет.", show_alert=True)

    now = datetime.utcnow()
    new_exp = now + timedelta(minutes=10)
    until_str = new_exp.strftime(db.TS_FMT)

    await db.update_player(uid, salt_boost_until=until_str, last_salt_boost_date=today)
    p_updated = await db.get_player(uid)

    await cb.answer("💥 СОЛЬ ПРИНЯТА! +25% к скорости на 10 минут! (1 раз в день)", show_alert=True)
    await cb_salt_boost(cb, p_updated)

