"""Командные активности в группах: Рейд на босса AMG и заезды."""
import random
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

import db
import data
from data import CAR_CATALOG, fmt
from engine import calc_stats, car_upgrades
from kb import boss_kb

router = Router(name="group_games")

BOSS_NAMES = [
    ("Шеф полиции на броне-Гелике", "g63", 3000),
    ("Призрак автобана на AMG ONE", "amg_one", 5000),
    ("Король ночного Берлина на GT Black Series", "gt_bs", 4000),
    ("Стритрейсер-тяжеловес на GLE 63 S", "gle63s", 3500),
]


@router.message(Command("boss"))
async def cmd_boss(message: Message):
    if message.chat.type == "private":
        return await message.answer("👾 Рейд на босса доступен только в группах! Добавь бота в чат и пиши /boss")

    chat_id = message.chat.id
    boss = await db.get_active_boss(chat_id)
    if not boss:
        name, car_key, hp = random.choice(BOSS_NAMES)
        boss = await db.create_boss(chat_id, name, car_key, hp)
        car = CAR_CATALOG[car_key]
        gif_tag = f"<a href='{data.AMG_GIFS['boss']}'>&#8205;</a>"
        await message.answer(
            f"{gif_tag}🚨 <b>ТРЕВОГА В ЧАТЕ! ПОЯВИЛСЯ БОСС!</b>\n\n"
            f"👤 <b>{boss['boss_name']}</b>\n"
            f"🚗 Машина: {car['emoji']} {car['name']}\n"
            f"❤️ Прочность: <b>{boss['current_hp']}/{boss['max_hp']} HP</b>\n\n"
            "Объединяйтесь всем чатом! Нажимайте кнопку, чтобы таранить босса и обгонять его. "
            "Победители получат монеты и редкий лут!",
            reply_markup=boss_kb()
        )
    else:
        pct = int(boss['current_hp'] / boss['max_hp'] * 100)
        await message.answer(
            f"👾 <b>Текущий босс: {boss['boss_name']}</b>\n"
            f"❤️ Осталось: <b>{boss['current_hp']}/{boss['max_hp']} HP</b> ({pct}%)\n\n"
            "Вперёд в атаку! 👇",
            reply_markup=boss_kb()
        )


@router.callback_query(F.data == "boss:hit")
async def cb_boss_hit(cb: CallbackQuery):
    uid = cb.from_user.id
    chat_id = cb.message.chat.id
    boss = await db.get_active_boss(chat_id)
    if not boss:
        return await cb.answer("Босс уже повержен или скрылся!", show_alert=True)

    pc = await db.get_selected_car(uid)
    if not pc:
        return await cb.answer("Сначала выбери авто в /start!", show_alert=True)

    if not await db.use_energy(uid):
        return await cb.answer("⚡ Нет энергии! Восстанови или купи в магазине.", show_alert=True)

    p = await db.get_player(uid)
    car = CAR_CATALOG[pc["car_key"]]
    st = calc_stats(car, car_upgrades(pc))
    base_dmg = int(st["rating"] * random.uniform(0.7, 1.3))

    # Бонусы за чат-нитро и золотой винил
    if p.get("chat_nitro_until"):
        base_dmg = int(base_dmg * 1.15)
    if p.get("gold_wrap"):
        base_dmg = int(base_dmg * 1.1)

    cur_hp, dead = await db.damage_boss(chat_id, uid, base_dmg)
    await cb.answer(f"💥 Твой удар: -{base_dmg} HP!")

    if dead:
        damagers = await db.get_boss_damagers(chat_id)
        medals = ["🥇", "🥈", "🥉"]
        lines = []
        for i, d in enumerate(damagers[:5]):
            m = medals[i] if i < 3 else f"{i + 1}."
            lines.append(f"{m} {d['first_name']} — <b>{fmt(d['damage'])}</b> урона")

        # Выдаем награды всем участникам
        for i, d in enumerate(damagers):
            bonus_coins = 50 if i == 0 else (30 if i < 3 else 15)
            await db.add_coins_admin(d["user_id"], bonus_coins, reason="Победа над рейдовым боссом")
            await db.add_xp(d["user_id"], bonus_coins * 10)

        gif_tag = f"<a href='{data.AMG_GIFS['win']}'>&#8205;</a>"
        await db.delete_boss(chat_id)
        await cb.message.answer(
            f"{gif_tag}🎉 <b>БОСС «{boss['boss_name']}» ПОВЕРЖЕН!</b>\n\n"
            f"Чат одержал победу! Награды зачислены всем участникам.\n\n"
            f"🏆 <b>Топ урона:</b>\n" + "\n".join(lines)
        )
    else:
        # Обновляем инфо раз в несколько ударов
        if random.random() < 0.35:
            pct = int(cur_hp / boss['max_hp'] * 100)
            bar_len = int(cur_hp / boss['max_hp'] * 10)
            bar = "▰" * bar_len + "▱" * (10 - bar_len)
            try:
                await cb.message.edit_text(
                    f"👾 <b>Босс: {boss['boss_name']}</b>\n"
                    f"❤️ {bar} <b>{cur_hp}/{boss['max_hp']} HP</b> ({pct}%)\n\n"
                    f"🔥 Последний урон: <b>{cb.from_user.first_name}</b> (-{base_dmg})\n"
                    "Все на таран! 👇",
                    reply_markup=boss_kb()
                )
            except Exception:
                pass


@router.callback_query(F.data == "boss:stats")
async def cb_boss_stats(cb: CallbackQuery):
    chat_id = cb.message.chat.id
    damagers = await db.get_boss_damagers(chat_id)
    if not damagers:
        return await cb.answer("Ещё никто не нанёс урон!", show_alert=True)
    lines = [f"{i + 1}. {d['first_name']} — {fmt(d['damage'])} HP" for i, d in enumerate(damagers[:10])]
    await cb.answer("\n".join(lines), show_alert=True)


# ── Групповой Турнир / Гран-при чата (/tournament) ───────────

TOURNAMENTS: dict = {}  # chat_id -> {status, participants: [user_id], names: {uid: name}, cars: {uid: pc}}


@router.message(Command("tournament"))
async def cmd_tournament(message: Message):
    if message.chat.type == "private":
        return await message.answer("🏁 Турнир доступен только в группах! Добавь бота в чат и пиши /tournament")

    chat_id = message.chat.id
    if chat_id in TOURNAMENTS and TOURNAMENTS[chat_id]["status"] == "recruiting":
        return await message.answer("⚠️ Регистрация на турнир уже открыта! Жми кнопку ниже.")

    TOURNAMENTS[chat_id] = {
        "status": "recruiting",
        "participants": [],
        "names": {},
        "cars": {},
    }

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton as Btn
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [Btn(text="🏎 Участвовать в Гран-при!", callback_data="tourn:join")],
        [Btn(text="🟢 СТАРТ ГОНКИ (минимум 2)", callback_data="tourn:start")],
    ])

    gif_tag = f"<a href='{data.AMG_GIFS['race']}'>&#8205;</a>"
    await message.answer(
        f"{gif_tag}🏆 <b>ГРАН-ПРИ ЧАТА ОБЪЯВЛЕН!</b>\n\n"
        f"Организатор: <b>{message.from_user.first_name}</b>\n\n"
        "Нажмите кнопку <b>«Участвовать»</b>, чтобы занять место на стартовой решетке.\n"
        "Победитель забирает банк очков и признание всего чата!\n\n"
        "Участников: <b>0</b>",
        reply_markup=kb
    )


@router.callback_query(F.data == "tourn:join")
async def cb_tourn_join(cb: CallbackQuery):
    chat_id = cb.message.chat.id
    t = TOURNAMENTS.get(chat_id)
    if not t or t["status"] != "recruiting":
        return await cb.answer("Набор в турнир закрыт!", show_alert=True)

    uid = cb.from_user.id
    if uid in t["participants"]:
        return await cb.answer("Ты уже в списке участников! 🏎", show_alert=True)

    pc = await db.get_selected_car(uid)
    if not pc:
        return await cb.answer("Сначала выбери авто в /start!", show_alert=True)

    t["participants"].append(uid)
    t["names"][uid] = cb.from_user.first_name or f"Гонщик {len(t['participants'])}"
    t["cars"][uid] = pc

    count = len(t["participants"])
    await cb.answer(f"Ты в игре! Место на решетке #{count} 🚦")

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton as Btn
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [Btn(text="🏎 Участвовать в Гран-при!", callback_data="tourn:join")],
        [Btn(text=f"🟢 СТАРТ ГОНКИ ({count} участников)", callback_data="tourn:start")],
    ])

    names_list = "\n".join(f"• <b>{t['names'][u]}</b> ({CAR_CATALOG[t['cars'][u]['car_key']]['name']})" for u in t["participants"])
    try:
        gif_tag = f"<a href='{data.AMG_GIFS['race']}'>&#8205;</a>"
        await cb.message.edit_text(
            f"{gif_tag}🏆 <b>ГРАН-ПРИ ЧАТА ОБЪЯВЛЕН!</b>\n\n"
            f"<b>Стартовая решетка ({count}):</b>\n{names_list}\n\n"
            "Нажимайте старт, когда все готовы! 👇",
            reply_markup=kb
        )
    except Exception:
        pass


@router.callback_query(F.data == "tourn:start")
async def cb_tourn_start(cb: CallbackQuery):
    chat_id = cb.message.chat.id
    t = TOURNAMENTS.get(chat_id)
    if not t or t["status"] != "recruiting":
        return await cb.answer("Турнир не найден!", show_alert=True)

    if len(t["participants"]) < 2:
        return await cb.answer("Нужно минимум 2 гонщика для старта!", show_alert=True)

    t["status"] = "racing"
    await cb.answer("🏁 Турнир стартует!")

    import asyncio
    status_msg = await cb.message.edit_text("🚦 <b>3... 2... 1... СТАРТ ГРАН-ПРИ!</b>\nМашины сорвались со старта!")
    await asyncio.sleep(1.5)

    # Симулируем заезд каждого с учетом рейтинга и рандома
    scores = []
    for uid in t["participants"]:
        pc = t["cars"][uid]
        car = CAR_CATALOG[pc["car_key"]]
        st = calc_stats(car, car_upgrades(pc))
        score = st["rating"] * random.uniform(0.85, 1.25)
        scores.append((score, uid, t["names"][uid], car["name"]))

    scores.sort(key=lambda x: x[0], reverse=True)

    # Выдаем награды топ-3
    medals = ["🥇", "🥈", "🥉"]
    res_lines = []
    for i, (_, uid, name, car_name) in enumerate(scores):
        m = medals[i] if i < 3 else f"{i + 1}."
        reward_txt = ""
        if i == 0:
            await db.add_coins_admin(uid, 40, reason="1 место в Гран-при чата")
            await db.add_money(uid, 25000)
            await db.add_xp(uid, 300)
            reward_txt = " (+40 🪙, +$25k, +300 XP)"
        elif i == 1:
            await db.add_coins_admin(uid, 20, reason="2 место в Гран-при чата")
            await db.add_money(uid, 12000)
            await db.add_xp(uid, 150)
            reward_txt = " (+20 🪙, +$12k, +150 XP)"
        elif i == 2:
            await db.add_coins_admin(uid, 10, reason="3 место в Гран-при чата")
            await db.add_money(uid, 6000)
            await db.add_xp(uid, 80)
            reward_txt = " (+10 🪙, +$6k, +80 XP)"
        res_lines.append(f"{m} <b>{name}</b> ({car_name}){reward_txt}")

    winner_name = scores[0][2]
    gif_tag = f"<a href='{data.AMG_GIFS['win']}'>&#8205;</a>"
    await status_msg.edit_text(
        f"{gif_tag}🏁 <b>ФИНИШ ГРАН-ПРИ ЧАТА!</b>\n\n"
        f"🏆 Чемпион заезда: <b>{winner_name}</b>!\n\n"
        f"📋 <b>Итоговая таблица:</b>\n" + "\n".join(res_lines)
    )
    TOURNAMENTS.pop(chat_id, None)


# ── Кооперативная игра: Погоня от полиции (/chase) ───────────

CHASES: dict = {}  # chat_id -> dict


@router.message(Command("chase"))
async def cmd_chase(message: Message):
    if message.chat.type == "private":
        return await message.answer("🚓 Режим погони доступен только в группах! Добавь бота в чат и пиши /chase")

    chat_id = message.chat.id
    if chat_id in CHASES:
        return await message.answer("⚠️ Погоня уже идёт! Жмите кнопки действий.")

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton as Btn
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [Btn(text="💨 Врубить форсаж!", callback_data="chase:nitro"),
         Btn(text="🛡 Прикрыть хвост!", callback_data="chase:block")],
        [Btn(text="↩️ Резкий вираж!", callback_data="chase:drift")],
    ])

    CHASES[chat_id] = {
        "distance": 100,  # нужно набрать 250м чтобы уйти
        "heat": 0,        # при 100 поймали
        "crew": set(),
    }

    gif_tag = f"<a href='{data.AMG_GIFS['crash']}'>&#8205;</a>"
    await message.answer(
        f"{gif_tag}🚨 <b>ОБЛАВА! ПОЛИЦЕЙСКАЯ ПОГОНЯ!</b>\n\n"
        "Патрульные перекрыли район! Вся банда должна действовать сообща:\n"
        "• <b>Форсаж:</b> добавляет отрыв от патруля.\n"
        "• <b>Прикрытие:</b> сбивает уровень тревоги полиции.\n"
        "• <b>Вираж:</b> путает перехватчиков!\n\n"
        "Дистанция отрыва: <b>100 / 250 м</b>\n"
        "Уровень тревоги: <b>15%</b>\n\n"
        "Координируйте действия кнопками ниже! 👇",
        reply_markup=kb
    )


@router.callback_query(F.data.startswith("chase:"))
async def cb_chase_act(cb: CallbackQuery):
    chat_id = cb.message.chat.id
    ch = CHASES.get(chat_id)
    if not ch:
        return await cb.answer("Погоня уже закончилась!", show_alert=True)

    uid = cb.from_user.id
    act = cb.data.split(":")[1]
    ch["crew"].add(uid)

    if act == "nitro":
        gain = random.randint(25, 45)
        ch["distance"] += gain
        ch["heat"] += random.randint(10, 18)
        note = f"💨 {cb.from_user.first_name} дал по газам! +{gain}м отрыва!"
    elif act == "block":
        drop = random.randint(15, 25)
        ch["heat"] = max(0, ch["heat"] - drop)
        note = f"🛡 {cb.from_user.first_name} подрезал экипаж! Тревога снижена на -{drop}%!"
    else:  # drift
        ch["distance"] += random.randint(15, 30)
        ch["heat"] = max(0, ch["heat"] - 10)
        note = f"↩️ {cb.from_user.first_name} ушел в боковой переулок!"

    await cb.answer()

    if ch["distance"] >= 250:
        # Успешный побег
        gif_tag = f"<a href='{data.AMG_GIFS['win']}'>&#8205;</a>"
        crew_count = len(ch["crew"])
        for u in ch["crew"]:
            await db.add_coins_admin(u, 25, reason="Успешный уход от погони")
            await db.add_money(u, 15000)
            await db.add_xp(u, 150)
        await cb.message.edit_text(
            f"{gif_tag}🏆 <b>БАНДА УШЛА В ОТРЫВ!</b>\n\n"
            f"Полиция потеряла след в ночном городе! Все участники ({crew_count} чел.) "
            "получили по <b>+25 🪙</b> и <b>+$15,000</b>!"
        )
        CHASES.pop(chat_id, None)
    elif ch["heat"] >= 100:
        # Провал
        gif_tag = f"<a href='{data.AMG_GIFS['crash']}'>&#8205;</a>"
        await cb.message.edit_text(
            f"{gif_tag}🚓 <b>ПЕРЕХВАТ! БАНДА ЗАБЛОКИРОВАНА!</b>\n\n"
            "Полицейские выставили шипы и окружили колонну. Придется залечь на дно!"
        )
        CHASES.pop(chat_id, None)
    else:
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton as Btn
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [Btn(text="💨 Врубить форсаж!", callback_data="chase:nitro"),
             Btn(text="🛡 Прикрыть хвост!", callback_data="chase:block")],
            [Btn(text="↩️ Резкий вираж!", callback_data="chase:drift")],
        ])
        try:
            gif_tag = f"<a href='{data.AMG_GIFS['crash']}'>&#8205;</a>"
            await cb.message.edit_text(
                f"{gif_tag}🚨 <b>ПОЛИЦЕЙСКАЯ ПОГОНЯ В РАЗГАРЕ!</b>\n\n"
                f"{note}\n\n"
                f"Дистанция отрыва: <b>{ch['distance']} / 250 м</b>\n"
                f"Уровень тревоги: <b>{ch['heat']}%</b> (на 100% — перехват!)\n\n"
                "Жмите действия! 👇",
                reply_markup=kb
            )
        except Exception:
            pass

