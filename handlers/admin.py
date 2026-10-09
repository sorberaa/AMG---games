"""Админ-панель AMG Racing. Вход: /admin (только для админов)."""
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton as Btn, InlineKeyboardMarkup, Message

import db
from config import ADMIN_IDS
from data import CAR_CATALOG, fmt
from utils import is_admin, safe_edit, set_admin_cache

router = Router(name="admin")


class Adm(StatesGroup):
    find_player = State()
    amount = State()
    car_key = State()
    level = State()
    broadcast = State()
    add_admin = State()


# ── Клавиатуры ───────────────────────────────────────────────

def main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [Btn(text="📊 Статистика", callback_data="adm:stats"), Btn(text="🪙 Приход/Уход монет", callback_data="adm:coin_flow")],
        [Btn(text="👥 Игроки", callback_data="adm:players:0"), Btn(text="🔎 Найти игрока", callback_data="adm:find")],
        [Btn(text="👑 Список админов", callback_data="adm:admins"), Btn(text="📢 Рассылка", callback_data="adm:broadcast")],
        [Btn(text="✖️ Закрыть", callback_data="adm:close")],
    ])



def back_kb(cb: str = "adm:main") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[Btn(text="◀️ Назад", callback_data=cb)]])


def player_kb(uid: int, p: dict) -> InlineKeyboardMarkup:
    adm = "👤 Снять админку" if p.get("is_admin") else "👑 Дать админку"
    ban = "✅ Разбанить" if p.get("is_banned") else "🚫 Забанить"
    return InlineKeyboardMarkup(inline_keyboard=[
        [Btn(text="💰 +Деньги", callback_data=f"adm:act:money_add:{uid}"),
         Btn(text="💸 −Деньги", callback_data=f"adm:act:money_sub:{uid}")],
        [Btn(text="🪙 +Монеты", callback_data=f"adm:act:coins_add:{uid}"),
         Btn(text="🪙 −Монеты", callback_data=f"adm:act:coins_sub:{uid}")],
        [Btn(text="🚗 Выдать авто", callback_data=f"adm:act:car:{uid}"),
         Btn(text="📈 Уровень", callback_data=f"adm:act:level:{uid}")],
        [Btn(text="⚡ Заполнить энергию", callback_data=f"adm:energy:{uid}")],
        [Btn(text=adm, callback_data=f"adm:toggle_admin:{uid}"),
         Btn(text=ban, callback_data=f"adm:toggle_ban:{uid}")],
        [Btn(text="🔄 Обновить", callback_data=f"adm:p:{uid}"), Btn(text="◀️ К списку", callback_data="adm:players:0")],
    ])


# ── Вход ─────────────────────────────────────────────────────

MAIN_TEXT = "🔐 <b>Админ-панель AMG Racing</b>\n\nВыбери действие:"


@router.message(Command("myid"))
async def cmd_myid(message: Message):
    await message.answer(f"Твой ID: <code>{message.from_user.id}</code>")


@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return await message.answer("❌ У вас нет доступа к админ-панели.")
    await state.clear()
    await message.answer(MAIN_TEXT, reply_markup=main_kb())


@router.message(Command("addadmin"))
async def cmd_addadmin(message: Message):
    if not is_admin(message.from_user.id):
        return await message.answer("❌ Назначать админов могут только главные владельцы.")

    if message.reply_to_message and message.reply_to_message.from_user:
        target_u = message.reply_to_message.from_user
        if target_u.is_bot:
            return await message.answer("❌ Бота нельзя назначить администратором.")
        target_id = target_u.id
        p = await db.get_player(target_id)
        if not p:
            p = await db.create_player(target_id, target_u.username, target_u.first_name)
        await db.update_player(target_id, is_admin=1)
        set_admin_cache(target_id, True)
        return await message.answer(
            f"✅ <b>{target_u.first_name} назначен администратором AMG Racing!</b>\n\n"
            f"🆔 ID: <code>{target_id}</code> (@{target_u.username or '—'})\n"
            f"👑 Ему доступна команда /admin",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[Btn(text="👤 Карточка игрока", callback_data=f"adm:p:{target_id}")]])
        )

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return await message.answer(
            "👑 <b>КАК НАЗНАЧИТЬ АДМИНА В AMG RACING:</b>\n\n"
            "• <b>Способ 1:</b> ответьте на сообщение игрока в группе командой <code>/addadmin</code>\n"
            "• <b>Способ 2:</b> <code>/addadmin 123456789</code> (по Telegram ID)\n"
            "• <b>Способ 3:</b> <code>/addadmin @username</code> (если он уже писал боту)\n"
            "• <b>Способ 4:</b> /admin ➔ «👑 Список админов» ➔ «👥 Выбрать из списка игроков»",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[Btn(text="👑 В админку", callback_data="adm:main")]])
        )

    target_str = parts[1].strip()
    target_id = None
    target_name = None
    target_uname = None

    if target_str.isdigit():
        target_id = int(target_str)
    else:
        uname = target_str.lstrip("@").strip()
        p = await db.get_player_by_username(uname)
        if p:
            target_id = p["user_id"]
            target_name = p["first_name"]
            target_uname = p["username"]
        else:
            return await message.answer(
                f"⚠️ <b>Игрок @{uname} пока не найден в базе бота!</b>\n\n"
                "Telegram не передает ботам информацию о незнакомых пользователях только по @юзернейму, пока они хотя бы раз не нажали /start в боте.\n\n"
                "<b>Решение:</b>\n"
                "1. Ответьте на его сообщение в группе командой <code>/addadmin</code>\n"
                "2. Или укажите его цифровой Telegram ID: <code>/addadmin ЦИФРЫ</code>",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[Btn(text="👑 В админку", callback_data="adm:main")]])
            )

    p = await db.get_player(target_id)
    if not p:
        p = await db.create_player(target_id, target_uname, target_name or f"Admin_{target_id}")
    await db.update_player(target_id, is_admin=1)
    set_admin_cache(target_id, True)
    await message.answer(
        f"✅ <b>{p['first_name']} назначен администратором AMG Racing!</b>\n\n"
        f"🆔 ID: <code>{target_id}</code>\n"
        f"👑 Доступна админ-панель по команде /admin",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [Btn(text="👤 Карточка игрока", callback_data=f"adm:p:{target_id}")],
            [Btn(text="👑 В админку", callback_data="adm:main")]
        ])
    )


@router.callback_query(F.data.startswith("adm:"))
async def adm_router(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id):
        return await cb.answer("Нет доступа", show_alert=True)
    parts = cb.data.split(":")
    action = parts[1]
    await cb.answer()

    if action == "main":
        await state.clear()
        await safe_edit(cb, MAIN_TEXT, main_kb())
    elif action == "close":
        await state.clear()
        await cb.message.delete()
    elif action == "stats":
        await show_stats(cb)
    elif action == "coin_flow":
        await show_coin_flow(cb)
    elif action == "players":
        await show_players(cb, int(parts[2]))
    elif action == "p":
        await show_player(cb, int(parts[2]))
    elif action == "find":
        await state.set_state(Adm.find_player)
        await safe_edit(cb, "🔎 Отправь <b>ID</b> или <b>@username</b> игрока:", back_kb())
    elif action == "admins":
        await show_admins(cb)
    elif action == "add_admin":
        await state.set_state(Adm.add_admin)
        await safe_edit(cb, "➕ <b>Добавление админа</b>\n\nОтправь цифровой <b>Telegram ID</b>, перешли сюда сообщение от игрока, либо укажи его <b>@username</b>:\n\n<i>Для отмены напиши: /admin</i>", back_kb("adm:admins"))
    elif action == "pick_admin_user":
        await show_pick_admin_user(cb, int(parts[2]) if len(parts) > 2 else 0)
    elif action == "make_adm_direct":
        await make_adm_direct(cb, int(parts[2]))
    elif action == "broadcast":
        await state.set_state(Adm.broadcast)
        await safe_edit(cb, "📢 Отправь текст рассылки (поддерживается HTML).\nДля отмены — /admin", back_kb())
    elif action == "energy":
        uid = int(parts[2])
        p = await db.get_player(uid)
        if p:
            await db.update_player(uid, energy=p["max_energy"])
        await show_player(cb, uid)
    elif action == "toggle_admin":
        await toggle_admin(cb, int(parts[2]))
    elif action == "toggle_ban":
        await toggle_ban(cb, int(parts[2]))
    elif action == "act":
        await start_action(cb, state, parts[2], int(parts[3]))


# ── Экраны ───────────────────────────────────────────────────

async def show_stats(cb: CallbackQuery):
    s = await db.server_stats()
    top = await db.get_top_players("wins", 3)
    medals = ["🥇", "🥈", "🥉"]
    top_t = "\n".join(f"{medals[i]} {p['first_name']} — {p['wins']}" for i, p in enumerate(top)) or "—"
    await safe_edit(cb, (
        "📊 <b>Статистика сервера</b>\n\n"
        f"👥 Игроков: <b>{s['players']}</b>\n🟢 Активны сегодня: <b>{s['active_today']}</b>\n"
        f"🚫 Забанено: <b>{s['banned']}</b>\n📈 Средний уровень: <b>{s['avg_level']:.1f}</b>\n\n"
        f"🏁 Гонок всего: <b>{fmt(s['races'])}</b>\n⚔️ PvP-дуэлей: <b>{fmt(s['pvp'])}</b>\n"
        f"🚗 Машин в гаражах: <b>{fmt(s['cars'])}</b>\n\n"
        f"💰 Денег в экономике: <b>${fmt(s['money'])}</b>\n🪙 Монет в экономике: <b>{fmt(s['coins'])}</b>\n"
        f"🪙 Монет добыто сегодня: <b>{fmt(s['coins_today'])}</b>\n\n🏆 <b>Топ по победам:</b>\n{top_t}"
    ), back_kb())


async def show_coin_flow(cb: CallbackQuery):
    flow = await db.get_coin_flow_stats()
    txs = await db.get_recent_coin_txs(12)
    tx_lines = []
    for t in txs:
        sign = "+" if t["amount"] > 0 else ""
        name = t["first_name"] or str(t["user_id"])
        time_part = t["created_at"][11:16] if len(t["created_at"]) >= 16 else ""
        tx_lines.append(f"• <code>{time_part}</code> {name}: <b>{sign}{t['amount']} 🪙</b> ({t['reason']})")
    tx_text = "\n".join(tx_lines) if tx_lines else "<i>Транзакций пока нет</i>"

    await safe_edit(cb, (
        "🪙 <b>Движение монет (Приход / Уход)</b>\n\n"
        f"📅 <b>Сегодня:</b>\n"
        f"🟢 Приход: <b>+{fmt(flow['in_today'])} 🪙</b>\n"
        f"🔴 Уход (траты): <b>-{fmt(flow['out_today'])} 🪙</b>\n"
        f"⚖️ Баланс дня: <b>{fmt(flow['in_today'] - flow['out_today'])} 🪙</b>\n\n"
        f"🌐 <b>За всё время:</b>\n"
        f"🟢 Всего начислено: <b>+{fmt(flow['in_all'])} 🪙</b>\n"
        f"🔴 Всего потрачено: <b>-{fmt(flow['out_all'])} 🪙</b>\n\n"
        f"📜 <b>Последние операции:</b>\n{tx_text}"
    ), back_kb())


async def show_players(cb: CallbackQuery, page: int):
    players = await db.get_all_players()
    per = 8
    rows = []
    for p in players[page * per:(page + 1) * per]:
        mark = ("🚫" if p["is_banned"] else "") + ("👑" if is_admin(p["user_id"]) else "")
        rows.append([Btn(text=f"{mark}{p['first_name']} · ур.{p['level']} · ${fmt(p['money'])}",
                         callback_data=f"adm:p:{p['user_id']}")])
    nav = []
    if page > 0:
        nav.append(Btn(text="◀️", callback_data=f"adm:players:{page - 1}"))
    if (page + 1) * per < len(players):
        nav.append(Btn(text="▶️", callback_data=f"adm:players:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([Btn(text="◀️ Назад", callback_data="adm:main")])
    await safe_edit(cb, f"👥 <b>Игроки</b> ({len(players)})\nСтраница {page + 1}",
                    InlineKeyboardMarkup(inline_keyboard=rows))


def player_card(p: dict, cars: list) -> str:
    role = "👑 Главный админ" if p["user_id"] in ADMIN_IDS else ("👑 Админ" if p["is_admin"] else "👤 Игрок")
    status = "🚫 Забанен" if p["is_banned"] else "✅ Активен"
    car_list = ", ".join(CAR_CATALOG[c["car_key"]]["name"].replace("Mercedes-AMG ", "") for c in cars[:8]
                         if c["car_key"] in CAR_CATALOG)
    if len(cars) > 8:
        car_list += f" и ещё {len(cars) - 8}"
    ins_status = "🛡 Страховка активна" if p.get("has_insurance") else "🛡 Без страховки"
    wrap_status = "✨ Золотой винил" if p.get("gold_wrap") else ""
    extra_status = f"\n{ins_status}" + (f" · {wrap_status}" if wrap_status else "")
    return (
        f"👤 <b>{p['first_name']}</b> (@{p['username'] or '—'})\n"
        f"🆔 <code>{p['user_id']}</code>\n{role} · {status}{extra_status}\n\n"
        f"📊 Уровень: {p['level']} ({p['xp']} XP)\n💰 Деньги: ${fmt(p['money'])}\n"
        f"🪙 Монеты: {fmt(p['coins'])} (сегодня: {p['coins_today'] if p['coins_date'] else 0})\n"
        f"⚡ Энергия: {p['energy']}/{p['max_energy']}\n⭐ Репутация: {p['reputation']}\n"
        f"🏁 Гонок: {p['races_total']} · 🏆 {p['wins']} · 💀 {p['losses']}\n"
        f"🔥 Стрик: {p['daily_streak']}\n📅 С нами с: {p['created_at'][:10]}\n\n"
        f"🚗 Машины ({len(cars)}): {car_list or '—'}"
    )



async def show_player(cb: CallbackQuery, uid: int):
    p = await db.get_player(uid)
    if not p:
        return await safe_edit(cb, "❌ Игрок не найден", back_kb())
    await safe_edit(cb, player_card(p, await db.get_player_cars(uid)), player_kb(uid, p))


async def show_admins(cb: CallbackQuery):
    lines = [f"👑 <code>{i}</code> (главный, из .env)" for i in ADMIN_IDS]
    for uid in await db.get_admin_ids():
        if uid in ADMIN_IDS:
            continue
        p = await db.get_player(uid)
        if p:
            lines.append(f"👑 <b>{p['first_name']}</b> — <code>{uid}</code>")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [Btn(text="➕ Ввести ID или переслать", callback_data="adm:add_admin")],
        [Btn(text="👥 Выбрать из списка игроков", callback_data="adm:pick_admin_user:0")],
        [Btn(text="◀️ Назад", callback_data="adm:main")]
    ])
    await safe_edit(cb, "👑 <b>Администраторы AMG Racing</b>\n\n" + ("\n".join(lines) or "Нет") +
                    "\n\n<i>Выберите способ добавления админа:</i>", kb)


async def show_pick_admin_user(cb: CallbackQuery, page: int = 0):
    players = await db.get_all_players()
    non_admins = [p for p in players if not p.get("is_admin") and p["user_id"] not in ADMIN_IDS]
    if not non_admins:
        return await safe_edit(cb, "👥 Все игроки в базе уже назначены админами!", back_kb("adm:admins"))
    per = 6
    rows = []
    for p in non_admins[page * per : (page + 1) * per]:
        rows.append([
            Btn(text=f"👤 {p['first_name']} (@{p.get('username') or p['user_id']})", callback_data=f"adm:p:{p['user_id']}"),
            Btn(text="👑 Назначить", callback_data=f"adm:make_adm_direct:{p['user_id']}")
        ])
    nav = []
    if page > 0:
        nav.append(Btn(text="◀️", callback_data=f"adm:pick_admin_user:{page - 1}"))
    if (page + 1) * per < len(non_admins):
        nav.append(Btn(text="▶️", callback_data=f"adm:pick_admin_user:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([Btn(text="◀️ Назад к админам", callback_data="adm:admins")])
    await safe_edit(cb, f"👥 <b>Выбор из игроков</b> ({len(non_admins)})\nНажмите «👑 Назначить» напротив нужного игрока:", InlineKeyboardMarkup(inline_keyboard=rows))


async def make_adm_direct(cb: CallbackQuery, uid: int):
    p = await db.get_player(uid)
    if not p:
        return await cb.answer("Игрок не найден!", show_alert=True)
    await db.update_player(uid, is_admin=1)
    set_admin_cache(uid, True)
    await cb.answer(f"✅ {p['first_name']} назначен админом!", show_alert=True)
    try:
        await cb.bot.send_message(uid, "👑 Тебе выданы права администратора в AMG Racing! Команда: /admin")
    except Exception:
        pass
    await show_admins(cb)


async def toggle_admin(cb: CallbackQuery, uid: int):
    p = await db.get_player(uid)
    if not p:
        return
    if uid in ADMIN_IDS:
        return await cb.answer("Главного админа нельзя снять", show_alert=True)
    if uid == cb.from_user.id:
        return await cb.answer("Нельзя менять свои права", show_alert=True)
    new = 0 if p["is_admin"] else 1
    await db.update_player(uid, is_admin=new)
    set_admin_cache(uid, bool(new))
    try:
        await cb.bot.send_message(uid, "👑 Тебе выданы права администратора! Команда: /admin" if new
                                  else "Твои права администратора сняты.")
    except Exception:
        pass
    await show_player(cb, uid)


async def toggle_ban(cb: CallbackQuery, uid: int):
    p = await db.get_player(uid)
    if not p:
        return
    if is_admin(uid) and not p["is_banned"]:
        return await cb.answer("Сначала сними админку", show_alert=True)
    await db.update_player(uid, is_banned=0 if p["is_banned"] else 1)
    await show_player(cb, uid)


# ── Действия с вводом ────────────────────────────────────────

PROMPTS = {
    "money_add": "💰 Сколько денег <b>выдать</b>?",
    "money_sub": "💸 Сколько денег <b>забрать</b>?",
    "coins_add": "🪙 Сколько монет <b>выдать</b>? (без дневного лимита)",
    "coins_sub": "🪙 Сколько монет <b>забрать</b>?",
    "level": "📈 Какой уровень установить? (1–100)",
}


async def start_action(cb: CallbackQuery, state: FSMContext, act: str, uid: int):
    await state.update_data(target=uid, act=act)
    if act == "car":
        await state.set_state(Adm.car_key)
        cars = "\n".join(f"<code>{k}</code> — {v['name']}" for k, v in CAR_CATALOG.items())
        await safe_edit(cb, f"🚗 Отправь ключ машины:\n\n{cars}", back_kb(f"adm:p:{uid}"))
    elif act == "level":
        await state.set_state(Adm.level)
        await safe_edit(cb, PROMPTS[act], back_kb(f"adm:p:{uid}"))
    else:
        await state.set_state(Adm.amount)
        await safe_edit(cb, PROMPTS[act] + "\nОтправь число:", back_kb(f"adm:p:{uid}"))


def card_kb(uid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[Btn(text="👤 К игроку", callback_data=f"adm:p:{uid}"),
                                                  Btn(text="🔐 Админка", callback_data="adm:main")]])


def parse_int(text: str | None):
    try:
        return int((text or "").replace(" ", "").replace(",", "").replace("$", ""))
    except ValueError:
        return None


@router.message(Adm.amount)
async def on_amount(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return await state.clear()
    n = parse_int(message.text)
    if n is None or n <= 0:
        return await message.answer("❌ Нужно положительное число")
    d = await state.get_data()
    uid, act = d["target"], d["act"]
    await state.clear()
    if act == "money_add":
        await db.add_money(uid, n)
    elif act == "money_sub":
        await db.add_money(uid, -n)
    elif act == "coins_add":
        await db.add_coins_admin(uid, n)
    elif act == "coins_sub":
        await db.add_coins_admin(uid, -n)
    p = await db.get_player(uid)
    await message.answer(f"✅ Готово. Теперь у {p['first_name']}: ${fmt(p['money'])} · {fmt(p['coins'])} 🪙",
                         reply_markup=card_kb(uid))


@router.message(Adm.car_key)
async def on_car_key(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return await state.clear()
    key = (message.text or "").strip().lower()
    if key not in CAR_CATALOG:
        return await message.answer("❌ Нет такой машины, проверь ключ")
    uid = (await state.get_data())["target"]
    await state.clear()
    await db.add_car(uid, key)
    await message.answer(f"✅ Выдана {CAR_CATALOG[key]['name']}", reply_markup=card_kb(uid))


@router.message(Adm.level)
async def on_level(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return await state.clear()
    n = parse_int(message.text)
    if n is None or not 1 <= n <= 100:
        return await message.answer("❌ Уровень от 1 до 100")
    uid = (await state.get_data())["target"]
    await state.clear()
    await db.update_player(uid, level=n, xp=0)
    await message.answer(f"✅ Уровень установлен: {n}", reply_markup=card_kb(uid))


@router.message(Adm.find_player)
async def on_find(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return await state.clear()
    q = (message.text or "").strip().lstrip("@")
    await state.clear()
    p = None
    if q.isdigit():
        p = await db.get_player(int(q))
    else:
        for pl in await db.get_all_players():
            if (pl["username"] or "").lower() == q.lower():
                p = pl
                break
    if not p:
        return await message.answer("❌ Игрок не найден (он должен хотя бы раз написать боту)", reply_markup=back_kb())
    await message.answer(player_card(p, await db.get_player_cars(p["user_id"])), reply_markup=player_kb(p["user_id"], p))


@router.message(Adm.broadcast)
async def on_broadcast(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return await state.clear()
    await state.clear()
    text = message.html_text if message.text else None
    if not text:
        return await message.answer("❌ Нужен текст")
    import asyncio
    sent = failed = 0
    status = await message.answer("📢 Рассылка идёт...")
    for p in await db.get_all_players():
        if p["is_banned"]:
            continue
        try:
            await message.bot.send_message(p["user_id"], f"📢 <b>Объявление</b>\n\n{text}")
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)
    await status.edit_text(f"📢 Рассылка завершена\n✅ Доставлено: {sent}\n❌ Ошибок: {failed}", reply_markup=back_kb())


@router.message(Adm.add_admin)
async def on_add_admin(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return await state.clear()

    target_id = None
    target_name = None
    target_uname = None

    if message.forward_origin:
        sender = getattr(message.forward_origin, "sender_user", None)
        if sender:
            target_id = sender.id
            target_name = sender.first_name
            target_uname = sender.username
    elif message.forward_from:
        target_id = message.forward_from.id
        target_name = message.forward_from.first_name
        target_uname = message.forward_from.username
    elif message.reply_to_message and message.reply_to_message.from_user:
        target_id = message.reply_to_message.from_user.id
        target_name = message.reply_to_message.from_user.first_name
        target_uname = message.reply_to_message.from_user.username
    elif message.contact:
        target_id = message.contact.user_id
        target_name = message.contact.first_name
    elif message.text:
        text = message.text.strip()
        if "t.me/" in text:
            text = text.split("t.me/")[-1].split("/")[0].split("?")[0].strip()
        if text.isdigit():
            target_id = int(text)
        else:
            uname = text.lstrip("@").strip()
            p = await db.get_player_by_username(uname)
            if p:
                target_id = p["user_id"]
                target_name = p["first_name"]
                target_uname = p["username"]
            else:
                return await message.answer(
                    f"⚠️ <b>Игрок @{uname} пока не найден в базе бота!</b>\n\n"
                    "Telegram не позволяет ботам узнать цифровой ID нового пользователя только по @юзернейму, пока он ни разу не нажимал /start в боте.\n\n"
                    "<b>Решение:</b>\n"
                    "1. Перешлите сюда любое сообщение от него\n"
                    "2. Ответьте на его сообщение в группе командой <code>/addadmin</code>\n"
                    "3. Отправьте его цифровой Telegram ID",
                    reply_markup=back_kb("adm:admins")
                )

    if not target_id:
        return await message.answer("❌ Не удалось определить ID. Отправьте цифровой ID или перешлите сообщение игрока.")

    await state.clear()
    p = await db.get_player(target_id)
    if not p:
        p = await db.create_player(target_id, target_uname, target_name or f"User_{target_id}")
    await db.update_player(target_id, is_admin=1)
    set_admin_cache(target_id, True)
    try:
        await message.bot.send_message(target_id, "👑 Тебе выданы права администратора в AMG Racing! Команда: /admin")
    except Exception:
        pass
    await message.answer(
        f"✅ <b>{p['first_name']} назначен администратором AMG Racing!</b>\n\n"
        f"🆔 ID: <code>{target_id}</code> (@{target_uname or '—'})\n"
        f"👑 Доступна админ-панель по команде /admin",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [Btn(text="👤 Карточка игрока", callback_data=f"adm:p:{target_id}")],
            [Btn(text="👑 В админку", callback_data="adm:main")]
        ])
    )
