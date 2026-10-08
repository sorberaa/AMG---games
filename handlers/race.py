from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message

import db
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
    pc = await db.get_selected_car(cb.from_user.id)
    my = calc_stats(CAR_CATALOG[pc["car_key"]], car_upgrades(pc))["rating"] if pc else 0
    lines = []
    for o in STREET_OPPONENTS:
        r = calc_stats(CAR_CATALOG[o["car_key"]], o["upgrades"])["rating"]
        lines.append(f"• {o['name']}: рейтинг {r}")
    await safe_edit(cb, f"🏎 <b>Уличные гонки</b>\n\nТвой рейтинг: <b>{my}</b>\n\n" + "\n".join(lines) +
                    "\n\n<i>Чем сильнее соперник — тем больше награда.</i>", street_opponents_kb())


async def apply_result(uid: int, car_id: int, won: bool, race_type: str, mult: float = 1.0) -> str:
    p = await db.get_player(uid)
    r = calc_rewards(p["level"], race_type, mult, won)
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
    try:
        opp = STREET_OPPONENTS[int(cb.data.split(":")[1])]
    except (ValueError, IndexError):
        return await cb.answer("Соперник не найден", show_alert=True)
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
    res = simulate_race(calc_stats(my_car, car_upgrades(pc)), calc_stats(opp_car, opp["upgrades"]), me, opp["name"])
    won = res["winner"] == 1
    rewards = await apply_result(uid, pc["id"], won, "street", opp["bonus_mult"])
    extra = {"ghost_slayer"} if won and opp["difficulty"] == "extreme" else set()
    ach = await award_achievements(uid, extra)
    head = (f"🏁 <b>{my_car['name']}</b> vs <b>{opp_car['name']}</b>\n"
            f"<i>{me} против «{opp['name']}»</i>\n\n")
    result = (f"🏆 <b>ПОБЕДА {res['margin']}</b>" if won else f"💀 <b>Поражение {res['margin']}</b>\n"
              "<i>Прокачай тачку в тюнинге и попробуй снова!</i>")
    await safe_edit(cb, f"{head}{res['narrative']}\n\n━━━━━━━━━━\n{result}\n{rewards}{ach}", race_result_kb())


# ── PvP ──────────────────────────────────────────────────────

@router.callback_query(F.data == "race_pvp")
async def cb_pvp(cb: CallbackQuery, player: dict):
    await cb.answer()
    await safe_edit(cb, f"⚔️ <b>Создать вызов</b>\n\n💰 Баланс: ${fmt(player['money'])}\n\n"
                        "Выбери ставку. Она замораживается, победитель забирает банк.\n"
                        "Вызов появится в этом чате — принять может любой.", pvp_bet_kb())


async def create_challenge(message: Message, user, bet: int) -> str | None:
    """Создаёт вызов. Возвращает текст ошибки или None при успехе."""
    uid = user.id
    if bet < 0 or bet > MAX_BET:
        return f"Ставка от 0 до ${fmt(MAX_BET)}"
    pc = await db.get_selected_car(uid)
    if not pc:
        return "Сначала выбери машину в гараже!"
    if await db.count_user_pending(uid) >= 3:
        return "У тебя уже 3 открытых вызова. Дождись соперников или отмени."
    if bet and not await db.spend_money(uid, bet):
        return "Недостаточно денег для ставки!"
    race_id = await db.create_race(uid, pc["id"], bet, message.chat.id)
    car = CAR_CATALOG[pc["car_key"]]
    rating = calc_stats(car, car_upgrades(pc))["rating"]
    bet_t = f"💵 Ставка: <b>${fmt(bet)}</b>" if bet else "🤝 Без ставки"
    await message.answer(
        f"⚔️ <b>ВЫЗОВ НА ДУЭЛЬ!</b>\n\n👤 {user.first_name} бросает вызов!\n"
        f"🚗 {car['emoji']} {car['name']} (рейтинг {rating})\n{bet_t}\n\nКто примет? 👇",
        reply_markup=pvp_challenge_kb(race_id),
    )
    return None


@router.callback_query(F.data.startswith("race_pvp_bet:"))
async def cb_pvp_bet(cb: CallbackQuery):
    try:
        bet = int(cb.data.split(":")[1])
    except ValueError:
        return await cb.answer()
    err = await create_challenge(cb.message, cb.from_user, bet)
    if err:
        return await cb.answer(err, show_alert=True)
    await cb.answer("Вызов создан!")
    await safe_edit(cb, "✅ Вызов опубликован ниже. Ждём соперника!", back_kb("race"))


@router.message(Command("duel"))
async def cmd_duel(message: Message, command: CommandObject):
    bet = 0
    if command.args:
        try:
            bet = int(command.args.replace(" ", "").replace("$", "").replace(",", ""))
        except ValueError:
            return await message.answer("Формат: <code>/duel 5000</code>")
    err = await create_challenge(message, message.from_user, bet)
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
        await db.add_money(race["challenger_id"], race["bet"])
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
    if bet and not await db.spend_money(uid, bet):
        await db.increment(uid, energy=1)
        return await cb.answer(f"Нужно ${fmt(bet)} для ставки!", show_alert=True)
    if not await db.lock_race(race["id"], uid, pc2["id"]):
        if bet:
            await db.add_money(uid, bet)
        await db.increment(uid, energy=1)
        return await cb.answer("Кто-то принял вызов раньше тебя!", show_alert=True)
    await cb.answer("⚔️ Дуэль началась!")

    pc1 = await db.get_car(race["challenger_car_id"])
    p1 = await db.get_player(race["challenger_id"])
    if not pc1 or pc1["user_id"] != p1["user_id"]:  # машину продали
        pc1 = await db.get_selected_car(p1["user_id"]) or (await db.get_player_cars(p1["user_id"]))[0]
    c1, c2 = CAR_CATALOG[pc1["car_key"]], CAR_CATALOG[pc2["car_key"]]
    n1, n2 = p1["first_name"], cb.from_user.first_name or "Соперник"
    res = simulate_race(calc_stats(c1, car_upgrades(pc1)), calc_stats(c2, car_upgrades(pc2)), n1, n2)
    winner_id = p1["user_id"] if res["winner"] == 1 else uid
    loser_id = uid if winner_id == p1["user_id"] else p1["user_id"]
    await db.finish_race(race["id"], winner_id)
    if bet:
        await db.add_money(winner_id, bet * 2)

    w_car = pc1["id"] if winner_id == p1["user_id"] else pc2["id"]
    l_car = pc2["id"] if w_car == pc1["id"] else pc1["id"]
    w_rew = await apply_result(winner_id, w_car, True, "pvp")
    l_rew = await apply_result(loser_id, l_car, False, "pvp")
    ach = await award_achievements(winner_id) + await award_achievements(loser_id)
    wn = n1 if winner_id == p1["user_id"] else n2
    ln = n2 if wn == n1 else n1
    bank = f"\n💵 Банк: <b>${fmt(bet * 2)}</b> → {wn}" if bet else ""
    await safe_edit(cb, f"⚔️ <b>ДУЭЛЬ</b>\n{c1['emoji']} {n1} ({c1['name']})\n🆚\n{c2['emoji']} {n2} ({c2['name']})\n\n"
                        f"{res['narrative']}\n\n━━━━━━━━━━\n🏆 <b>{wn}</b> побеждает {res['margin']}{bank}\n\n"
                        f"<b>{wn}:</b> {w_rew}\n<b>{ln}:</b> {l_rew}{ach}")

