from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

import db
from data import CAR_CATALOG, CAR_CLASS_EMOJIS, CAR_COLORS, UPGRADE_BONUSES, UPGRADE_DEFS, fmt, get_sell_price, get_upgrade_cost
from engine import calc_stats, car_upgrades
from kb import back_kb, car_actions_kb, car_plate_kb, garage_kb, paint_shop_kb, sell_confirm_kb, tuning_kb, upgrade_confirm_kb
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
    plate = pc.get("plate")
    plate_str = f"<code>[{plate}]</code>" if plate else "<i>не установлен</i>"
    return (
        f"{car['emoji']} <b>{car['name']}</b>\n"
        f"{CAR_CLASS_EMOJIS[car['cls']]} Класс {car['cls']}\n<i>{car['desc']}</i>\n\n"
        f"🎨 Цвет кузова: <b>{c_str}</b>\n"
        f"🏷 Госномер: <b>{plate_str}</b>\n\n"
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
    await safe_edit(cb, f"💰 Продать <b>{car['name']}</b> за <b>{fmt(price)} 🪙</b>?\n\n"
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
    await db.add_coins(cb.from_user.id, price, reason=f"Продажа {car['name']}")
    p = await db.get_player(cb.from_user.id)
    if not p["selected_car_id"]:
        cars = await db.get_player_cars(cb.from_user.id)
        if cars:
            await db.select_car(cb.from_user.id, cars[0]["id"])
    await cb.answer(f"Продано за {fmt(price)} 🪙", show_alert=True)
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
        f"🪙 Твой баланс: <b>{fmt(p['coins'])} монет</b>\n\n"
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
    if not await db.spend_coins(cb.from_user.id, price, reason=f"Покраска {color_key}"):
        return await cb.answer("Недостаточно монет для покраски! 🪙", show_alert=True)

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
        f"🪙 Твой баланс: <b>{fmt(p['coins'])} монет</b>\n\n"
        "Выбери цвет кузова! В гонках бот будет закреплять за тобой именно твой цвет болида:"
    )
    await safe_edit(cb, text, paint_shop_kb(updated_pc["id"], color_key))


# ── Тюнинг ───────────────────────────────────────────────────

async def tuning_view(cb: CallbackQuery, pc: dict):
    p = await db.get_player(cb.from_user.id)
    car = CAR_CATALOG[pc["car_key"]]
    st = calc_stats(car, car_upgrades(pc))
    text = (f"🔧 <b>Тюнинг-ателье</b>\n{car['emoji']} {car['name']}\n\n{stats_block(st)}\n\n"
            f"🪙 Баланс: <b>{fmt(p['coins'])} монет</b>\n\nВыбери узел для улучшения:")
    await safe_edit(cb, text, tuning_kb(pc, p["coins"]))


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
    p = await db.get_player(cb.from_user.id)
    can_afford = (p["coins"] >= cost)
    warn_text = "" if can_afford else f"\n\n⚠️ <i>Не хватает {fmt(cost - p['coins'])} монет. Пополни в магазине звёзд!</i>"
    await safe_edit(cb, f"{u['emoji']} <b>{u['name']}</b>: ур. {lvl} → {lvl + 1}\n\n" + "\n".join(diff) +
                    f"\n\n🪙 Стоимость: <b>{fmt(cost)} монет</b>{warn_text}",
                    upgrade_confirm_kb(pc["id"], key, cost, can_afford=can_afford))


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
    if not await db.spend_coins(cb.from_user.id, cost, reason=f"Тюнинг {key}"):
        from kb import not_enough_coins_kb
        p = await db.get_player(cb.from_user.id)
        deficit = cost - p["coins"]
        await cb.answer()
        return await safe_edit(
            cb,
            f"🔧 <b>НЕ ХВАТАЕТ МОНЕТ ДЛЯ ТЮНИНГА!</b>\n\n"
            f"Деталь: {UPGRADE_DEFS[key]['emoji']} <b>{UPGRADE_DEFS[key]['name']}</b>\n"
            f"Стоимость: <b>{fmt(cost)} 🪙</b> · У тебя: <b>{fmt(p['coins'])} 🪙</b>\n"
            f"Не хватает: <b>{fmt(deficit)} 🪙</b>\n\n"
            "Пополни баланс монет за Telegram Stars ⭐️ без ожидания!",
            not_enough_coins_kb(f"tuning:{pc['id']}")
        )
    await db.upgrade_car(pc["id"], key, lvl + 1)
    await cb.answer(f"✅ {UPGRADE_DEFS[key]['name']} улучшен до {lvl + 1} уровня!")
    ach = await award_achievements(cb.from_user.id)
    if ach:
        await cb.message.answer(ach.strip())
    await tuning_view(cb, await db.get_car(pc["id"]))


# ── Блатные госномера ────────────────────────────────────────

@router.callback_query(F.data.startswith("car_plate:"))
async def cb_car_plate(cb: CallbackQuery):
    pc = await own_car(cb, int(cb.data.split(":")[1]))
    if not pc:
        return
    await cb.answer()
    p = await db.get_player(cb.from_user.id)
    car = CAR_CATALOG[pc["car_key"]]
    plate = pc.get("plate")
    plate_str = f"<code>[{plate}]</code>" if plate else "<i>не установлен</i>"
    has_plates = bool(p.get("custom_plates", 0) > 0 or p.get("is_admin"))

    if has_plates:
        status_info = (
            f"✅ <b>Доступно установок номеров: {p.get('custom_plates', 0)}</b>\n\n"
            "Выбери готовый блатной номер кнопкой ниже или установи свой собственный текст командой:\n"
            "👉 <code>/plate ТВОЙ_НОМЕР</code>"
        )
    else:
        status_info = (
            "⭐️ <b>Стоимость установки: 29 ⭐️ (Telegram Stars)</b>\n"
            "<i>(Включает право на любой номер + 40 золотых монет 🪙 в подарок!)</i>\n\n"
            "Выбери готовый номер из списка или нажми «Купить установку номера», чтобы задать абсолютно любой свой текст!"
        )

    text = (
        f"🏷 <b>БЛАТНЫЕ ГОСНОМЕРА НА БОЛИД</b> 🏷\n\n"
        f"🚗 Автомобиль: <b>{car['name']}</b>\n"
        f"Текущий номер: <b>{plate_str}</b>\n\n"
        "Блатной номер выделяет твой болид на сходках, отображается в заездах, дуэлях и турнирах чата!\n\n"
        f"{status_info}"
    )
    await safe_edit(cb, text, car_plate_kb(pc["id"], has_plates, plate))


@router.callback_query(F.data.startswith("plate_set:"))
async def cb_plate_set(cb: CallbackQuery):
    parts = cb.data.split(":")
    car_id = int(parts[1])
    plate_val = parts[2]
    pc = await own_car(cb, car_id)
    if not pc:
        return

    p = await db.get_player(cb.from_user.id)
    has_plates = bool(p.get("custom_plates", 0) > 0 or p.get("is_admin"))

    if not has_plates:
        await cb.answer()
        from kb import stars_pack_kb
        return await safe_edit(
            cb,
            f"⭐️ <b>Для установки номера требуется пакет «Блатной госномер»!</b>\n\n"
            f"Выбранный номер: <code>[{plate_val}]</code>\n"
            "⭐️ Стоимость: <b>29 ⭐️</b>\n"
            "🎁 Бонус в комплекте: <b>+40 монет 🪙</b> на игровой баланс!\n\n"
            "Приобрети пакет ниже в 1 клик через Telegram Stars:",
            stars_pack_kb("plate_custom", 29)
        )

    if not p.get("is_admin"):
        await db.increment(cb.from_user.id, custom_plates=-1)

    await db.set_car_plate(car_id, plate_val)
    await cb.answer(f"✅ Номер [{plate_val}] установлен!", show_alert=True)
    pc = await db.get_car(car_id)
    p = await db.get_player(cb.from_user.id)
    await safe_edit(cb, await car_detail_text(pc), car_actions_kb(pc["id"], p["selected_car_id"] == pc["id"]))


@router.callback_query(F.data.startswith("plate_remove:"))
async def cb_plate_remove(cb: CallbackQuery):
    car_id = int(cb.data.split(":")[1])
    pc = await own_car(cb, car_id)
    if not pc:
        return
    await db.set_car_plate(car_id, None)
    await cb.answer("🗑 Номер снят!", show_alert=True)
    pc = await db.get_car(car_id)
    p = await db.get_player(cb.from_user.id)
    await safe_edit(cb, await car_detail_text(pc), car_actions_kb(pc["id"], p["selected_car_id"] == pc["id"]))


@router.message(Command("plate"))
async def cmd_plate(message: Message):
    uid = message.from_user.id
    p = await db.get_player(uid)
    if not p:
        return await message.answer("Сначала напиши /start!")

    sel_id = p.get("selected_car_id")
    if not sel_id:
        return await message.answer("У тебя не выбрана основная машина в гараже! Выбери её в /garage.")

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.answer(
            "🏷 <b>Установка блатного госномера на выбранный болид:</b>\n\n"
            "Используй формат:\n"
            "<code>/plate А 777 АА 77</code>\n"
            "или <code>/plate BOSS 01</code>\n\n"
            "<i>Длина: от 2 до 12 символов. Номер будет красоваться в гонках и чатах!</i>"
        )

    new_plate = args[1].strip().upper()
    if len(new_plate) < 2 or len(new_plate) > 12:
        return await message.answer("⚠️ Длина номера должна быть от 2 до 12 символов!")

    if not p.get("is_admin") and p.get("custom_plates", 0) <= 0:
        from kb import stars_pack_kb
        return await message.answer(
            f"⭐️ <b>Для установки номера требуется пакет «Блатной госномер» (29 ⭐️)!</b>\n\n"
            f"Ты получишь:\n"
            f"• Установку любого своего номера: <code>[{new_plate}]</code>\n"
            f"• +40 золотых монет 🪙 в подарок!\n\n"
            f"Приобрети пакет в Звёздном Магазине:",
            reply_markup=stars_pack_kb("plate_custom", 29)
        )

    if not p.get("is_admin"):
        await db.increment(uid, custom_plates=-1)

    await db.set_car_plate(sel_id, new_plate)
    car_obj = await db.get_car(sel_id)
    car_name = CAR_CATALOG[car_obj["car_key"]]["name"] if car_obj else "болид"

    await message.answer(
        f"🏷 <b>БЛАТНОЙ ГОСНОМЕР УСПЕШНО УСТАНОВЛЕН!</b>\n\n"
        f"🚗 Автомобиль: <b>{car_name}</b>\n"
        f"Новый номер: <code>[{new_plate}]</code> ✨\n\n"
        f"<i>Номер зафиксирован во всех протоколах гонок и чатах!</i>"
    )


