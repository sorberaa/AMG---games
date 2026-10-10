from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message

import db
import data
from data import CAR_CATALOG, STREET_OPPONENTS, fmt
from engine import calc_rewards, calc_stats, car_upgrades, simulate_race
from kb import back_kb, pvp_bet_kb, pvp_challenge_kb, pvp_list_kb, race_menu_kb, race_result_kb, street_opponents_kb
from utils import award_achievements, safe_edit, send_menu

router = Router(name="race")
MAX_BET = 1_000_000


async def race_menu_text(uid: int) -> str:
    energy = await db.regen_energy(uid)
    p = await db.get_player(uid)
    pc = await db.get_selected_car(uid)
    car = CAR_CATALOG[pc["car_key"]] if pc else None
    rating = calc_stats(car, car_upgrades(pc))["rating"] if pc else 0
    wait = await db.minutes_to_next_energy(uid)
    regen = f"\n⏳ +1 ⚡ через {wait} мин" if wait else ""
    return (f"🏁 <b>Гонки</b>\n\n🚗 {car['name'] if car else 'нет машины'} (рейтинг {rating})\n"
            f"⚡ Энергия: <b>{energy}/{p['max_energy']}</b>{regen}\n\nВыбери режим:")


@router.message(Command("race"))
async def cmd_race(message: Message):
    await send_menu(message, message.from_user.id, await race_menu_text(message.from_user.id), race_menu_kb())


@router.callback_query(F.data == "race")
async def cb_race(cb: CallbackQuery):
    await cb.answer()
    await safe_edit(cb, await race_menu_text(cb.from_user.id), race_menu_kb())


@router.callback_query(F.data == "race_street")
async def cb_street(cb: CallbackQuery):
    await cb.answer()
    uid = cb.from_user.id
    p = await db.get_player(uid)
    defeated = p.get("defeated_opponents", 0)
    pc = await db.get_selected_car(uid)
    my = calc_stats(CAR_CATALOG[pc["car_key"]], car_upgrades(pc))["rating"] if pc else 0
    lines = []
    for i, o in enumerate(STREET_OPPONENTS):
        r = calc_stats(CAR_CATALOG[o["car_key"]], o["upgrades"])["rating"]
        status = "✅" if i < defeated else ("⚔️" if i == defeated else "🔒")
        lines.append(f"{status} {o['name']}: рейтинг {r}")
    await safe_edit(cb, f"🏎 <b>Уличные гонки (Лестница боссов)</b>\n\nТвой рейтинг: <b>{my}</b>\n\n" + "\n".join(lines) +
                    "\n\n<i>Побеждай по порядку! Доход и монеты зависят от крутости твоей тачки.</i>", street_opponents_kb(defeated))


@router.callback_query(F.data.startswith("race_street_locked:"))
async def cb_street_locked(cb: CallbackQuery):
    await cb.answer("🔒 Сначала одолей предыдущего соперника!", show_alert=True)


async def apply_result(uid: int, car_id: int, won: bool, race_type: str, mult: float = 1.0, car_rating: int = 150) -> str:
    p = await db.get_player(uid)
    r = calc_rewards(p["level"], race_type, mult, won, car_rating=car_rating)
    await db.car_race_result(car_id, won)
    await db.increment(uid, races_total=1, wins=int(won), losses=int(not won), reputation=r["rep"],
                       pvp_wins=int(won and race_type == "pvp"))
    await db.add_money(uid, r["money"])
    lvl, up = await db.add_xp(uid, r["xp"])
    coins = await db.grant_coins(uid, r["coins"])
    parts = [f"💰 +${fmt(r['money'])}", f"📈 +{r['xp']} XP"]
    if coins:
        parts.append(f"🪙 +{coins}")
    if r["rep"]:
        parts.append(f"⭐ +{r['rep']}")
    text = " · ".join(parts)
    if up:
        text += f"\n🆙 <b>Новый уровень: {lvl}!</b>"
    return text


@router.callback_query(F.data.startswith("race_street:"))
async def cb_street_race(cb: CallbackQuery):
    uid = cb.from_user.id
    opp_idx = int(cb.data.split(":")[1])
    try:
        opp = STREET_OPPONENTS[opp_idx]
    except (ValueError, IndexError):
        return await cb.answer("Соперник не найден", show_alert=True)

    p = await db.get_player(uid)
    defeated = p.get("defeated_opponents", 0)
    if opp_idx > defeated:
        return await cb.answer("🔒 Сначала победи предыдущего соперника!", show_alert=True)

    # Лимит 5 гонок в день против слабых соперников (easy)
    from datetime import datetime
    today = datetime.utcnow().strftime("%Y-%m-%d")
    is_easy = opp["difficulty"] == "easy"
    easy_count = p.get("easy_races_today", 0) if p.get("easy_races_date") == today else 0

    if is_easy and easy_count >= 5:
        return await cb.answer("⚠️ Лимит 5 заездов в день против слабых соперников исчерпан! Бросай вызов более сильным гонщикам — они без лимита!", show_alert=True)

    pc = await db.get_selected_car(uid)
    if not pc:
        return await cb.answer("Сначала выбери машину в гараже!", show_alert=True)
    if not await db.use_energy(uid):
        wait = await db.minutes_to_next_energy(uid)
        return await cb.answer(f"⚡ Нет энергии! Следующая через {wait} мин.\nМожно восполнить в магазине монет 🪙",
                               show_alert=True)
    await cb.answer("🏁 Погнали!")
    my_car = CAR_CATALOG[pc["car_key"]]
    opp_car = CAR_CATALOG[opp["car_key"]]
    me = cb.from_user.first_name or "Ты"

    # Иммунитет от аварии для самых слабых машин в каждом тире
    my_immune = data.is_weakest_in_tier(pc["car_key"])
    opp_immune = data.is_weakest_in_tier(opp["car_key"])

    p_ins = bool(p.get("has_insurance"))
    my_stats = calc_stats(my_car, car_upgrades(pc))
    my_color = pc.get("color")
    res = simulate_race(
        my_stats, calc_stats(opp_car, opp["upgrades"]), me, opp["name"],
        p1_insured=p_ins, p1_immune=my_immune, p2_immune=opp_immune,
        p1_color=my_color, p2_color=None
    )
    if res.get("insurance_saved") == 1:
        await db.update_player(uid, has_insurance=0)
    won = res["winner"] == 1

    # Учитываем легкий заезд в счетчике лимита
    if is_easy:
        new_cnt = 1 if p.get("easy_races_date") != today else easy_count + 1
        await db.update_player(uid, easy_races_today=new_cnt, easy_races_date=today)

    # Если победил текущего максимального босса — открываем следующего!
    if won and opp_idx == defeated:
        await db.update_player(uid, defeated_opponents=defeated + 1)

    rewards = await apply_result(uid, pc["id"], won, "street", opp["bonus_mult"], car_rating=my_stats["rating"])
    extra = {"ghost_slayer"} if won and opp["difficulty"] == "extreme" else set()
    ach = await award_achievements(uid, extra)

    # Пошаговая трансляция этапов с задержкой в 1 секунду
    import asyncio
    c1 = res.get("color1", "🏎")
    c2 = res.get("color2", "🏎")
    head_base = f"🏁 <b>{my_car['name']}</b> vs <b>{opp_car['name']}</b>\n<i>{c1} <b>{me}</b> против {c2} <b>{opp['name']}</b></i>\n\n"
    if res.get("round_steps"):
        cur_text = head_base + (res.get("saved_note") or "")
        for step in res["round_steps"]:
            cur_text += f"\n\n{step}"
            await safe_edit(cb, cur_text)
            await asyncio.sleep(1.0)
    else:
        cur_text = head_base + res["narrative"]

    gif_tag = f"<a href='{data.AMG_GIFS['win']}'>&#8205;</a>" if won and not res.get("crashed") else (f"<a href='{data.AMG_GIFS['crash']}'>&#8205;</a>" if res.get("crashed") else "")
    limit_note = f"\n<i>Заездов со слабачками сегодня: {easy_count + 1}/5</i>" if is_easy else ""
    winner_name = f"{c1} <b>{me}</b>" if won else f"{c2} <b>{opp['name']}</b>"
    result = (f"🏆 ПОБЕДИТЕЛЬ: {winner_name} {res['margin']}" if won else f"💀 ПОБЕДИТЕЛЬ: {winner_name} {res['margin']}\n<i>Прокачай тачку в тюнинге и попробуй снова!</i>")
    await safe_edit(cb, f"{gif_tag}{cur_text}\n\n━━━━━━━━━━\n{result}\n{rewards}{limit_note}{ach}", race_result_kb())






# ── PvP ──────────────────────────────────────────────────────

@router.callback_query(F.data == "race_pvp")
async def cb_pvp(cb: CallbackQuery, player: dict):
    await cb.answer()
    await safe_edit(cb, f"⚔️ <b>Создать вызов</b>\n\n💰 Баланс: ${fmt(player['money'])}\n\n"
                        "Выбери ставку. Она замораживается, победитель забирает банк.\n"
                        "Вызов появится в этом чате — принять может любой.", pvp_bet_kb())


async def create_challenge(message: Message, user, bet: int, bet_type: str = "money") -> str | None:
    """Создаёт вызов. Возвращает текст ошибки или None при успехе."""
    uid = user.id
    from datetime import datetime, timedelta
    p = await db.get_player(uid)

    if bet_type == "coins":
        if bet <= 0:
            return "Ставка монетами должна быть больше 0!"
        # Лимит 1 час на дуэль на монеты
        if p.get("last_coin_duel"):
            try:
                last_dt = datetime.strptime(p["last_coin_duel"], "%Y-%m-%d %H:%M:%S")
                diff = datetime.utcnow() - last_dt
                if diff < timedelta(hours=1):
                    rem_mins = int((timedelta(hours=1) - diff).total_seconds() // 60)
                    return f"⏳ Лимит на гонки на монеты: 1 раз в час! Осталось подождать {rem_mins} мин."
            except Exception:
                pass
        if not await db.spend_coins(uid, bet, reason="Ставка на PvP дуэль"):
            return "Недостаточно монет 🪙 для ставки!"
    else:
        if bet < 0 or bet > MAX_BET:
            return f"Ставка от 0 до ${fmt(MAX_BET)}"
        if bet and not await db.spend_money(uid, bet):
            return "Недостаточно денег для ставки!"

    pc = await db.get_selected_car(uid)
    if not pc:
        return "Сначала выбери машину в гараже!"
    if await db.count_user_pending(uid) >= 3:
        return "У тебя уже 3 открытых вызова. Дождись соперников или отмени."

    race_id = await db.create_race(uid, pc["id"], bet, message.chat.id)
    if bet_type == "coins":
        async with db._connect() as _db:
            await _db.execute("UPDATE races SET bet_type = 'coins' WHERE id = ?", (race_id,))
            await _db.commit()

    car = CAR_CATALOG[pc["car_key"]]
    rating = calc_stats(car, car_upgrades(pc))["rating"]
    bet_t = f"🪙 Ставка: <b>{fmt(bet)} монет</b>" if bet_type == "coins" else (f"💵 Ставка: <b>${fmt(bet)}</b>" if bet else "🤝 Без ставки")
    await message.answer(
        f"⚔️ <b>ВЫЗОВ НА ДУЭЛЬ!</b>\n\n👤 {user.first_name} бросает вызов!\n"
        f"🚗 {car['emoji']} {car['name']} (рейтинг {rating})\n{bet_t}\n\nКто примет? 👇",
        reply_markup=pvp_challenge_kb(race_id),
    )
    return None


@router.callback_query(F.data.startswith("race_coin_bet:"))
async def cb_coin_bet(cb: CallbackQuery):
    try:
        bet = int(cb.data.split(":")[1])
    except ValueError:
        return await cb.answer()
    err = await create_challenge(cb.message, cb.from_user, bet, bet_type="coins")
    if err:
        return await cb.answer(err, show_alert=True)
    await cb.answer("Вызов на монеты создан!")
    await safe_edit(cb, "✅ Вызов на монеты опубликован ниже! Лимит: 1 раз в час.", back_kb("race"))


@router.callback_query(F.data.startswith("race_pvp_bet:"))
async def cb_pvp_bet(cb: CallbackQuery):
    try:
        bet = int(cb.data.split(":")[1])
    except ValueError:
        return await cb.answer()
    err = await create_challenge(cb.message, cb.from_user, bet, bet_type="money")
    if err:
        return await cb.answer(err, show_alert=True)
    await cb.answer("Вызов создан!")
    await safe_edit(cb, "✅ Вызов опубликован ниже. Ждём соперника!", back_kb("race"))


@router.message(Command("duel"))
async def cmd_duel(message: Message, command: CommandObject):
    bet = 0
    bet_type = "money"
    if command.args:
        args_lower = command.args.lower()
        if "монет" in args_lower or "coin" in args_lower or "🪙" in args_lower:
            bet_type = "coins"
        try:
            bet = int("".join(c for c in command.args if c.isdigit()))
        except ValueError:
            return await message.answer("Формат: <code>/duel 5000</code> или <code>/duel 50 монет</code>")
    err = await create_challenge(message, message.from_user, bet, bet_type=bet_type)
    if err:
        await message.answer(f"❌ {err}")


@router.callback_query(F.data == "race_pvp_list")
async def cb_pvp_list(cb: CallbackQuery):
    await cb.answer()
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
        if race.get("bet_type") == "coins":
            await db.add_coins_admin(race["challenger_id"], race["bet"], reason="Возврат отмены дуэли")
        else:
            await db.add_money(race["challenger_id"], race["bet"])
    await cb.answer("Вызов отменён, ставка возвращена")
    await safe_edit(cb, "❌ Вызов отменён автором.")


@router.callback_query(F.data.startswith("race_accept:"))
async def cb_pvp_accept(cb: CallbackQuery):
    uid = cb.from_user.id
    from datetime import datetime, timedelta
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
    is_coins = race.get("bet_type") == "coins"
    p2 = await db.get_player(uid)

    if is_coins:
        if p2.get("last_coin_duel"):
            try:
                last_dt = datetime.strptime(p2["last_coin_duel"], "%Y-%m-%d %H:%M:%S")
                diff = datetime.utcnow() - last_dt
                if diff < timedelta(hours=1):
                    rem_mins = int((timedelta(hours=1) - diff).total_seconds() // 60)
                    await db.increment(uid, energy=1)
                    return await cb.answer(f"⏳ Твой лимит на гонки на монеты: подожди {rem_mins} мин.", show_alert=True)
            except Exception:
                pass
        if not await db.spend_coins(uid, bet, reason="Принятие дуэли на монеты"):
            await db.increment(uid, energy=1)
            return await cb.answer(f"Нужно {fmt(bet)} монет 🪙 для ставки!", show_alert=True)
    else:
        if bet and not await db.spend_money(uid, bet):
            await db.increment(uid, energy=1)
            return await cb.answer(f"Нужно ${fmt(bet)} для ставки!", show_alert=True)

    if not await db.lock_race(race["id"], uid, pc2["id"]):
        if bet:
            if is_coins:
                await db.add_coins_admin(uid, bet, reason="Возврат не успел принять")
            else:
                await db.add_money(uid, bet)
        await db.increment(uid, energy=1)
        return await cb.answer("Кто-то принял вызов раньше тебя!", show_alert=True)

    await cb.answer("⚔️ Дуэль началась!")

    pc1 = await db.get_car(race["challenger_car_id"])
    p1 = await db.get_player(race["challenger_id"])
    if not pc1 or pc1["user_id"] != p1["user_id"]:
        pc1 = await db.get_selected_car(p1["user_id"]) or (await db.get_player_cars(p1["user_id"]))[0]
    c1, c2 = CAR_CATALOG[pc1["car_key"]], CAR_CATALOG[pc2["car_key"]]
    n1, n2 = p1["first_name"], cb.from_user.first_name or "Соперник"

    # Страховки и иммунитет для слабых машин в тире
    p1_ins = bool(p1.get("has_insurance"))
    p2_ins = bool(p2.get("has_insurance"))
    p1_imm = data.is_weakest_in_tier(pc1["car_key"])
    p2_imm = data.is_weakest_in_tier(pc2["car_key"])
    res = simulate_race(
        calc_stats(c1, car_upgrades(pc1)), calc_stats(c2, car_upgrades(pc2)),
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

    # Фиксируем кулдаун для монетной дуэли
    if is_coins:
        now_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        await db.update_player(p1["user_id"], last_coin_duel=now_time)
        await db.update_player(uid, last_coin_duel=now_time)
        await db.add_coins_admin(winner_id, bet * 2, reason="Выигрыш в дуэли на монеты")
        bank = f"\n🪙 Банк: <b>{fmt(bet * 2)} монет</b> → {n1 if winner_id == p1['user_id'] else n2}"
    else:
        if bet:
            await db.add_money(winner_id, bet * 2)
        bank = f"\n💵 Банк: <b>${fmt(bet * 2)}</b> → {n1 if winner_id == p1['user_id'] else n2}" if bet else ""

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



