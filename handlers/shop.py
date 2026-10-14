import random

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton as Btn, InlineKeyboardMarkup, Message

import data
import db
from data import (CAR_CATALOG, CAR_CLASS_EMOJIS, CAR_CLASS_NAMES, CASE_DROPS, CASES, COIN_SHOP,
                  MAX_ENERGY_CAP, fmt, get_cars_by_class)
from engine import calc_stats
from kb import back_kb, buy_confirm_kb, cases_kb, coin_shop_kb, not_enough_coins_kb, shop_classes_kb, shop_list_kb
from utils import award_achievements, safe_edit

router = Router(name="shop")


@router.callback_query(F.data == "shop")
async def cb_shop(cb: CallbackQuery, player: dict):
    await cb.answer()
    await safe_edit(cb, f"🏪 <b>Автосалон Mercedes-AMG</b>\n\n🪙 Баланс: <b>{fmt(player['coins'])} монет</b>\n\nВыбери класс:",
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
                        f"🪙 Баланс: <b>{fmt(player['coins'])} монет</b> · 📊 Ур. {player['level']}",
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
    need_coins = False
    if player["level"] < car["level_req"]:
        problems.append(f"🔒 Нужен уровень {car['level_req']}")
    if player["coins"] < car["price"]:
        deficit = car["price"] - player["coins"]
        problems.append(f"🪙 Не хватает <b>{fmt(deficit)} монет</b> (пополни за ⭐️)")
        need_coins = True
    status = "\n".join(problems) if problems else "✅ Можно купить!"
    if owned:
        status += "\n<i>У тебя уже есть такая — можно взять вторую.</i>"
    text = (f"{car['emoji']} <b>{car['name']}</b>\n{CAR_CLASS_EMOJIS[car['cls']]} Класс {car['cls']}\n"
            f"<i>{car['desc']}</i>\n\n"
            f"⚡ {car['power']} л.с. · 🏁 {car['speed']} км/ч\n🚀 0-100: {car['acceleration']} с · "
            f"🎯 {car['handling']} · ⚖️ {car['weight']} кг\n📊 Рейтинг: <b>{st['rating']}</b>\n\n"
            f"🪙 Цена: <b>{fmt(car['price'])} монет</b> · Ур. {car['level_req']}+\n\n{status}")
    await safe_edit(cb, text, buy_confirm_kb(key, car["cls"], not problems, need_coins=need_coins))


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
    if car["price"] > 0 and not await db.spend_coins(cb.from_user.id, car["price"], reason=f"Покупка авто {car['name']}"):
        deficit = car["price"] - p["coins"]
        await cb.answer()
        return await safe_edit(
            cb,
            f"🪙 <b>НЕ ХВАТАЕТ МОНЕТ ДЛЯ ПОКУПКИ!</b>\n\n"
            f"Автомобиль: {car['emoji']} <b>{car['name']}</b>\n"
            f"Стоимость: <b>{fmt(car['price'])} 🪙</b>\n"
            f"Твой баланс: <b>{fmt(p['coins'])} 🪙</b> (не хватает <b>{fmt(deficit)} 🪙</b>)\n\n"
            "Пополни баланс монет за Telegram Stars ⭐️ без ограничений по суточным лимитам!",
            not_enough_coins_kb(f"shop_car:{key}")
        )
    car_id = await db.add_car(cb.from_user.id, key)
    await db.select_car(cb.from_user.id, car_id)
    await cb.answer()
    ach = await award_achievements(cb.from_user.id)
    await safe_edit(cb, f"🎉 <b>Поздравляем с покупкой!</b>\n\n{car['emoji']} {car['name']} теперь в твоём гараже "
                        f"и выбрана основной.{ach}", back_kb("garage:0", "🚗 В гараж"))


# ── Магазин за монеты ─────────────────────────────────────────

@router.message(Command("cshop"))
async def cmd_cshop(message: Message):
    p = await db.get_player(message.from_user.id)
    items = "\n".join(f"{i['name']} — <b>{i['price']} 🪙</b>\n<i>{i['desc']}</i>" for k, i in COIN_SHOP.items() if not k.startswith("case_"))
    await message.answer(
        f"🪙 <b>Магазин AMG</b>\n\nУ тебя: <b>{fmt(p['coins'])} 🪙</b>\n\n{items}\n\n"
        "<i>Монеты даются за командные заезды, дуэли, рейды на боссов и бонус дня!</i>",
        reply_markup=coin_shop_kb()
    )


@router.callback_query(F.data == "cshop")
async def cb_coin_shop(cb: CallbackQuery, player: dict):
    await cb.answer()
    items = "\n".join(f"{i['name']} — <b>{i['price']} 🪙</b>\n<i>{i['desc']}</i>" for k, i in COIN_SHOP.items() if not k.startswith("case_"))
    await safe_edit(cb, f"🪙 <b>Магазин AMG</b>\n\nУ тебя: <b>{fmt(player['coins'])} 🪙</b>\n\n{items}\n\n"
                        "<i>Монеты даются за командные заезды, дуэли, рейды на боссов и бонус дня!</i>", coin_shop_kb())


# ── Сундуки и Кейсы ───────────────────────────────────────────

def roll_case(case_key: str):
    drops = CASE_DROPS.get(case_key, CASE_DROPS["case_basic"])
    return random.choices(drops, weights=[d[0] for d in drops])[0]


async def render_cases_view(uid: int):
    p = await db.get_player(uid)
    gif_tag = f"<a href='{data.AMG_GIFS.get('chest', data.AMG_GIFS['welcome'])}'>&#8205;</a>"
    text = (
        f"{gif_tag}🧰 <b>СУНДУКИ И КЕЙСЫ AMG PERFORMANCE</b> 🧰\n\n"
        f"Твой баланс: <b>{fmt(p['coins'])} 🪙 монет</b>\n\n"
        "Испытай удачу и выбей редкий суперкар AMG, запас монет или горы опыта!\n\n"
        "📦 <b>Базовый сундук (100 🪙):</b>\n"
        "• Монеты: до 1 000 🪙 · Опыт: 300 XP\n"
        "• Машины: A35, CLA 45 S, C63 S\n\n"
        "🎁 <b>Элитный кейс AMG (350 🪙):</b>\n"
        "• Монеты: до 800 🪙 · Опыт: 1 500 XP\n"
        "• Машины: E63 S, AMG GT, GT 63 S, GT R, GT Black Series, AMG ONE\n\n"
        "👑 <b>Легендарный ларец ONE (750 🪙):</b>\n"
        "• Куш: до 2 500 🪙 · Опыт: 3 000 XP\n"
        "• Шанс сорвать гиперкары: GT 63 S E, GT R PRO, GT Black Series и <b>AMG ONE</b>!\n\n"
        "Выбери сундук для открытия:"
    )
    return text, cases_kb()


@router.message(Command("cases", "chests", "box"))
async def cmd_cases(message: Message):
    text, kb = await render_cases_view(message.from_user.id)
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "cases")
async def cb_cases(cb: CallbackQuery):
    await cb.answer()
    text, kb = await render_cases_view(cb.from_user.id)
    await safe_edit(cb, text, kb)


@router.callback_query(F.data.startswith("case_open:"))
async def cb_case_open(cb: CallbackQuery):
    key = cb.data.split(":")[1]
    c_info = CASES.get(key)
    if not c_info:
        return await cb.answer("Сундук не найден", show_alert=True)
    uid = cb.from_user.id
    p = await db.get_player(uid)
    if p["coins"] < c_info["price"]:
        deficit = c_info["price"] - p["coins"]
        await cb.answer()
        return await safe_edit(
            cb,
            f"🧰 <b>НЕ ХВАТАЕТ МОНЕТ ДЛЯ ОТКРЫТИЯ КЕЙСА!</b>\n\n"
            f"Сундук: {c_info['emoji']} <b>{c_info['name']}</b>\n"
            f"Стоимость: <b>{c_info['price']} 🪙</b>\n"
            f"Твой баланс: <b>{p['coins']} 🪙</b> (не хватает <b>{deficit} 🪙</b>)\n\n"
            "Пополни баланс монет за Telegram Stars ⭐️ и сорви суперкар прямо сейчас!",
            not_enough_coins_kb("cases")
        )
    if await db.count_cars(uid) >= 30:
        return await cb.answer("Гараж переполнен! Продай машину перед открытием.", show_alert=True)

    if not await db.spend_coins(uid, c_info["price"], reason=f"Открытие: {c_info['name']}"):
        deficit = c_info["price"] - p["coins"]
        await cb.answer()
        return await safe_edit(
            cb,
            f"🧰 <b>НЕ ХВАТАЕТ МОНЕТ ДЛЯ ОТКРЫТИЯ КЕЙСА!</b>\n\n"
            f"Сундук: {c_info['emoji']} <b>{c_info['name']}</b>\n"
            f"Стоимость: <b>{c_info['price']} 🪙</b>\n"
            f"Твой баланс: <b>{p['coins']} 🪙</b> (не хватает <b>{deficit} 🪙</b>)\n\n"
            "Пополни баланс монет за Telegram Stars ⭐️!",
            not_enough_coins_kb("cases")
        )

    await cb.answer("🧰 Открываем сундук...")
    _, kind, value = roll_case(key)
    res_text = ""
    if kind == "coins" or kind == "money":
        await db.add_coins(uid, value, reason=f"Выигрыш в кейсе {c_info['name']}")
        res_text = f"🪙 <b>ВЫИГРЫШ:</b> +{fmt(value)} 🪙 монет!"
    elif kind == "xp":
        lvl, up = await db.add_xp(uid, value)
        res_text = f"📈 <b>ВЫИГРЫШ:</b> +{value} XP опыта гонщика!" + (f"\n🆙 <b>Новый уровень: {lvl}!</b>" if up else "")
    else:
        await db.add_car(uid, value)
        car = CAR_CATALOG[value]
        res_text = f"🚗 <b>ДЖЕКПОТ! ВЫПАЛ АВТОМОБИЛЬ:</b>\n{car['emoji']} <b>{car['name']}</b> (Класс {car['cls']})!\nМашина уже доставлена в твой гараж."

    gif_tag = f"<a href='{data.AMG_GIFS.get('chest', data.AMG_GIFS['welcome'])}'>&#8205;</a>"
    p_after = await db.get_player(uid)
    ach = await award_achievements(uid)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [Btn(text=f"🔄 Открыть ещё ({c_info['price']} 🪙)", callback_data=f"case_open:{key}")],
        [Btn(text="🧰 К сундукам", callback_data="cases"), Btn(text="🏠 Меню", callback_data="menu")],
    ])

    await safe_edit(
        cb,
        f"{gif_tag}✨ <b>{c_info['name'].upper()} ОТКРЫТ!</b> ✨\n\n"
        f"{res_text}\n\n"
        f"🪙 Твой остаток: <b>{fmt(p_after['coins'])} 🪙 монет</b>{ach}",
        kb
    )


# ── Товары магазина за монеты ─────────────────────────────────

@router.callback_query(F.data.startswith("cbuy:"))
async def cb_coin_buy(cb: CallbackQuery):
    key = cb.data.split(":")[1]
    item = COIN_SHOP.get(key)
    uid = cb.from_user.id
    if not item:
        return await cb.answer("Товар не найден", show_alert=True)
    p = await db.get_player(uid)

    refills_today = 0
    if key == "energy_refill":
        if p["energy"] >= p["max_energy"]:
            return await cb.answer("Энергия и так полная ⚡", show_alert=True)
        refills_today = await db.count_energy_refills_today(uid)
        if refills_today >= 3:
            return await cb.answer(
                "⏳ Дневной лимит: максимум 3 пополнения за монеты в день!\n\n"
                "Энергия пополняется бесплатно (+1 каждые 30 мин) или в Звёздном магазине ⭐.",
                show_alert=True
            )
    if key == "energy_plus" and p["max_energy"] >= MAX_ENERGY_CAP:
        return await cb.answer("Достигнут максимум энергии!", show_alert=True)
    if key == "insurance" and p.get("has_insurance"):
        return await cb.answer("У тебя уже действует страховка! 🛡", show_alert=True)
    if not await db.spend_coins(uid, item["price"], reason=f"Покупка: {item['name']}"):
        deficit = item["price"] - p["coins"]
        await cb.answer()
        return await safe_edit(
            cb,
            f"🪙 <b>НЕ ХВАТАЕТ МОНЕТ!</b>\n\n"
            f"Товар: <b>{item['name']}</b>\n"
            f"Цена: <b>{item['price']} 🪙</b> · У тебя: <b>{p['coins']} 🪙</b>\n"
            f"Не хватает: <b>{deficit} 🪙</b>\n\n"
            "Пополни баланс за Telegram Stars ⭐️ в звёздном магазине!",
            not_enough_coins_kb("cshop")
        )

    await cb.answer()
    result = ""
    if key == "energy_refill":
        await db.update_player(uid, energy=p["max_energy"])
        left = max(0, 3 - (refills_today + 1))
        result = f"⚡ <b>Энергия восстановлена до {p['max_energy']}!</b>\n(Осталось пополнений за монеты сегодня: {left})"
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

    ach = await award_achievements(uid)
    await safe_edit(cb, f"{result}{ach}", back_kb("cshop", "🪙 В магазин"))

