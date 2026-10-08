import random

from aiogram import F, Router
from aiogram.types import CallbackQuery

import db
from data import (CAR_CATALOG, CAR_CLASS_EMOJIS, CAR_CLASS_NAMES, CASE_DROPS, COIN_SHOP,
                  MAX_ENERGY_CAP, fmt, get_cars_by_class)
from engine import calc_stats
from kb import back_kb, buy_confirm_kb, coin_shop_kb, shop_classes_kb, shop_list_kb
from utils import award_achievements, safe_edit

router = Router(name="shop")


@router.callback_query(F.data == "shop")
async def cb_shop(cb: CallbackQuery, player: dict):
    await cb.answer()
    await safe_edit(cb, f"🏪 <b>Автосалон Mercedes-AMG</b>\n\n💰 Баланс: ${fmt(player['money'])}\n\nВыбери класс:",
                    shop_classes_kb())


@router.callback_query(F.data.startswith("shop_class:"))
async def cb_shop_class(cb: CallbackQuery, player: dict):
    cls = cb.data.split(":")[1]
    cars = get_cars_by_class(cls)
    if not cars:
        await cb.answer("Нет такого класса", show_alert=True)
        return
    await cb.answer()
    owned = {c["car_key"] for c in await db.get_player_cars(cb.from_user.id)}
    await safe_edit(cb, f"{CAR_CLASS_EMOJIS[cls]} <b>Класс {cls} — {CAR_CLASS_NAMES[cls]}</b>\n\n"
                        f"💰 Баланс: ${fmt(player['money'])} · 📊 Ур. {player['level']}",
                    shop_list_kb(cars, player["level"], owned))


@router.callback_query(F.data.startswith("shop_car:"))
async def cb_shop_car(cb: CallbackQuery, player: dict):
    key = cb.data.split(":")[1]
    car = CAR_CATALOG.get(key)
    if not car:
        await cb.answer("Машина не найдена", show_alert=True)
        return
    await cb.answer()
    st = calc_stats(car, {})
    owned = await db.player_has_car_key(cb.from_user.id, key)
    problems = []
    if player["level"] < car["level_req"]:
        problems.append(f"🔒 Нужен уровень {car['level_req']}")
    if player["money"] < car["price"]:
        problems.append(f"💸 Не хватает ${fmt(car['price'] - player['money'])}")
    status = "\n".join(problems) if problems else "✅ Можно купить!"
    if owned:
        status += "\n<i>У тебя уже есть такая — можно взять вторую.</i>"
    text = (f"{car['emoji']} <b>{car['name']}</b>\n{CAR_CLASS_EMOJIS[car['cls']]} Класс {car['cls']}\n"
            f"<i>{car['desc']}</i>\n\n"
            f"⚡ {car['power']} л.с. · 🏁 {car['speed']} км/ч\n🚀 0-100: {car['acceleration']} с · "
            f"🎯 {car['handling']} · ⚖️ {car['weight']} кг\n📊 Рейтинг: <b>{st['rating']}</b>\n\n"
            f"💰 Цена: <b>${fmt(car['price'])}</b> · Ур. {car['level_req']}+\n\n{status}")
    await safe_edit(cb, text, buy_confirm_kb(key, car["cls"], not problems))


@router.callback_query(F.data.startswith("buy_yes:"))
async def cb_buy(cb: CallbackQuery):
    key = cb.data.split(":")[1]
    car = CAR_CATALOG.get(key)
    p = await db.get_player(cb.from_user.id)
    if not car:
        return await cb.answer("Машина не найдена", show_alert=True)
    if p["level"] < car["level_req"]:
        return await cb.answer(f"Нужен уровень {car['level_req']}!", show_alert=True)
    if await db.count_cars(cb.from_user.id) >= 30:
        return await cb.answer("Гараж переполнен (макс. 30)! Продай что-нибудь.", show_alert=True)
    if car["price"] > 0 and not await db.spend_money(cb.from_user.id, car["price"]):
        return await cb.answer("Недостаточно денег! 💸", show_alert=True)
    car_id = await db.add_car(cb.from_user.id, key)
    await db.select_car(cb.from_user.id, car_id)
    await cb.answer()
    ach = await award_achievements(cb.from_user.id)
    await safe_edit(cb, f"🎉 <b>Поздравляем с покупкой!</b>\n\n{car['emoji']} {car['name']} теперь в твоём гараже "
                        f"и выбрана основной.{ach}", back_kb("garage:0", "🚗 В гараж"))


# ── Магазин монет ────────────────────────────────────────────

@router.callback_query(F.data == "cshop")
async def cb_coin_shop(cb: CallbackQuery, player: dict):
    await cb.answer()
    items = "\n".join(f"{i['name']} — <b>{i['price']} 🪙</b>\n<i>{i['desc']}</i>" for i in COIN_SHOP.values())
    await safe_edit(cb, f"🪙 <b>Магазин монет</b>\n\nУ тебя: <b>{fmt(player['coins'])} 🪙</b>\n\n{items}\n\n"
                        "<i>Монеты даются за гонки, бонус дня и достижения.</i>", coin_shop_kb())


def roll_case(case_key: str):
    drops = CASE_DROPS[case_key]
    return random.choices(drops, weights=[d[0] for d in drops])[0]


@router.callback_query(F.data.startswith("cbuy:"))
async def cb_coin_buy(cb: CallbackQuery):
    key = cb.data.split(":")[1]
    item = COIN_SHOP.get(key)
    uid = cb.from_user.id
    if not item:
        return await cb.answer("Товар не найден", show_alert=True)
    p = await db.get_player(uid)

    if key == "energy_refill" and p["energy"] >= p["max_energy"]:
        return await cb.answer("Энергия и так полная ⚡", show_alert=True)
    if key == "energy_plus" and p["max_energy"] >= MAX_ENERGY_CAP:
        return await cb.answer("Достигнут максимум энергии!", show_alert=True)
    if key == "insurance" and p.get("has_insurance"):
        return await cb.answer("У тебя уже действует страховка! 🛡", show_alert=True)
    if key.startswith("case") and await db.count_cars(uid) >= 30:
        return await cb.answer("Гараж переполнен! Продай машину перед открытием кейса.", show_alert=True)
    if not await db.spend_coins(uid, item["price"], reason=f"Покупка: {item['name']}"):
        return await cb.answer("Недостаточно монет 🪙", show_alert=True)

    await cb.answer()
    result = ""
    if key == "energy_refill":
        await db.update_player(uid, energy=p["max_energy"])
        result = f"⚡ Энергия восстановлена до {p['max_energy']}!"
    elif key == "energy_plus":
        await db.update_player(uid, max_energy=p["max_energy"] + 1, energy=p["energy"] + 1)
        result = f"🔋 Максимум энергии теперь {p['max_energy'] + 1}!"
    elif key == "insurance":
        await db.update_player(uid, has_insurance=1)
        result = "🛡 <b>Страховка AMG оформлена!</b>\nОна спасет твою машину при риске аварии."
    elif key == "chat_nitro":
        from datetime import datetime, timedelta
        until = (datetime.utcnow() + timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
        await db.update_player(uid, chat_nitro_until=until)
        result = "⚡ <b>Нитро для чата активировано на 24 часа!</b>\n+10% мощности в битвах с боссами и чат-заездах."
    elif key == "gold_wrap":
        await db.update_player(uid, gold_wrap=1)
        result = "✨ <b>Золотой винил установлен!</b>\nМашина сияет, повышая твой авторитет и награды."
    elif key == "xp_boost":
        lvl, up = await db.add_xp(uid, 500)
        result = "📈 +500 XP!" + (f"\n🆙 <b>Новый уровень: {lvl}!</b>" if up else "")

    else:
        _, kind, value = roll_case(key)
        if kind == "money":
            await db.add_money(uid, value)
            result = f"💰 Выпало: <b>${fmt(value)}</b>"
        elif kind == "xp":
            lvl, up = await db.add_xp(uid, value)
            result = f"📈 Выпало: <b>{value} XP</b>" + (f"\n🆙 Новый уровень: {lvl}!" if up else "")
        else:
            await db.add_car(uid, value)
            car = CAR_CATALOG[value]
            result = f"🚗 Выпала машина: {car['emoji']} <b>{car['name']}</b>!\nОна уже в гараже."
        result = f"{item['name']} открыт...\n\n" + result
    ach = await award_achievements(uid)
    await safe_edit(cb, f"{result}{ach}", back_kb("cshop", "🪙 В магазин"))

