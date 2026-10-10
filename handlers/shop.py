import random

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, InlineKeyboardButton as Btn, InlineKeyboardMarkup, Message

import data
import db
from config import ADMIN_IDS
from data import (CAR_CATALOG, CAR_CLASS_EMOJIS, CAR_CLASS_NAMES, CASE_DROPS, CASES, COIN_SHOP,
                  MAX_ENERGY_CAP, fmt, get_cars_by_class)
from engine import calc_stats
from kb import (back_kb, buy_confirm_kb, cases_kb, coin_exchange_kb, coin_shop_kb,
                shop_classes_kb, shop_list_kb, withdraw_kb)
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


# ── Магазин и Вывод монет ─────────────────────────────────────

@router.message(Command("cshop"))
async def cmd_cshop(message: Message):
    p = await db.get_player(message.from_user.id)
    items = "\n".join(f"{i['name']} — <b>{i['price']} 🪙</b>\n<i>{i['desc']}</i>" for k, i in COIN_SHOP.items() if not k.startswith("case_"))
    await message.answer(
        f"🪙 <b>Магазин и Вывод монет AMG</b>\n\nУ тебя: <b>{fmt(p['coins'])} 🪙</b>\n\n{items}\n\n"
        "<i>Монеты даются за командные заезды, дуэли, рейды на боссов и бонус дня!</i>",
        reply_markup=coin_shop_kb()
    )


@router.callback_query(F.data == "cshop")
async def cb_coin_shop(cb: CallbackQuery, player: dict):
    await cb.answer()
    items = "\n".join(f"{i['name']} — <b>{i['price']} 🪙</b>\n<i>{i['desc']}</i>" for k, i in COIN_SHOP.items() if not k.startswith("case_"))
    await safe_edit(cb, f"🪙 <b>Магазин и Вывод монет AMG</b>\n\nУ тебя: <b>{fmt(player['coins'])} 🪙</b>\n\n{items}\n\n"
                        "<i>Монеты даются за командные заезды, дуэли, рейды на боссов и бонус дня!</i>", coin_shop_kb())


# ── Сундуки и Кейсы (В личке с ботом) ─────────────────────────

def roll_case(case_key: str):
    drops = CASE_DROPS.get(case_key, CASE_DROPS["case_basic"])
    return random.choices(drops, weights=[d[0] for d in drops])[0]


async def render_cases_view(uid: int):
    p = await db.get_player(uid)
    gif_tag = f"<a href='{data.AMG_GIFS.get('chest', data.AMG_GIFS['welcome'])}'>&#8205;</a>"
    text = (
        f"{gif_tag}🧰 <b>СУНДУКИ И КЕЙСЫ AMG PERFORMANCE</b> 🧰\n\n"
        f"Твой баланс: <b>{fmt(p['coins'])} 🪙 монет</b>\n\n"
        "Испытай удачу и выбей редкий суперкар AMG, крупный денежный куш или горы опыта!\n\n"
        "📦 <b>Базовый сундук (100 🪙):</b>\n"
        "• Деньги: до $100,000 · Опыт: 300 XP\n"
        "• Машины: A35, CLA 45 S, C63 S\n\n"
        "🎁 <b>Элитный кейс AMG (350 🪙):</b>\n"
        "• Деньги: до $250,000 · Опыт: 1500 XP\n"
        "• Машины: E63 S, AMG GT, GT 63 S, GT R, GT Black Series, AMG ONE\n\n"
        "👑 <b>Легендарный ларец ONE (750 🪙):</b>\n"
        "• Мега-куш: до $750,000 · Опыт: 3000 XP\n"
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
        return await cb.answer(f"Не хватает монет! Нужно {c_info['price']} 🪙 (у тебя {p['coins']} 🪙)", show_alert=True)
    if await db.count_cars(uid) >= 30:
        return await cb.answer("Гараж переполнен! Продай машину перед открытием.", show_alert=True)

    if not await db.spend_coins(uid, c_info["price"], reason=f"Открытие: {c_info['name']}"):
        return await cb.answer("Недостаточно монет 🪙", show_alert=True)

    await cb.answer("🧰 Открываем сундук...")
    _, kind, value = roll_case(key)
    res_text = ""
    if kind == "money":
        await db.add_money(uid, value)
        res_text = f"💰 <b>ВЫИГРЫШ:</b> +${fmt(value)} наличных!"
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


# ── Вывод монет ───────────────────────────────────────────────

@router.callback_query(F.data == "c_withdraw")
async def cb_withdraw_info(cb: CallbackQuery):
    await cb.answer()
    uid = cb.from_user.id
    p = await db.get_player(uid)
    history = await db.get_user_withdrawals(uid, limit=3)
    hist_text = ""
    if history:
        lines = []
        for h in history:
            st = "⏳ На рассмотрении" if h["status"] == "pending" else ("✅ Выплачено" if h["status"] == "completed" else "❌ Отклонено")
            lines.append(f"• #{h['id']} — <b>{h['amount']} 🪙</b> ({st})")
        hist_text = "\n\n<b>История твоих выводов:</b>\n" + "\n".join(lines)

    await safe_edit(
        cb,
        f"💸 <b>ВЫВОД ЗОЛОТЫХ МОНЕТ AMG</b> 🪙\n\n"
        f"Твой баланс: <b>{fmt(p['coins'])} 🪙</b>\n"
        f"Курс конвертации: <b>1 🪙 = 1 ₽</b> (или эквивалент в TON / USDT)\n"
        f"Минимальный вывод: <b>50 🪙</b>\n\n"
        f"📌 <b>Как заказать вывод:</b>\n"
        f"Отправь в этот чат команду:\n"
        f"<code>/withdraw [количество] [номер карты / СБП / кошелёк]</code>\n\n"
        f"<i>Примеры:</i>\n"
        f"<code>/withdraw 150 +79991234567 СБП Т-Банк</code>\n"
        f"<code>/withdraw 500 UQCx... TON</code>\n"
        f"<code>/withdraw 300 2200123456789012 Сбербанк</code>\n\n"
        f"Все заявки обрабатываются администрацией в течение 24 часов.{hist_text}",
        withdraw_kb()
    )


@router.message(Command("withdraw"))
async def cmd_withdraw(message: Message, command: CommandObject):
    uid = message.from_user.id
    p = await db.get_player(uid)
    if not command.args:
        return await message.answer(
            "Формат команды:\n<code>/withdraw [количество] [реквизиты карты / СБП / TON]</code>\n\n"
            "<i>Пример:</i> <code>/withdraw 100 +79991234567 СБП Т-Банк</code>"
        )
    parts = command.args.split(maxsplit=1)
    if len(parts) < 2 or not parts[0].isdigit():
        return await message.answer("Укажи корректное количество монет и реквизиты!\nПример: <code>/withdraw 100 +79990001122 СБП</code>")

    amount = int(parts[0])
    wallet = parts[1].strip()

    if amount < 50:
        return await message.answer("Минимальная сумма для вывода — <b>50 🪙 монет</b>!")
    if p["coins"] < amount:
        return await message.answer(f"Недостаточно монет на балансе! У тебя <b>{p['coins']} 🪙</b>.")

    if not await db.spend_coins(uid, amount, reason=f"Вывод: {wallet[:30]}"):
        return await message.answer("Не удалось списать монеты. Попробуй позже.")

    w_id = await db.create_withdrawal(uid, amount, wallet)
    await message.answer(
        f"✅ <b>ЗАЯВКА НА ВЫВОД #{w_id} УСПЕШНО СОЗДАНА!</b>\n\n"
        f"Сумма: <b>{amount} 🪙</b>\n"
        f"Реквизиты: <code>{wallet}</code>\n"
        f"Статус: ⏳ <i>На рассмотрении администратором</i>\n\n"
        "Деньги будут отправлены после проверки."
    )

    # Уведомляем администраторов
    for adm_id in ADMIN_IDS:
        try:
            await message.bot.send_message(
                adm_id,
                f"🚨 <b>НОВАЯ ЗАЯВКА НА ВЫВОД #{w_id}!</b>\n\n"
                f"👤 Игрок: {message.from_user.first_name} (@{message.from_user.username or 'нет'})\n"
                f"ID: <code>{uid}</code>\n"
                f"Сумма: <b>{amount} 🪙</b>\n"
                f"Реквизиты: <code>{wallet}</code>\n\n"
                f"Чтобы подтвердить: <code>/pay_done {w_id}</code>\n"
                f"Чтобы отклонить: <code>/pay_reject {w_id}</code>"
            )
        except Exception:
            pass


# ── Обмен монет на кэш ────────────────────────────────────────

@router.callback_query(F.data == "c_exchange")
async def cb_exchange(cb: CallbackQuery, player: dict):
    await cb.answer()
    await safe_edit(
        cb,
        f"💱 <b>ОБМЕН МОНЕТ НА ИГРОВОЙ КЭШ $</b>\n\n"
        f"Твой баланс: <b>{fmt(player['coins'])} 🪙</b>\n\n"
        "Моментально обменяй золотые монеты на доллары для тюнинга и покупки суперкаров:\n\n"
        "• 50 🪙 ➔ <b>$150,000</b>\n"
        "• 120 🪙 ➔ <b>$400,000</b>\n"
        "• 400 🪙 ➔ <b>$1,500,000</b>\n\n"
        "Выбери пакет обмена:",
        coin_exchange_kb()
    )


@router.callback_query(F.data.startswith("c_ex:"))
async def cb_ex_execute(cb: CallbackQuery):
    cost = int(cb.data.split(":")[1])
    rates = {50: 150000, 120: 400000, 400: 1500000}
    if cost not in rates:
        return await cb.answer()
    uid = cb.from_user.id
    gain = rates[cost]
    if not await db.spend_coins(uid, cost, reason=f"Обмен на ${gain}"):
        return await cb.answer("Недостаточно монет 🪙", show_alert=True)
    await db.add_money(uid, gain)
    p_after = await db.get_player(uid)
    await cb.answer(f"✅ Обменено: +${fmt(gain)}!")
    await safe_edit(
        cb,
        f"🎉 <b>УСПЕШНЫЙ ОБМЕН!</b>\n\n"
        f"Списано: <b>-{cost} 🪙</b>\n"
        f"Зачислено: <b>+${fmt(gain)}</b>\n\n"
        f"💰 Твой баланс: <b>${fmt(p_after['money'])}</b>\n"
        f"🪙 Баланс монет: <b>{fmt(p_after['coins'])} 🪙</b>",
        back_kb("cshop", "◀️ В магазин монет")
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

    if key == "energy_refill" and p["energy"] >= p["max_energy"]:
        return await cb.answer("Энергия и так полная ⚡", show_alert=True)
    if key == "energy_plus" and p["max_energy"] >= MAX_ENERGY_CAP:
        return await cb.answer("Достигнут максимум энергии!", show_alert=True)
    if key == "insurance" and p.get("has_insurance"):
        return await cb.answer("У тебя уже действует страховка! 🛡", show_alert=True)
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

    ach = await award_achievements(uid)
    await safe_edit(cb, f"{result}{ach}", back_kb("cshop", "🪙 В магазин"))

