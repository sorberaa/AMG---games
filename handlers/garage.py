from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

import db
from data import CAR_CATALOG, CAR_CLASS_EMOJIS, CAR_COLORS, UPGRADE_BONUSES, UPGRADE_DEFS, fmt, get_sell_price, get_upgrade_cost
from engine import calc_stats, car_upgrades
from kb import back_kb, car_actions_kb, garage_kb, paint_shop_kb, sell_confirm_kb, tuning_kb, upgrade_confirm_kb
from utils import award_achievements, safe_edit, send_menu

router = Router(name="garage")


import data

async def garage_view(user_id: int, page: int = 0):
    p = await db.get_player(user_id)
    cars = await db.get_player_cars(user_id)
    sel = next((c for c in cars if c["id"] == p["selected_car_id"]), None)
    sel_name = CAR_CATALOG[sel["car_key"]]["name"] if sel else "не выбрана"
    gif_tag = f"<a href='{data.AMG_GIFS['garage']}'>&#8205;</a>"
    text = f"{gif_tag}🚗 <b>Твой гараж</b> ({len(cars)} авто)\n\nОсновная: <b>{sel_name}</b>\n\nНажми на машину:"
    return text, garage_kb(cars, p["selected_car_id"], page)


def stats_block(st: dict) -> str:
    return (
        f"⚡ Мощность: <b>{st['power']:.0f}</b> л.с.\n"
        f"🏁 Макс. скорость: <b>{st['speed']:.0f}</b> км/ч\n"
        f"🚀 0-100: <b>{st['acceleration']:.1f}</b> с\n"
        f"🎯 Управляемость: <b>{st['handling']:.0f}</b>\n"
        f"⚖️ Масса: <b>{st['weight']:.0f}</b> кг\n"
        f"📊 Рейтинг: <b>{st['rating']}</b>"
    )


async def own_car(cb: CallbackQuery, car_id: int):
    car = await db.get_car(car_id)
    if not car or car["user_id"] != cb.from_user.id:
        await cb.answer("Машина не найдена", show_alert=True)
        return None
    return car


@router.message(Command("garage"))
async def cmd_garage(message: Message):
    text, kb = await garage_view(message.from_user.id)
    await send_menu(message, message.from_user.id, text, kb)


@router.callback_query(F.data.startswith("garage:"))
async def cb_garage(cb: CallbackQuery):
    await cb.answer()
    text, kb = await garage_view(cb.from_user.id, int(cb.data.split(":")[1]))
    await safe_edit(cb, text, kb)


async def car_detail_text(pc: dict) -> str:
    car = CAR_CATALOG[pc["car_key"]]
    st = calc_stats(car, car_upgrades(pc))
    ups = " ".join(f"{u['emoji']}{pc[f'{k}_level']}" for k, u in UPGRADE_DEFS.items())
    c_key = pc.get("color")
    c_info = CAR_COLORS.get(c_key) if c_key else None
    c_str = f"{c_info['emoji']} {c_info['name']}" if c_info else "Заводской (серебристый 🔘)"
    return (
        f"{car['emoji']} <b>{car['name']}</b>\n"
        f"{CAR_CLASS_EMOJIS[car['cls']]} Класс {car['cls']}\n<i>{car['desc']}</i>\n\n"
        f"🎨 Цвет кузова: <b>{c_str}</b>\n\n"
        f"{stats_block(st)}\n\n🔧 Тюнинг: {ups}\n"
        f"🏁 Гонок: {pc['total_races']} · 🏆 Побед: {pc['total_wins']}"
    )


@router.callback_query(F.data.startswith("car:"))
async def cb_car(cb: CallbackQuery):
    pc = await own_car(cb, int(cb.data.split(":")[1]))
    if not pc:
        return
    await cb.answer()
    p = await db.get_player(cb.from_user.id)
    await safe_edit(cb, await car_detail_text(pc), car_actions_kb(pc["id"], p["selected_car_id"] == pc["id"]))


@router.callback_query(F.data.startswith("car_select:"))
async def cb_select(cb: CallbackQuery):
    pc = await own_car(cb, int(cb.data.split(":")[1]))
    if not pc:
        return
    await db.select_car(cb.from_user.id, pc["id"])
    await cb.answer(f"✅ {CAR_CATALOG[pc['car_key']]['name']} — основная машина!")
    await safe_edit(cb, await car_detail_text(pc), car_actions_kb(pc["id"], True))


@router.callback_query(F.data.startswith("car_sell:"))
async def cb_sell(cb: CallbackQuery):
    pc = await own_car(cb, int(cb.data.split(":")[1]))
    if not pc:
        return
    if await db.count_cars(cb.from_user.id) <= 1:
        await cb.answer("Нельзя продать единственную машину!", show_alert=True)
        return
    await cb.answer()
    car = CAR_CATALOG[pc["car_key"]]
    price = get_sell_price(car, pc)
    await safe_edit(cb, f"💰 Продать <b>{car['name']}</b> за <b>${fmt(price)}</b>?\n\n"
                        "<i>Салон выкупает за 60% цены + 40% вложений в тюнинг.</i>",
                    sell_confirm_kb(pc["id"], price))


@router.callback_query(F.data.startswith("car_sell_yes:"))
async def cb_sell_yes(cb: CallbackQuery):
    pc = await own_car(cb, int(cb.data.split(":")[1]))
    if not pc:
        return
    if await db.count_cars(cb.from_user.id) <= 1:
        await cb.answer("Нельзя продать единственную машину!", show_alert=True)
        return
    car = CAR_CATALOG[pc["car_key"]]
    price = get_sell_price(car, pc)
    await db.remove_car(pc["id"])
    await db.add_money(cb.from_user.id, price)
    p = await db.get_player(cb.from_user.id)
    if not p["selected_car_id"]:
        cars = await db.get_player_cars(cb.from_user.id)
        if cars:
            await db.select_car(cb.from_user.id, cars[0]["id"])
    await cb.answer(f"Продано за ${fmt(price)}", show_alert=True)
    text, kb = await garage_view(cb.from_user.id)
    await safe_edit(cb, text, kb)


# ── Покраска ─────────────────────────────────────────────────

@router.callback_query(F.data.startswith("car_paint:"))
async def cb_car_paint(cb: CallbackQuery):
    pc = await own_car(cb, int(cb.data.split(":")[1]))
    if not pc:
        return
    await cb.answer()
    p = await db.get_player(cb.from_user.id)
    car = CAR_CATALOG[pc["car_key"]]
    c_key = pc.get("color")
    c_info = CAR_COLORS.get(c_key) if c_key else None
    c_str = f"{c_info['emoji']} {c_info['name']}" if c_info else "Заводской (серебристый 🔘)"
    gif_tag = f"<a href='{data.AMG_GIFS['garage']}'>&#8205;</a>"
    text = (
        f"{gif_tag}🎨 <b>Покрасочный цех AMG Performance Studio</b>\n\n"
        f"Автомобиль: {car['emoji']} <b>{car['name']}</b>\n"
        f"Текущий цвет: <b>{c_str}</b>\n"
        f"💰 Твой баланс: <b>${fmt(p['money'])}</b>\n\n"
        "Выбери цвет кузова! В гонках бот будет закреплять за тобой именно твой цвет болида:"
    )
    await safe_edit(cb, text, paint_shop_kb(pc["id"], c_key))


@router.callback_query(F.data.startswith("car_paint_buy:"))
async def cb_car_paint_buy(cb: CallbackQuery):
    _, car_id_str, color_key = cb.data.split(":")
    pc = await own_car(cb, int(car_id_str))
    if not pc or color_key not in CAR_COLORS:
        return
    if pc.get("color") == color_key:
        return await cb.answer("Этот цвет уже нанесен на машину!", show_alert=True)

    c_info = CAR_COLORS[color_key]
    price = c_info["price"]
    if not await db.spend_money(cb.from_user.id, price):
        return await cb.answer("Недостаточно денег для покраски! 💸", show_alert=True)

    await db.paint_car(pc["id"], color_key)
    await cb.answer(f"✅ Автомобиль перекрашен в {c_info['name']}!", show_alert=True)
    updated_pc = await db.get_car(pc["id"])
    p = await db.get_player(cb.from_user.id)
    car = CAR_CATALOG[updated_pc["car_key"]]
    gif_tag = f"<a href='{data.AMG_GIFS['garage']}'>&#8205;</a>"
    text = (
        f"{gif_tag}🎨 <b>Покрасочный цех AMG Performance Studio</b>\n\n"
        f"Автомобиль: {car['emoji']} <b>{car['name']}</b>\n"
        f"Текущий цвет: <b>{c_info['emoji']} {c_info['name']}</b> ✅\n"
        f"💰 Твой баланс: <b>${fmt(p['money'])}</b>\n\n"
        "Выбери цвет кузова! В гонках бот будет закреплять за тобой именно твой цвет болида:"
    )
    await safe_edit(cb, text, paint_shop_kb(updated_pc["id"], color_key))


# ── Тюнинг ───────────────────────────────────────────────────

async def tuning_view(cb: CallbackQuery, pc: dict):
    p = await db.get_player(cb.from_user.id)
    car = CAR_CATALOG[pc["car_key"]]
    st = calc_stats(car, car_upgrades(pc))
    text = (f"🔧 <b>Тюнинг-ателье</b>\n{car['emoji']} {car['name']}\n\n{stats_block(st)}\n\n"
            f"💰 Баланс: ${fmt(p['money'])}\n\nВыбери узел для улучшения:")
    await safe_edit(cb, text, tuning_kb(pc, p["money"]))


@router.callback_query(F.data == "tuning")
async def cb_tuning(cb: CallbackQuery):
    pc = await db.get_selected_car(cb.from_user.id)
    if not pc:
        await cb.answer("Сначала выбери машину в гараже!", show_alert=True)
        return
    await cb.answer()
    await tuning_view(cb, pc)


@router.callback_query(F.data.startswith("tuning:"))
async def cb_tuning_car(cb: CallbackQuery):
    pc = await own_car(cb, int(cb.data.split(":")[1]))
    if not pc:
        return
    await cb.answer()
    await tuning_view(cb, pc)


@router.callback_query(F.data.startswith("upgrade:"))
async def cb_upgrade(cb: CallbackQuery):
    _, car_id, key = cb.data.split(":")
    pc = await own_car(cb, int(car_id))
    if not pc or key not in UPGRADE_DEFS:
        return
    lvl = pc[f"{key}_level"]
    u = UPGRADE_DEFS[key]
    if lvl >= u["max_level"]:
        await cb.answer("Уже на максимуме!", show_alert=True)
        return
    await cb.answer()
    car = CAR_CATALOG[pc["car_key"]]
    cost = get_upgrade_cost(car["price"], key, lvl)
    old = calc_stats(car, car_upgrades(pc))
    ups = car_upgrades(pc)
    ups[key] = lvl + 1
    new = calc_stats(car, ups)
    names = {"power": "⚡ Мощность", "speed": "🏁 Скорость", "acceleration": "🚀 0-100",
             "handling": "🎯 Управляемость", "weight": "⚖️ Масса"}
    diff = []
    for k, n in names.items():
        if abs(new[k] - old[k]) > 0.01:
            fmt_s = "{:.1f}" if k == "acceleration" else "{:.0f}"
            diff.append(f"{n}: {fmt_s.format(old[k])} → <b>{fmt_s.format(new[k])}</b>")
    diff.append(f"📊 Рейтинг: {old['rating']} → <b>{new['rating']}</b>")
    await safe_edit(cb, f"{u['emoji']} <b>{u['name']}</b>: ур. {lvl} → {lvl + 1}\n\n" + "\n".join(diff) +
                    f"\n\n💰 Стоимость: <b>${fmt(cost)}</b>", upgrade_confirm_kb(pc["id"], key, cost))


@router.callback_query(F.data.startswith("upgrade_yes:"))
async def cb_upgrade_yes(cb: CallbackQuery):
    _, car_id, key = cb.data.split(":")
    pc = await own_car(cb, int(car_id))
    if not pc or key not in UPGRADE_DEFS:
        return
    lvl = pc[f"{key}_level"]
    if lvl >= UPGRADE_DEFS[key]["max_level"]:
        await cb.answer("Уже на максимуме!", show_alert=True)
        return
    cost = get_upgrade_cost(CAR_CATALOG[pc["car_key"]]["price"], key, lvl)
    if not await db.spend_money(cb.from_user.id, cost):
        await cb.answer("Недостаточно денег! 💸", show_alert=True)
        return
    await db.upgrade_car(pc["id"], key, lvl + 1)
    await cb.answer(f"✅ {UPGRADE_DEFS[key]['name']} улучшен до {lvl + 1} уровня!")
    ach = await award_achievements(cb.from_user.id)
    if ach:
        await cb.message.answer(ach.strip())
    await tuning_view(cb, await db.get_car(pc["id"]))

