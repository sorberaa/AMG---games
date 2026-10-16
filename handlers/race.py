import asyncio
import random
from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message

import db
import data
from data import CAR_CATALOG, STREET_OPPONENTS, fmt
from engine import calc_rewards, calc_stats, car_upgrades, simulate_race
from kb import (
    back_kb, no_energy_kb, pvp_bet_kb, pvp_challenge_kb, pvp_list_kb,
    race_menu_kb, race_result_kb, solo_race_kb, solo_race_result_kb, street_opponents_kb
)
from utils import award_achievements, safe_edit, send_menu

router = Router(name="race")
MAX_BET = 100


async def team_only_redirect(event, is_callback: bool = False):
    bot_info = await event.bot.get_me()
    from aiogram.types import InlineKeyboardButton as Btn, InlineKeyboardMarkup
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [Btn(text="➕ Добавить бота в группу / команду", url=f"https://t.me/{bot_info.username}?startgroup=true")],
        [Btn(text="◀️ Назад к гонкам", callback_data="race"),
         Btn(text="🏠 Главное меню", callback_data="menu")],
    ])
    gif_tag = f"<a href='{data.AMG_GIFS['race']}'>&#8205;</a>"
    text = (
        f"{gif_tag}👥 <b>ВСЕ ГОНКИ И ЗАЕЗДЫ ПРОВОДЯТСЯ В КОМАНДЕ!</b>\n\n"
        "⚡ <b>В личке с ботом ты:</b>\n"
        "• 🚗 Настраиваешь, тюнингуешь и красишь болиды (/garage, /tuning)\n"
        "• 🧰 Открываешь сундуки и кейсы AMG (/cases)\n"
        "• 🪙 Управляешь монетами и бонусами (/cshop)\n"
        "• 🎁 Забираешь ежедневные подарки (/daily)\n"
        "• 👤 Смотришь профиль и статистику (/profile)\n\n"
        "🏁 <b>Все игры проводятся в команде!</b>\n"
        "Добавь бота в свою группу или командный чат, чтобы устраивать заезды, соревноваться в дуэлях со ставками и крушить боссов вместе с друзьями! 👇"
    )
    if is_callback:
        await safe_edit(event, text, kb)
    else:
        await event.answer(text, reply_markup=kb)


async def race_menu_text(uid: int) -> str:
    energy = await db.regen_energy(uid)
    p = await db.get_player(uid)
    pc = await db.get_selected_car(uid)
    car = CAR_CATALOG[pc["car_key"]] if pc else None
    rating = calc_stats(car, car_upgrades(pc))["rating"] if pc else 0
    wait = await db.minutes_to_next_energy(uid)
    regen = f"\n⏳ +1 ⚡ через {wait} мин" if wait else ""
    gif_tag = f"<a href='{data.AMG_GIFS['race']}'>&#8205;</a>"
    return (
        f"{gif_tag}🏁 <b>ГОНКИ И ЗАЕЗДЫ MERCEDES-AMG</b>\n\n"
        f"🚗 Твой болид: <b>{car['name'] if car else 'не выбран'}</b> (Рейтинг: <b>{rating}</b>)\n"
        f"⚡ Энергия: <b>{energy}/{p['max_energy']}</b>{regen} · 🪙 Баланс: <b>{fmt(p['coins'])} монет</b>\n\n"
        "Выбери режим гонки или командного соревнования:"
    )


@router.message(Command("race"))
async def cmd_race(message: Message):
    uid = message.from_user.id
    energy = await db.regen_energy(uid)
    await send_menu(message, uid, await race_menu_text(uid), race_menu_kb(energy))


@router.callback_query(F.data == "race")
async def cb_race(cb: CallbackQuery):
    await cb.answer()
    uid = cb.from_user.id
    energy = await db.regen_energy(uid)
    await safe_edit(cb, await race_menu_text(uid), race_menu_kb(energy))


async def solo_race_view(uid: int):
    energy = await db.regen_energy(uid)
    p = await db.get_player(uid)
    pc = await db.get_selected_car(uid)
    if not pc:
        return "⚠️ <b>Сначала выбери машину в гараже (/garage)!</b>", back_kb("garage:0")
    car = CAR_CATALOG[pc["car_key"]]
    rating = calc_stats(car, car_upgrades(pc))["rating"]
    wait = await db.minutes_to_next_energy(uid)
    regen = f"\n⏳ +1 ⚡ через {wait} мин" if wait else ""
    gif_tag = f"<a href='{data.AMG_GIFS['race']}'>&#8205;</a>"
    text = (
        f"{gif_tag}🏎 <b>ОДИНОЧНЫЙ ЗАЕЗД MERCEDES-AMG</b> 🎁\n\n"
        f"🚗 Твой болид: {car['emoji']} <b>{car['name']}</b> (Рейтинг: <b>{rating}</b>)\n"
        f"⚡ Энергия: <b>{energy}/{p['max_energy']}</b>{regen}\n\n"
        "Быстрый одиночный спринт против городского гонщика на улицах города!\n"
        "• ⚡ Расход: <b>1 энергия</b>\n"
        "• 🎁 Награды за победу: <b>4–6 🪙 монет</b>, <b>+50 XP</b>\n"
        "• 🎁 <b>Случайный подарок:</b> шанс выиграть бонусные монеты или восстановление энергии!\n\n"
        "<i>🔥 Главные командные соревнования, битва за кубки и дуэли со ставками — в командных чатах (/tournament, /duel, /boss)!</i>"
    )
    return text, solo_race_kb(energy)


@router.callback_query(F.data == "race_solo")
@router.callback_query(F.data == "race_street")
async def cb_solo_race(cb: CallbackQuery):
    return await cb.answer("🤝 Одиночные режимы убраны! Играйте командой в групповом чате: /boss, /chase, /tournament, /royale, /drag, /airdrop, /quiz, /wheel", show_alert=True)
    text, kb = await solo_race_view(cb.from_user.id)
    await safe_edit(cb, text, kb)


async def apply_result(uid: int, car_id: int, won: bool, race_type: str, mult: float = 1.0, car_rating: int = 150) -> str:
    p = await db.get_player(uid)
    r = calc_rewards(p["level"], race_type, mult, won, car_rating=car_rating)
    await db.car_race_result(car_id, won)
    await db.increment(uid, races_total=1, wins=int(won), losses=int(not won), reputation=r["rep"],
                       pvp_wins=int(won and race_type == "pvp"))
    coins = r.get("coins", 0)
    earned = 0
    if coins:
        earned = await db.grant_coins(uid, coins, reason=f"Гонка ({race_type})")
    lvl, up = await db.add_xp(uid, r["xp"])
    parts = [f"🪙 +{earned} монет", f"📈 +{r['xp']} XP"]
    if r["rep"]:
        parts.append(f"⭐ +{r['rep']}")
    text = " · ".join(parts)
    if up:
        text += f"\n🆙 <b>Новый уровень: {lvl}!</b>"
    return text


@router.callback_query(F.data == "race_solo_start")
@router.callback_query(F.data.startswith("race_street:"))
async def cb_solo_race_start(cb: CallbackQuery):
    return await cb.answer("🤝 Одиночные режимы убраны! Играйте командой в групповом чате: /boss, /chase, /tournament, /royale, /drag, /airdrop, /quiz, /wheel", show_alert=True)
    uid = cb.from_user.id
    pc = await db.get_selected_car(uid)
    if not pc:
        return await cb.answer("Сначала выбери машину в гараже!", show_alert=True)
    if not await db.use_energy(uid):
        wait = await db.minutes_to_next_energy(uid)
        await cb.answer()
        gif_tag = f"<a href='{data.AMG_GIFS['race']}'>&#8205;</a>"
        return await safe_edit(
            cb,
            f"{gif_tag}⚡ <b>ТОПЛИВНЫЙ БАК ПУСТ!</b>\n\n"
            f"Вся энергия израсходована. Следующая единица восстановится через <b>{wait} мин</b>.\n\n"
            "Не хочешь прерывать заезды? Заправься экспрессом:\n"
            "• ⚡ <b>100% энергии (полный бак)</b>\n"
            "• 🔥 <b>Нитро-ускорение (+15% к скорости)</b> на 2 часа во всех заездах!\n\n"
            "⭐️ <i>Всего 15 Telegram Stars или 60 игровых монет 🪙</i>",
            no_energy_kb()
        )
    await cb.answer("🏁 Погнали!")
    p = await db.get_player(uid)
    my_car = CAR_CATALOG[pc["car_key"]]
    me = cb.from_user.first_name or "Ты"
    if pc.get("plate"):
        me = f"{me} [{pc['plate']}]"

    # Подбираем сбалансированного соперника из списка
    opp = random.choice(STREET_OPPONENTS)
    opp_car = CAR_CATALOG[opp["car_key"]]

    my_immune = data.is_weakest_in_tier(pc["car_key"])
    opp_immune = data.is_weakest_in_tier(opp["car_key"])
    p_ins = bool(p.get("has_insurance"))
    from utils import is_salt_boosted
    my_spd_mult = 1.0
    if is_salt_boosted(p):
        my_spd_mult *= 1.25
    if db.is_nitro_boosted(p):
        my_spd_mult *= 1.15
    my_stats = calc_stats(my_car, car_upgrades(pc), speed_mult=my_spd_mult)

    my_color = pc.get("color")

    res = simulate_race(
        my_stats, calc_stats(opp_car, opp["upgrades"]), me, opp["name"],
        p1_insured=p_ins, p1_immune=my_immune, p2_immune=opp_immune,
        p1_color=my_color, p2_color=None
    )
    if res.get("insurance_saved") == 1:
        await db.update_player(uid, has_insurance=0)
    won = res["winner"] == 1

    rewards = await apply_result(uid, pc["id"], won, "street", opp["bonus_mult"], car_rating=my_stats["rating"])

    # Подарок за заезд (небольшой приятный сюрприз)
    gift_note = ""
    if won:
        gift_roll = random.random()
        if gift_roll < 0.20:
            extra_c = random.randint(3, 5)
            granted_extra = await db.grant_coins(uid, extra_c, reason="Подарочный бонус за заезд")
            if granted_extra > 0:
                gift_note = f"\n🎁 <b>ПОДАРОК ЗА ЗАЕЗД:</b> +{granted_extra} бонусных монет 🪙!"
        elif gift_roll < 0.30:
            await db.increment(uid, energy=1)
            gift_note = "\n🎁 <b>ПОДАРОК ЗА ЗАЕЗД:</b> ⚡ Восстановлена +1 энергия!"

    ach = await award_achievements(uid)

    import asyncio
    c1 = res.get("color1", "🏎")
    c2 = res.get("color2", "🏎")

    if res.get("round_steps"):
        for r_num, step in enumerate(res["round_steps"], start=1):
            stage_view = (
                f"🏁 <b>{my_car['name']}</b> vs <b>{opp_car['name']}</b>\n"
                f"<i>{c1} <b>{me}</b> против {c2} <b>{opp['name']}</b></i>\n\n"
                f"📍 <b>ЭТАП {r_num}/5</b>\n"
                f"{step}"
            )
            await safe_edit(cb, stage_view)
            await asyncio.sleep(1.0)

    gif_tag = f"<a href='{data.AMG_GIFS['win']}'>&#8205;</a>" if won and not res.get("crashed") else (f"<a href='{data.AMG_GIFS['crash']}'>&#8205;</a>" if res.get("crashed") else "")
    winner_name = f"{c1} <b>{me}</b>" if won else f"{c2} <b>{opp['name']}</b>"
    result = (f"🏆 ПОБЕДИТЕЛЬ: {winner_name} {res['margin']}" if won else f"💀 ПОБЕДИТЕЛЬ: {winner_name} {res['margin']}\n<i>Прокачай тачку в тюнинге и попробуй ещё раз!</i>")

    final_text = (
        f"{gif_tag}🏁 <b>ФИНИШНАЯ ЧЕРТА!</b>\n\n"
        f"🏎 <b>{my_car['name']}</b> vs <b>{opp_car['name']}</b>\n"
        f"<i>{c1} <b>{me}</b> против {c2} <b>{opp['name']}</b></i>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{res.get('saved_note', '')}"
        f"{res['narrative']}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{result}\n\n"
        f"{rewards}{gift_note}{ach}"
    )
    await safe_edit(cb, final_text, solo_race_result_kb())






# ── Режимы гонок (rmode:...) ─────────────────────────────────

@router.callback_query(F.data.startswith("rmode:"))
async def cb_race_mode(cb: CallbackQuery):
    mode = cb.data.split(":")[1]
    bot_info = await cb.bot.get_me()
    is_group = (cb.message.chat.type != "private")
    chat_id = cb.message.chat.id

    if mode == "adv":
        return await cb.answer("🤝 Одиночные режимы убраны! Играйте командой в групповом чате: /boss, /chase, /tournament, /royale, /drag, /airdrop, /quiz, /wheel", show_alert=True)

    if is_group:
        await cb.answer()
        from handlers.group_games import (
            start_tournament_recruitment, cmd_chase, cmd_boss, cmd_drag,
            cmd_royale, cmd_airdrop, cmd_quiz, cmd_wheel
        )
        if mode == "wheel":
            return await cmd_wheel(cb.message, caller=cb.from_user)
        elif mode == "chase":
            return await cmd_chase(cb.message, caller=cb.from_user)
        elif mode == "tourn":
            return await start_tournament_recruitment(chat_id, cb.from_user.first_name, cb.message.answer)
        elif mode == "boss":
            return await cmd_boss(cb.message, caller=cb.from_user)
        elif mode == "drag":
            return await cmd_drag(cb.message, caller=cb.from_user)
        elif mode == "royale":
            return await cmd_royale(cb.message, caller=cb.from_user)
        elif mode == "airdrop":
            return await cmd_airdrop(cb.message, caller=cb.from_user)
        elif mode == "quiz":
            return await cmd_quiz(cb.message, caller=cb.from_user)

    await cb.answer()
    from aiogram.types import InlineKeyboardButton as Btn, InlineKeyboardMarkup
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [Btn(text="➕ Запустить в группе (добавить бота)", url=f"https://t.me/{bot_info.username}?startgroup=true")],
        [Btn(text="◀️ Назад к гонкам", callback_data="race"),
         Btn(text="🏠 Главное меню", callback_data="menu")],
    ])

    info_cards = {
        "chase": (
            data.AMG_GIFS["crash"],
            "🚨 <b>ПОЛИЦЕЙСКАЯ ПОГОНЯ (/chase)</b>",
            "Патрульные перекрыли квартал! Вся банда действует сообща:\n\n"
            "• 💨 <b>Форсаж:</b> добавляет отрыв от погони\n"
            "• 🛡 <b>Прикрытие:</b> сбивает тревогу полиции\n"
            "• ↩️ <b>Вираж:</b> путает перехватчиков\n\n"
            "💰 Награда каждому участнику при отрыве: <b>монеты 🪙 и XP</b>!\n\n"
            "<i>Запусти режим в командном чате кнопкой ниже или командой /chase!</i>"
        ),
        "tourn": (
            data.AMG_GIFS["race"],
            "🏆 <b>ГРАН-ПРИ ЧАТА (/tournament, /grouprace)</b>",
            "Большой командный турнир от 2 участников!\n\n"
            "• Все участники собираются на стартовой решетке\n"
            "• Серия этапов с обгонами, динамическими сменами лидеров\n"
            "• Призовой подиум с кубками, солидными монетами и славой!\n\n"
            "<i>Запусти турнир в группе кнопкой ниже или командой /tournament!</i>"
        ),
        "boss": (
            data.AMG_GIFS["boss"],
            "👾 <b>РЕЙД НА БОССА АВТОБАНА (/boss)</b>",
            "Командная битва против элитных боссов (Шеф на броне-Гелике, Призрак на AMG ONE)!\n\n"
            "• Общее огромное здоровье (HP) босса на весь чат\n"
            "• Тараньте и наносите нитро-удары x2.5 всей бандой\n"
            "• Банк монет делится пропорционально урону!\n\n"
            "<i>Запусти рейд в группе кнопкой ниже или командой /boss!</i>"
        ),
        "drag": (
            data.AMG_GIFS["burnout"],
            "🚦 <b>ДРАГ-РЕЙСИНГ 402М (/drag)</b>",
            "Спринтерская дуэль двух гонщиков на 1/4 мили!\n\n"
            "• Проверка моментальной реакции на стартовом светофоре\n"
            "• Огромное значение имеют лошадиные силы и чип-тюнинг\n"
            "• Фальстарт = поражение! Кто идеален на старте — побеждает!\n\n"
            "<i>Запусти дуэль в группе кнопкой ниже или командой /drag!</i>"
        ),
        "royale": (
            data.AMG_GIFS["race"],
            "👑 <b>КОРОЛЕВСКАЯ БИТВА НА ВЫБЫВАНИЕ (/royale)</b>",
            "Массовое состязание на выживание от 2+ пилотов!\n\n"
            "• Каждый круг самый неудачливый участник выбывает\n"
            "• Только один гонщик дойдет до финиша\n"
            "• Победитель забирает джекпот: <b>+25 🪙 монет и +500 XP</b>!\n\n"
            "<i>Запусти битву в группе кнопкой ниже или командой /royale!</i>"
        ),
        "airdrop": (
            data.AMG_GIFS["boss"],
            "📦 <b>АИРДРОП КОНТЕЙНЕРА AMG (/airdrop)</b>",
            "В город сброшен контейнер с контрабандным грузом!\n\n"
            "• Банда собирается для вскрытия тяжелого замка (мин. 2 участника)\n"
            "• Топовый лут, монеты и детали распределяются между всеми, кто успел!\n\n"
            "<i>Сбрось аирдроп в группу кнопкой ниже или командой /airdrop!</i>"
        ),
        "wheel": (
            data.AMG_GIFS["wheel"],
            "🎰 <b>КОЛЕСО ФОРТУНЫ ЧАТА (/wheel)</b>",
            "Командное колесо для всей банды в групповом чате!\n\n"
            "• Крутите рулетку в чате — призы: монеты, энергия, опыт\n"
            "• Каждый гонщик чата — 1 бесплатный спин в сутки\n\n"
            "<i>Запусти колесо в группе кнопкой ниже или командой /wheel!</i>"
        ),
        "quiz": (
            data.AMG_GIFS["welcome"],
            "🧠 <b>АВТО-ВИКТОРИНА AMG (/quiz)</b>",
            "Битва эрудитов и знатоков мира Mercedes-AMG!\n\n"
            "• Уникальные вопросы об истории AMG, моторах V8 biturbo и легендах\n"
            "• Доступна раз в 3 часа в чате\n"
            "• Кто первый нажимает правильный ответ — мгновенно получает 🪙 монеты!\n\n"
            "<i>Запусти викторину в группе кнопкой ниже или командой /quiz!</i>"
        ),
    }

    card = info_cards.get(mode)
    if not card:
        return await safe_edit(cb, "Режим в разработке!", kb)

    gif_url, title, desc = card
    gif_tag = f"<a href='{gif_url}'>&#8205;</a>"
    await safe_edit(cb, f"{gif_tag}{title}\n\n{desc}", kb)


# ── PvP ──────────────────────────────────────────────────────

@router.callback_query(F.data == "race_pvp")
async def cb_pvp(cb: CallbackQuery, player: dict):
    await cb.answer()
    if cb.message.chat.type == "private":
        bot_info = await cb.bot.get_me()
        from aiogram.types import InlineKeyboardButton as Btn, InlineKeyboardMarkup
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [Btn(text="➕ Создать дуэль в группе (добавить бота)", url=f"https://t.me/{bot_info.username}?startgroup=true")],
            [Btn(text="📋 Открытые дуэли", callback_data="race_pvp_list")],
            [Btn(text="◀️ Назад к гонкам", callback_data="race"),
             Btn(text="🏠 Главное меню", callback_data="menu")],
        ])
        gif_tag = f"<a href='{data.AMG_GIFS['race']}'>&#8205;</a>"
        return await safe_edit(
            cb,
            f"{gif_tag}⚔️ <b>ДУЭЛИ 1х1 СО СТАВКАМИ (/duel)</b>\n\n"
            "Бросай персональный вызов любому участнику чата на монеты 🪙!\n\n"
            "• Ставки от 0 до 100 монет\n"
            "• Победитель забирает весь банк соперника\n"
            "• Учитываются рейтинг авто, чип-тюнинг и тактика обгонов\n\n"
            "<i>Добавь бота в командный чат или пиши /duel [ставка] в группе!</i>",
            kb
        )
    await safe_edit(cb, f"⚔️ <b>Создать вызов</b>\n\n🪙 Баланс: <b>{fmt(player['coins'])} монет</b>\n\n"
                        "Выбери ставку в монетах. Она замораживается, победитель забирает банк.\n"
                        "Вызов появится в этом чате — принять может любой участник.", pvp_bet_kb())


async def create_challenge(message: Message, user, bet: int, bet_type: str = "coins") -> str | None:
    """Создаёт вызов. Возвращает текст ошибки или None при успехе."""
    uid = user.id
    p = await db.get_player(uid)

    if bet < 0:
        return "Ставка не может быть отрицательной!"
    if bet > MAX_BET:
        return f"Максимальная ставка: {MAX_BET} 🪙 монет!"

    pc = await db.get_selected_car(uid)
    if not pc:
        return "Сначала выбери машину в гараже!"
    if await db.count_user_pending(uid) >= 3:
        return "У тебя уже 3 открытых вызова. Дождись соперников или отмени."

    if bet and not await db.spend_coins(uid, bet, reason="Ставка на PvP дуэль"):
        return f"Недостаточно монет 🪙 для ставки! У тебя: {fmt(p['coins'])} монет."

    race_id = await db.create_race(uid, pc["id"], bet, message.chat.id)
    async with db._connect() as _db:
        await _db.execute("UPDATE races SET bet_type = 'coins' WHERE id = ?", (race_id,))
        await _db.commit()

    car = CAR_CATALOG[pc["car_key"]]
    rating = calc_stats(car, car_upgrades(pc))["rating"]
    bet_t = f"🪙 Ставка: <b>{fmt(bet)} монет</b>" if bet else "🤝 Без ставки"
    await message.answer(
        f"⚔️ <b>ВЫЗОВ НА ДУЭЛЬ!</b>\n\n👤 {user.first_name} бросает вызов!\n"
        f"🚗 {car['emoji']} {car['name']} (рейтинг {rating})\n{bet_t}\n\nКто примет? 👇",
        reply_markup=pvp_challenge_kb(race_id),
    )
    return None


@router.callback_query(F.data.startswith("race_coin_bet:"))
@router.callback_query(F.data.startswith("race_pvp_bet:"))
async def cb_pvp_bet(cb: CallbackQuery):
    if cb.message.chat.type == "private":
        await cb.answer()
        return await team_only_redirect(cb, is_callback=True)
    try:
        bet = int(cb.data.split(":")[1])
    except ValueError:
        return await cb.answer()
    if bet > MAX_BET:
        bet = MAX_BET
    err = await create_challenge(cb.message, cb.from_user, bet, bet_type="coins")
    if err:
        return await cb.answer(err, show_alert=True)
    await cb.answer("Вызов создан!")
    await safe_edit(cb, "✅ Вызов опубликован ниже. Ждём соперника!", back_kb("race"))


@router.message(Command("duel"))
async def cmd_duel(message: Message, command: CommandObject):
    if message.chat.type == "private":
        return await team_only_redirect(message, is_callback=False)
    bet = 0
    if command.args:
        try:
            bet = int("".join(c for c in command.args if c.isdigit()))
        except ValueError:
            return await message.answer("Формат: <code>/duel 50</code> (ставка в монетах)")
    if bet > MAX_BET:
        return await message.answer(f"❌ Максимальная ставка в дуэли: <b>{MAX_BET} 🪙 монет</b>!")
    err = await create_challenge(message, message.from_user, bet, bet_type="coins")
    if err:
        await message.answer(f"❌ {err}")


@router.callback_query(F.data == "race_pvp_list")
async def cb_pvp_list(cb: CallbackQuery):
    await cb.answer()
    if cb.message.chat.type == "private":
        return await team_only_redirect(cb, is_callback=True)
    races = await db.get_pending_races(cb.from_user.id)
    text = "📋 <b>Открытые вызовы</b>\n\n" + ("Выбери, чей вызов принять:" if races else "Пока никто не бросил вызов 😴")
    await safe_edit(cb, text, pvp_list_kb(races))


@router.callback_query(F.data.startswith("race_cancel:"))
async def cb_pvp_cancel(cb: CallbackQuery):
    race = await db.get_race(int(cb.data.split(":")[1]))
    if not race:
        return await cb.answer("Вызов не найден", show_alert=True)
    if race["challenger_id"] != cb.from_user.id:
        return await cb.answer("Отменить может только автор вызова", show_alert=True)
    if not await db.cancel_race(race["id"]):
        return await cb.answer("Вызов уже неактивен", show_alert=True)
    if race["bet"]:
        await db.add_coins(race["challenger_id"], race["bet"], reason="Возврат отмены дуэли")
    await cb.answer("Вызов отменён, ставка возвращена")
    await safe_edit(cb, "❌ Вызов отменён автором.")


@router.callback_query(F.data.startswith("race_accept:"))
async def cb_pvp_accept(cb: CallbackQuery):
    uid = cb.from_user.id
    race = await db.get_race(int(cb.data.split(":")[1]))
    if not race or race["status"] != "pending":
        return await cb.answer("Вызов уже неактивен", show_alert=True)
    if race["challenger_id"] == uid:
        return await cb.answer("Нельзя принять свой вызов 🙂", show_alert=True)
    pc2 = await db.get_selected_car(uid)
    if not pc2:
        return await cb.answer("Сначала напиши боту /start и выбери машину!", show_alert=True)
    if not await db.use_energy(uid):
        return await cb.answer("⚡ Нет энергии!", show_alert=True)

    bet = race["bet"]
    p2 = await db.get_player(uid)

    if bet and not await db.spend_coins(uid, bet, reason="Принятие дуэли"):
        await db.increment(uid, energy=1)
        return await cb.answer(f"Нужно {fmt(bet)} монет 🪙 для ставки!", show_alert=True)

    if not await db.lock_race(race["id"], uid, pc2["id"]):
        if bet:
            await db.add_coins(uid, bet, reason="Возврат не успел принять")
        await db.increment(uid, energy=1)
        return await cb.answer("Кто-то принял вызов раньше тебя!", show_alert=True)

    await cb.answer("⚔️ Дуэль началась!")

    pc1 = await db.get_car(race["challenger_car_id"])
    p1 = await db.get_player(race["challenger_id"])
    if not pc1 or pc1["user_id"] != p1["user_id"]:
        pc1 = await db.get_selected_car(p1["user_id"]) or (await db.get_player_cars(p1["user_id"]))[0]
    c1, c2 = CAR_CATALOG[pc1["car_key"]], CAR_CATALOG[pc2["car_key"]]
    n1, n2 = p1["first_name"], cb.from_user.first_name or "Соперник"
    if pc1.get("plate"):
        n1 = f"{n1} [{pc1['plate']}]"
    if pc2.get("plate"):
        n2 = f"{n2} [{pc2['plate']}]"

    # Страховки и иммунитет для слабых машин в тире
    p1_ins = bool(p1.get("has_insurance"))
    p2_ins = bool(p2.get("has_insurance"))
    p1_imm = data.is_weakest_in_tier(pc1["car_key"])
    p2_imm = data.is_weakest_in_tier(pc2["car_key"])
    from utils import is_salt_boosted
    s1_mult = 1.25 if is_salt_boosted(p1) else 1.0
    s2_mult = 1.25 if is_salt_boosted(p2) else 1.0
    res = simulate_race(
        calc_stats(c1, car_upgrades(pc1), speed_mult=s1_mult),
        calc_stats(c2, car_upgrades(pc2), speed_mult=s2_mult),
        n1, n2, p1_insured=p1_ins, p2_insured=p2_ins, p1_immune=p1_imm, p2_immune=p2_imm,
        p1_color=pc1.get("color"), p2_color=pc2.get("color")
    )


    # Если страховка сработала, снимаем её
    if res.get("insurance_saved") == 1:
        await db.update_player(p1["user_id"], has_insurance=0)
    elif res.get("insurance_saved") == 2:
        await db.update_player(uid, has_insurance=0)

    winner_id = p1["user_id"] if res["winner"] == 1 else uid
    loser_id = uid if winner_id == p1["user_id"] else p1["user_id"]
    await db.finish_race(race["id"], winner_id)

    boost_note = ""
    if race.get("chat_id"):
        boost = await db.get_chat_boost(race["chat_id"])
        if boost:
            b_coins = 10
            await db.grant_coins(winner_id, b_coins, reason="Бонус буста чата x2 в дуэли")
            await db.add_xp(winner_id, 200)
            boost_note = f"\n🔥 <i>(Применён Буст чата x2: +{b_coins} 🪙 и +200 XP от спонсора {boost['sponsor_name']}!)</i>"

    if bet:
        await db.add_coins(winner_id, bet * 2, reason="Выигрыш в дуэли")
        bank = f"\n🪙 Банк: <b>{fmt(bet * 2)} монет</b> → {n1 if winner_id == p1['user_id'] else n2}{boost_note}"
    else:
        bank = boost_note

    s1 = calc_stats(c1, car_upgrades(pc1))
    s2 = calc_stats(c2, car_upgrades(pc2))
    w_car = pc1["id"] if winner_id == p1["user_id"] else pc2["id"]
    l_car = pc2["id"] if w_car == pc1["id"] else pc1["id"]
    w_rating = s1["rating"] if winner_id == p1["user_id"] else s2["rating"]
    l_rating = s2["rating"] if winner_id == p1["user_id"] else s1["rating"]
    w_rew = await apply_result(winner_id, w_car, True, "pvp", car_rating=w_rating)
    l_rew = await apply_result(loser_id, l_car, False, "pvp", car_rating=l_rating)
    ach = await award_achievements(winner_id) + await award_achievements(loser_id)

    c1_col = res.get("color1", c1["emoji"])
    c2_col = res.get("color2", c2["emoji"])
    wn = f"{c1_col} <b>{n1}</b>" if winner_id == p1["user_id"] else f"{c2_col} <b>{n2}</b>"
    ln = f"{c2_col} <b>{n2}</b>" if wn == f"{c1_col} <b>{n1}</b>" else f"{c1_col} <b>{n1}</b>"

    import asyncio
    head_base = f"⚔️ <b>ДУЭЛЬ</b>\n{c1_col} <b>{n1}</b> ({c1['name']})\n🆚\n{c2_col} <b>{n2}</b> ({c2['name']})\n\n"
    if res.get("round_steps"):
        cur_text = head_base + (res.get("saved_note") or "")
        for step in res["round_steps"]:
            cur_text += f"\n\n{step}"
            await safe_edit(cb, cur_text)
            await asyncio.sleep(1.0)
    else:
        cur_text = head_base + res["narrative"]

    gif_tag = f"<a href='{data.AMG_GIFS['win']}'>&#8205;</a>" if not res.get("crashed") else f"<a href='{data.AMG_GIFS['crash']}'>&#8205;</a>"
    await safe_edit(cb, f"{gif_tag}{cur_text}\n\n━━━━━━━━━━\n🏆 ПОБЕДИТЕЛЬ: {wn} {res['margin']}{bank}\n\n"
                        f"{wn}: {w_rew}\n{ln}: {l_rew}{ach}")



