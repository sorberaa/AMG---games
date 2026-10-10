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
        boss_data = random.choice(data.BOSS_ROSTER)
        boss = await db.create_boss(chat_id, boss_data["name"], boss_data["car_key"], boss_data["hp"])
        car = CAR_CATALOG[boss_data["car_key"]]
        gif_tag = f"<a href='{data.AMG_GIFS['boss']}'>&#8205;</a>"
        await message.answer(
            f"{gif_tag}🚨 <b>ТРЕВОГА В ЧАТЕ! ПОЯВИЛСЯ РЕЙДОВЫЙ БОСС!</b>\n\n"
            f"👤 <b>{boss_data['name']}</b>\n"
            f"🚗 Машина: {car['emoji']} <b>{car['name']}</b>\n"
            f"❤️ Прочность: <b>{boss['current_hp']}/{boss['max_hp']} HP</b>\n"
            f"⚡ Способность: <i>{boss_data['ability']}</i>\n"
            f"💬 <i>{boss_data['phrase']}</i>\n\n"
            f"🎁 <b>Призовой фонд победы:</b> {boss_data['coins_pool']} 🪙 монет + ${fmt(boss_data['money_pool'])}\n"
            f"🏆 Дополнительный трофей: <b>{boss_data['loot']}</b>\n\n"
            "Объединяйтесь всем чатом! Выбирайте обычный таран или мощный Нитро-удар! 👇",
            reply_markup=boss_kb()
        )
    else:
        pct = int(boss['current_hp'] / boss['max_hp'] * 100)
        bar_len = max(0, min(10, int(boss['current_hp'] / boss['max_hp'] * 10)))
        bar = "▰" * bar_len + "▱" * (10 - bar_len)
        gif_tag = f"<a href='{data.AMG_GIFS['boss_rage']}'>&#8205;</a>" if pct <= 40 else f"<a href='{data.AMG_GIFS['boss']}'>&#8205;</a>"
        rage_note = "\n⚠️ <b>ВНИМАНИЕ: БОСС ВПАЛ В ЯРОСТЬ!</b> Контратаки усилены!" if pct <= 40 else ""
        await message.answer(
            f"{gif_tag}👾 <b>Босс: {boss['boss_name']}</b>\n"
            f"❤️ {bar} <b>{boss['current_hp']}/{boss['max_hp']} HP</b> ({pct}%){rage_note}\n\n"
            "Все на таран! Давите газ в пол! 👇",
            reply_markup=boss_kb()
        )


async def execute_boss_strike(cb: CallbackQuery, is_nitro: bool = False):
    """Общая логика нанесения урона боссу (обычный таран или нитро-удар)."""
    uid = cb.from_user.id
    chat_id = cb.message.chat.id
    boss = await db.get_active_boss(chat_id)
    if not boss:
        return await cb.answer("Босс уже повержен или скрылся!", show_alert=True)

    pc = await db.get_selected_car(uid)
    if not pc:
        return await cb.answer("Сначала выбери авто в /start!", show_alert=True)

    energy_cost = 2 if is_nitro else 1
    p = await db.get_player(uid)
    if p["energy"] < energy_cost:
        return await cb.answer(f"⚡ Нужно {energy_cost} энергии! Подожди или восстанови в магазине.", show_alert=True)

    # Списываем энергию
    for _ in range(energy_cost):
        await db.use_energy(uid)

    car = CAR_CATALOG[pc["car_key"]]
    st = calc_stats(car, car_upgrades(pc))

    # Базовый урон от характеристик авто
    dmg_mult = random.uniform(0.8, 1.2)
    base_dmg = int(st["rating"] * dmg_mult)

    # Нитро-удар: x2.5 урон + шанс крита 35%
    is_crit = False
    if is_nitro:
        base_dmg = int(base_dmg * 2.5)
        if random.random() < 0.35:
            is_crit = True
            base_dmg = int(base_dmg * 1.5)

    # Бонусы за расходники чата
    if p.get("chat_nitro_until"):
        base_dmg = int(base_dmg * 1.2)
    if p.get("gold_wrap"):
        base_dmg = int(base_dmg * 1.15)

    cur_hp, dead = await db.damage_boss(chat_id, uid, base_dmg)

    crit_alert = " 💥 КРИТИЧЕСКИЙ ВЫБРОС ТУРБО!" if is_crit else ""
    strike_type = "🔥 НИТРО-УДАР" if is_nitro else "💥 ТАРАН"
    await cb.answer(f"{strike_type}: -{fmt(base_dmg)} HP!{crit_alert}")

    if dead:
        damagers = await db.get_boss_damagers(chat_id)
        medals = ["🥇", "🥈", "🥉"]
        lines = []
        for i, d in enumerate(damagers[:8]):
            m = medals[i] if i < 3 else f"{i + 1}."
            lines.append(f"{m} <b>{d['first_name']}</b> — <b>{fmt(d['damage'])}</b> HP")

        # Щедрые награды по местам
        for i, d in enumerate(damagers):
            target_uid = d["user_id"]
            if i == 0:
                coins = 120
                money = 100000
                xp = 1500
                await db.add_money(target_uid, money)
            elif i < 3:
                coins = 70
                money = 50000
                xp = 800
                await db.add_money(target_uid, money)
            elif i < 10:
                coins = 35
                money = 25000
                xp = 400
                await db.add_money(target_uid, money)
            else:
                coins = 20
                xp = 200

            await db.add_coins_admin(target_uid, coins, reason=f"Победа над боссом {boss['boss_name']}")
            await db.add_xp(target_uid, xp)

        gif_tag = f"<a href='{data.AMG_GIFS['win']}'>&#8205;</a>"
        await db.delete_boss(chat_id)
        await cb.message.answer(
            f"{gif_tag}🏆 <b>БОСС «{boss['boss_name']}» ПОЛНОСТЬЮ УНИЧТОЖЕН!</b>\n\n"
            f"🎉 Чат одержал сокрушительную победу! Все участники битвы получили щедрые награды (монеты 🪙, наличные $ и опыт XP).\n\n"
            f"👑 <b>ГЕРОИ БИТВЫ (ТОП ПО УРОНУ):</b>\n" + "\n".join(lines)
        )
    else:
        # Регулярно обновляем сообщение босса в чате
        pct = int(cur_hp / boss['max_hp'] * 100)
        bar_len = max(0, min(10, int(cur_hp / boss['max_hp'] * 10)))
        bar = "▰" * bar_len + "▱" * (10 - bar_len)
        gif_tag = f"<a href='{data.AMG_GIFS['boss_rage']}'>&#8205;</a>" if pct <= 40 else f"<a href='{data.AMG_GIFS['boss']}'>&#8205;</a>"
        rage_warning = "\n⚠️ <b>ФАЗА ЯРОСТИ:</b> Босс огрызается и выпускает клубы дыма!" if pct <= 40 else ""

        # Обновляем сообщение раз в несколько атак или при критическом ударе
        if random.random() < 0.4 or is_crit:
            try:
                await cb.message.edit_text(
                    f"{gif_tag}👾 <b>Босс: {boss['boss_name']}</b>\n"
                    f"❤️ {bar} <b>{fmt(cur_hp)}/{fmt(boss['max_hp'])} HP</b> ({pct}%){rage_warning}\n\n"
                    f"⚡ Последняя атака: <b>{cb.from_user.first_name}</b> ({strike_type} -{fmt(base_dmg)} HP!{crit_alert})\n\n"
                    "Продолжайте натиск! 👇",
                    reply_markup=boss_kb()
                )
            except Exception:
                pass


@router.callback_query(F.data == "boss:hit")
async def cb_boss_hit(cb: CallbackQuery):
    await execute_boss_strike(cb, is_nitro=False)


@router.callback_query(F.data == "boss:nitro")
async def cb_boss_nitro(cb: CallbackQuery):
    await execute_boss_strike(cb, is_nitro=True)


@router.callback_query(F.data == "boss:refresh")
async def cb_boss_refresh(cb: CallbackQuery):
    chat_id = cb.message.chat.id
    boss = await db.get_active_boss(chat_id)
    if not boss:
        return await cb.answer("Босс уже повержен!", show_alert=True)
    pct = int(boss['current_hp'] / boss['max_hp'] * 100)
    bar_len = max(0, min(10, int(boss['current_hp'] / boss['max_hp'] * 10)))
    bar = "▰" * bar_len + "▱" * (10 - bar_len)
    gif_tag = f"<a href='{data.AMG_GIFS['boss_rage']}'>&#8205;</a>" if pct <= 40 else f"<a href='{data.AMG_GIFS['boss']}'>&#8205;</a>"
    try:
        await cb.message.edit_text(
            f"{gif_tag}👾 <b>Босс: {boss['boss_name']}</b>\n"
            f"❤️ {bar} <b>{fmt(boss['current_hp'])}/{fmt(boss['max_hp'])} HP</b> ({pct}%)\n\n"
            "Все на таран! Давите газ в пол! 👇",
            reply_markup=boss_kb()
        )
        await cb.answer("Статус HP обновлен")
    except Exception:
        await cb.answer()


@router.callback_query(F.data == "boss:stats")
async def cb_boss_stats(cb: CallbackQuery):
    chat_id = cb.message.chat.id
    damagers = await db.get_boss_damagers(chat_id)
    if not damagers:
        return await cb.answer("Ещё никто не нанёс урон!", show_alert=True)
    medals = ["🥇", "🥈", "🥉"]
    lines = [f"{medals[i] if i < 3 else str(i+1)+'.'} {d['first_name']} — {fmt(d['damage'])} HP" for i, d in enumerate(damagers[:10])]
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

    # Назначаем уникальные цвета участникам (приоритет - цвет покраски машины)
    used_colors = set()
    participant_colors = {}
    for uid in t["participants"]:
        pc = t["cars"][uid]
        pref = pc.get("color")
        c_emoji = data.CAR_COLORS[pref]["emoji"] if (pref and pref in data.CAR_COLORS) else None
        if not c_emoji or c_emoji in used_colors:
            avail = [c for c in data.COLOR_PALETTE if c not in used_colors]
            c_emoji = random.choice(avail) if avail else random.choice(data.COLOR_PALETTE)
        used_colors.add(c_emoji)
        participant_colors[uid] = c_emoji

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
        col = participant_colors.get(uid, "🏎")
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
        res_lines.append(f"{m} {col} <b>{name}</b> ({car_name}){reward_txt}")

    winner_uid = scores[0][1]
    winner_name = scores[0][2]
    win_col = participant_colors.get(winner_uid, "🏎")
    gif_tag = f"<a href='{data.AMG_GIFS['win']}'>&#8205;</a>"
    await status_msg.edit_text(
        f"{gif_tag}🏁 <b>ФИНИШ ГРАН-ПРИ ЧАТА!</b>\n\n"
        f"🏆 Чемпион заезда: {win_col} <b>{winner_name}</b>!\n\n"
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


# ── 1. Авто-Викторина AMG в чате (/quiz) ─────────────────────

QUIZ_QUESTIONS = [
    {
        "q": "Какой первый гоночный седан AMG получил легендарное прозвище «Красный кабан» (Rote Sau)?",
        "opts": ["Mercedes 300 SEL 6.8 AMG", "Mercedes 190E 2.5-16 Evo II", "Mercedes SLS AMG GT3", "Mercedes 500E W124"],
        "correct": 0,
        "fact": "В 1971 году тяжелый седан 300 SEL 6.8 AMG сенсационно занял 2-е место в 24 часах Спа!"
    },
    {
        "q": "Какой силовой агрегат установлен в гиперкаре Mercedes-AMG ONE?",
        "opts": ["1.6L V6 Turbo из Formula 1 + 4 электромотора", "4.0L V8 Biturbo", "6.0L V12 Biturbo", "2.0L M139 гибрид"],
        "correct": 0,
        "fact": "Мотор напрямую взят из чемпионского болида F1 W07 и крутится до 11 000 об/мин!"
    },
    {
        "q": "Сколько лошадиных сил развивает трековый Mercedes-AMG GT Black Series?",
        "opts": ["730 л.с.", "585 л.с.", "639 л.с.", "843 л.с."],
        "correct": 0,
        "fact": "GT Black Series развивает 730 л.с. с плоским коленвалом и установил рекорд Нюрбургринга!"
    },
    {
        "q": "Что означает девиз ручной сборки двигателей AMG?",
        "opts": ["«One Man, One Engine»", "«Power and Precision»", "«Handcrafted for Speed»", "«Made in Affalterbach»"],
        "correct": 0,
        "fact": "Каждый V8 собирается вручную одним мастером, который крепит на мотор свою именную плакетку!"
    },
    {
        "q": "В каком немецком городе находится историческая штаб-квартира Mercedes-AMG?",
        "opts": ["Аффальтербах (Affalterbach)", "Штутгарт", "Мюнхен", "Ингольштадт"],
        "correct": 0,
        "fact": "Аффальтербах — дом и завод AMG с 1976 года!"
    },
    {
        "q": "Какой AMG является самым мощным серийным гибридом E Performance?",
        "opts": ["AMG GT 63 S E Performance (843 л.с.)", "AMG C63 S E Performance", "AMG SL 63", "AMG G63 4x4²"],
        "correct": 0,
        "fact": "GT 63 S E Performance развивает невероятные 843 л.с. и более 1400 Нм крутящего момента!"
    },
    {
        "q": "Какой мотор AMG признан самым мощным 2.0-литровым 4-цилиндровым серийным двигателем в мире?",
        "opts": ["M139 (до 421 л.с.)", "M177", "M133", "M256"],
        "correct": 0,
        "fact": "Турбомотор M139 выдает 421 л.с. в стоке на моделях A45 S и CLA 45 S!"
    },
    {
        "q": "Как расшифровывается аббревиатура AMG?",
        "opts": ["Aufrecht, Melcher, Großaspach", "Auto Motorsport Germany", "Advanced Mercedes Gears", "Automotive Master Group"],
        "correct": 0,
        "fact": "Ауфрехт (A), Мельхер (M) и Гроссаспах (G) — город рождения основателя Ганса Ауфрехта!"
    }
]

ACTIVE_QUIZZES: dict = {}  # chat_id -> {"correct": int, "q": dict, "active": bool}


@router.message(Command("quiz"))
async def cmd_quiz(message: Message):
    if message.chat.type == "private":
        return await message.answer("❓ Викторина доступна только в группах! Добавь бота в чат и пиши /quiz")

    chat_id = message.chat.id
    q_data = random.choice(QUIZ_QUESTIONS)
    # Перемешиваем варианты
    opts_with_idx = list(enumerate(q_data["opts"]))
    random.shuffle(opts_with_idx)

    correct_new_idx = 0
    shuffled_opts = []
    for new_idx, (orig_idx, opt_text) in enumerate(opts_with_idx):
        shuffled_opts.append(opt_text)
        if orig_idx == q_data["correct"]:
            correct_new_idx = new_idx

    ACTIVE_QUIZZES[chat_id] = {
        "correct": correct_new_idx,
        "q": q_data,
        "active": True
    }

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton as Btn
    rows = []
    for i, opt in enumerate(shuffled_opts):
        rows.append([Btn(text=f"{chr(65+i)}. {opt}", callback_data=f"quiz:{i}")])

    await message.answer(
        "🧠 <b>АВТО-ВИКТОРИНА AMG ДЛЯ ЧАТА!</b>\n\n"
        f"<b>Вопрос:</b>\n{q_data['q']}\n\n"
        "<i>Кто первым нажмет правильный ответ — забирает +25 🪙 монет и +150 XP!</i>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
    )


@router.callback_query(F.data.startswith("quiz:"))
async def cb_quiz_answer(cb: CallbackQuery):
    chat_id = cb.message.chat.id
    qz = ACTIVE_QUIZZES.get(chat_id)
    if not qz or not qz.get("active"):
        return await cb.answer("Эта викторина уже завершена! Запустите новую через /quiz", show_alert=True)

    ans_idx = int(cb.data.split(":")[1])
    uid = cb.from_user.id
    uname = cb.from_user.first_name

    if ans_idx == qz["correct"]:
        qz["active"] = False
        await db.add_coins_admin(uid, 25, reason="Победа в чат-викторине")
        await db.add_xp(uid, 150)
        await cb.answer("🎉 ПРАВИЛЬНО! Ты выиграл!", show_alert=True)
        fact_text = qz["q"]["fact"]
        await cb.message.edit_text(
            f"🏆 <b>ПОБЕДИТЕЛЬ ВИКТОРИНЫ: {uname}!</b>\n\n"
            f"✅ <b>Верный ответ:</b> {qz['q']['opts'][qz['q']['correct']]}\n\n"
            f"💡 <i>{fact_text}</i>\n\n"
            f"💰 Награда <b>+25 🪙 монет</b> и <b>+150 XP</b> начислена {uname}!\n"
            "Запустить ещё: <code>/quiz</code>"
        )
        ACTIVE_QUIZZES.pop(chat_id, None)
    else:
        await cb.answer("❌ Неверно! Попробуй другой вариант или дай шанс другим!", show_alert=True)


# ── 2. Аирдроп контейнера с лутом (/airdrop, /drop) ──────────

AIRDROPS: dict = {}  # chat_id -> {"participants": set, "names": dict, "status": str}


@router.message(Command("airdrop", "drop"))
async def cmd_airdrop(message: Message):
    if message.chat.type == "private":
        return await message.answer("📦 Аирдроп доступен только в группах! Добавь бота в чат и пиши /airdrop")

    chat_id = message.chat.id
    if chat_id in AIRDROPS and AIRDROPS[chat_id]["status"] == "waiting":
        return await message.answer("⚠️ В чате уже сброшен контейнер! Жмите кнопку ниже, чтобы взломать.")

    AIRDROPS[chat_id] = {
        "participants": set(),
        "names": {},
        "status": "waiting"
    }

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton as Btn
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [Btn(text="🧰 Взломать контейнер!", callback_data="drop:loot")],
        [Btn(text="💥 Открыть контейнер (мин. 2)!", callback_data="drop:open")],
    ])

    gif_tag = f"<a href='{data.AMG_GIFS['boss']}'>&#8205;</a>"
    await message.answer(
        f"{gif_tag}📦 <b>В ЧАТ СБРОШЕН КОНТЕЙНЕР AMG PERFORMANCE!</b>\n\n"
        f"Инициатор сброса: <b>{message.from_user.first_name}</b>\n\n"
        "Контрабандный груз приземлился в центре города! Все желающие забрать долю — нажимайте <b>«Взломать контейнер»</b>.\n"
        "Добыча распределится между всеми, кто успел отметиться!\n\n"
        "👥 Участников взлома: <b>0</b>",
        reply_markup=kb
    )


@router.callback_query(F.data == "drop:loot")
async def cb_drop_loot(cb: CallbackQuery):
    chat_id = cb.message.chat.id
    dr = AIRDROPS.get(chat_id)
    if not dr or dr["status"] != "waiting":
        return await cb.answer("Контейнер уже вскрыт или исчез!", show_alert=True)

    uid = cb.from_user.id
    if uid in dr["participants"]:
        return await cb.answer("Ты уже в списке вскрывающих! Жди открытия 🧰", show_alert=True)

    dr["participants"].add(uid)
    dr["names"][uid] = cb.from_user.first_name
    count = len(dr["participants"])
    await cb.answer(f"Ты подключился к взлому! (#{count}) 🔓")

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton as Btn
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [Btn(text="🧰 Взломать контейнер!", callback_data="drop:loot")],
        [Btn(text=f"💥 Открыть контейнер ({count} чел.)!", callback_data="drop:open")],
    ])

    names_str = "\n".join(f"• <b>{dr['names'][u]}</b>" for u in dr["participants"])
    try:
        gif_tag = f"<a href='{data.AMG_GIFS['boss']}'>&#8205;</a>"
        await cb.message.edit_text(
            f"{gif_tag}📦 <b>В ЧАТ СБРОШЕН КОНТЕЙНЕР AMG PERFORMANCE!</b>\n\n"
            f"<b>Команда взломщиков ({count}):</b>\n{names_str}\n\n"
            "Нажимайте открыть, когда все собрались! 👇",
            reply_markup=kb
        )
    except Exception:
        pass


@router.callback_query(F.data == "drop:open")
async def cb_drop_open(cb: CallbackQuery):
    chat_id = cb.message.chat.id
    dr = AIRDROPS.get(chat_id)
    if not dr or dr["status"] != "waiting":
        return await cb.answer("Контейнер уже открыт!", show_alert=True)

    if len(dr["participants"]) < 2:
        return await cb.answer("Нужно минимум 2 участника для вскрытия тяжелого замка!", show_alert=True)

    dr["status"] = "opened"
    await cb.answer("💥 Контейнер распахнут!")

    plist = list(dr["participants"])
    random.shuffle(plist)

    medals = ["🥇", "🥈", "🥉"]
    res_lines = []
    for i, uid in enumerate(plist):
        name = dr["names"][uid]
        m = medals[i] if i < 3 else "📦"
        if i == 0:
            coins, money, xp = 40, 30000, 300
        elif i == 1:
            coins, money, xp = 25, 20000, 200
        elif i == 2:
            coins, money, xp = 15, 12000, 150
        else:
            coins, money, xp = 8, 8000, 80

        await db.add_coins_admin(uid, coins, reason="Аирдроп контейнера в чате")
        await db.add_money(uid, money)
        await db.add_xp(uid, xp)
        res_lines.append(f"{m} <b>{name}</b> — <b>+{coins} 🪙</b>, +${fmt(money)}, +{xp} XP")

    gif_tag = f"<a href='{data.AMG_GIFS['win']}'>&#8205;</a>"
    await cb.message.edit_text(
        f"{gif_tag}🎉 <b>КОНТЕЙНЕР AMG PERFORMANCE ВСКРЫТ!</b>\n\n"
        "Лут поделён между участниками рейда:\n\n"
        + "\n".join(res_lines) +
        "\n\n<i>Запустить новый дроп: /airdrop</i>"
    )
    AIRDROPS.pop(chat_id, None)


# ── 3. Королевская битва на выбывание (/royale) ──────────────

ROYALES: dict = {}  # chat_id -> {"participants": list, "names": dict, "cars": dict, "status": str}

CRASH_REASONS = [
    "на скорости 310 км/ч пробил радиатор и залил мотор антифризом",
    "не удержал занос на мокром асфальте и развернулся поперек трассы",
    "поймал гидроудар турбины на перегазовке",
    "нарвался на полицейский кордон с шипами",
    "перегрел тормоза перед крутой шпилькой и вылетел в гравий",
    "ошибся с передачей и разорвал сцепление в клочья",
]


@router.message(Command("royale", "elimination"))
async def cmd_royale(message: Message):
    if message.chat.type == "private":
        return await message.answer("👑 Битва на выбывание доступна только в группах! Пиши /royale в чате.")

    chat_id = message.chat.id
    if chat_id in ROYALES and ROYALES[chat_id]["status"] == "recruiting":
        return await message.answer("⚠️ Битва на выбывание уже собирается! Жмите кнопку ниже.")

    ROYALES[chat_id] = {
        "participants": [],
        "names": {},
        "cars": {},
        "status": "recruiting"
    }

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton as Btn
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [Btn(text="🏎 Занять место на старте!", callback_data="royale:join")],
        [Btn(text="🟢 СТАРТ ВЫБЫВАНИЯ (мин. 3)", callback_data="royale:start")],
    ])

    gif_tag = f"<a href='{data.AMG_GIFS['race']}'>&#8205;</a>"
    await message.answer(
        f"{gif_tag}👑 <b>КОРОЛЕВСКАЯ БИТВА НА ВЫБЫВАНИЕ (ROYALE)!</b>\n\n"
        f"Организатор: <b>{message.from_user.first_name}</b>\n\n"
        "Правила просты: каждый круг самый неудачливый гонщик вылетает из гонки!\n"
        "Выживает только один — <b>Король Автобана</b> забирает джекпот: <b>+50 🪙 монет</b> и <b>+$50,000</b>!\n\n"
        "Участников: <b>0</b>",
        reply_markup=kb
    )


@router.callback_query(F.data == "royale:join")
async def cb_royale_join(cb: CallbackQuery):
    chat_id = cb.message.chat.id
    ry = ROYALES.get(chat_id)
    if not ry or ry["status"] != "recruiting":
        return await cb.answer("Набор закрыт!", show_alert=True)

    uid = cb.from_user.id
    if uid in ry["participants"]:
        return await cb.answer("Ты уже на стартовой решетке!", show_alert=True)

    pc = await db.get_selected_car(uid)
    if not pc:
        return await cb.answer("Сначала выбери авто в /start!", show_alert=True)

    ry["participants"].append(uid)
    ry["names"][uid] = cb.from_user.first_name
    ry["cars"][uid] = pc
    count = len(ry["participants"])
    await cb.answer(f"Ты в списке гладиаторов! (#{count}) 🔥")

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton as Btn
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [Btn(text="🏎 Занять место на старте!", callback_data="royale:join")],
        [Btn(text=f"🟢 СТАРТ ВЫБЫВАНИЯ ({count} чел.)", callback_data="royale:start")],
    ])

    names_str = "\n".join(f"• <b>{ry['names'][u]}</b> ({CAR_CATALOG[ry['cars'][u]['car_key']]['name']})" for u in ry["participants"])
    try:
        gif_tag = f"<a href='{data.AMG_GIFS['race']}'>&#8205;</a>"
        await cb.message.edit_text(
            f"{gif_tag}👑 <b>КОРОЛЕВСКАЯ БИТВА НА ВЫБЫВАНИЕ (ROYALE)!</b>\n\n"
            f"<b>Стартовая решетка ({count}):</b>\n{names_str}\n\n"
            "Жмите старт, когда все бойцы собраны! 👇",
            reply_markup=kb
        )
    except Exception:
        pass


@router.callback_query(F.data == "royale:start")
async def cb_royale_start(cb: CallbackQuery):
    chat_id = cb.message.chat.id
    ry = ROYALES.get(chat_id)
    if not ry or ry["status"] != "recruiting":
        return await cb.answer("Битва не найдена!", show_alert=True)

    if len(ry["participants"]) < 2:
        return await cb.answer("Нужно минимум 2 участника для гонки на выбывание!", show_alert=True)

    ry["status"] = "racing"
    await cb.answer("🏁 Битва началась!")

    import asyncio
    alive = list(ry["participants"])
    random.shuffle(alive)

    rounds_log = []
    round_num = 1

    await cb.message.edit_text("🚦 <b>ЗЕЛЁНЫЙ СВЕТ! МОТОРЫ РЕВУТ НА ПРЕДЕЛЕ!</b>\nНачалась гонка на выживание...")
    await asyncio.sleep(2)

    while len(alive) > 1:
        # Выбираем выбывшего с учетом шанса от рейтинга авто
        eliminated = alive.pop(random.randint(0, len(alive) - 1))
        elim_name = ry["names"][eliminated]
        reason = random.choice(CRASH_REASONS)
        rounds_log.append(f"💥 <b>Круг {round_num}:</b> <i>{elim_name}</i> {reason}! (Выбыл ❌)")
        round_num += 1

    winner_id = alive[0]
    winner_name = ry["names"][winner_id]
    winner_car = CAR_CATALOG[ry["cars"][winner_id]["car_key"]]["name"]

    # Награда победителю
    await db.add_coins_admin(winner_id, 50, reason="1 место в Royal Выбывании")
    await db.add_money(winner_id, 50000)
    await db.add_xp(winner_id, 500)

    gif_tag = f"<a href='{data.AMG_GIFS['win']}'>&#8205;</a>"
    log_text = "\n".join(rounds_log)
    await cb.message.edit_text(
        f"{gif_tag}👑 <b>ФИНИШ БИТВЫ НА ВЫБЫВАНИЕ!</b>\n\n"
        f"<b>Хроника заезда:</b>\n{log_text}\n\n"
        f"🏆 <b>ЕДИНСТВЕННЫЙ ВЫЖИВШИЙ ЧЕМПИОН:</b>\n"
        f"🥇 <b>{winner_name}</b> на <b>{winner_car}</b>!\n\n"
        f"💰 Награда победителя: <b>+50 🪙 монет</b>, <b>+$50,000</b> и <b>+500 XP</b>!\n"
        "Сыграть ещё: <code>/royale</code>"
    )
    ROYALES.pop(chat_id, None)


# ── Колесо Фортуны AMG (/wheel, /spin) ──────────────────────────

@router.message(Command("wheel"))
@router.message(Command("spin"))
async def cmd_wheel(message: Message):
    if message.chat.type == "private":
        bot_info = await message.bot.get_me()
        from aiogram.types import InlineKeyboardButton as Btn, InlineKeyboardMarkup
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [Btn(text="➕ Добавить бота в группу", url=f"https://t.me/{bot_info.username}?startgroup=true")],
            [Btn(text="🏠 Меню", callback_data="menu")],
        ])
        return await message.answer(
            "🎰 <b>Колесо Фортуны крутят на командных сходках в группе!</b>\n\n"
            "Добавь бота в командный чат и пиши <code>/wheel</code> там!",
            reply_markup=kb
        )

    gif_tag = f"<a href='{data.AMG_GIFS['wheel']}'>&#8205;</a>"
    from kb import wheel_kb
    await message.answer(
        f"{gif_tag}🎰 <b>КОЛЕСО ФОРТУНЫ MERCEDES-AMG</b> 🎰\n\n"
        "Испытай удачу на закрытой сходке стритрейсеров!\n"
        "Каждый гонщик может крутить рулетку <b>1 раз в сутки бесплатно</b>.\n\n"
        "🎁 <b>Возможные призы:</b>\n"
        "• До <b>100 🪙 золотых монет</b>\n"
        "• До <b>$50,000</b> наличных\n"
        "• Дополнительная ⚡ энергия и 📈 опыт\n"
        "• <i>(Осторожно: есть шанс нарваться на штраф от ДПС!)</i>\n\n"
        "Жми кнопку ниже, чтобы запустить вращение! 👇",
        reply_markup=wheel_kb()
    )


@router.callback_query(F.data == "wheel:spin")
async def cb_wheel_spin(cb: CallbackQuery):
    uid = cb.from_user.id
    today = db.now_str()[:10]
    p = await db.get_player(uid)
    if not p:
        return await cb.answer("Сначала напиши /start!", show_alert=True)

    if p.get("last_wheel_spin") == today:
        return await cb.answer("⏳ Ты уже крутил колесо сегодня! Возвращайся завтра.", show_alert=True)

    # Крутим колесо
    weights = [item["weight"] for item in data.WHEEL_PRIZES]
    prize = random.choices(data.WHEEL_PRIZES, weights=weights, k=1)[0]

    # Фиксируем дату крутки
    await db.update_player(uid, last_wheel_spin=today)

    # Выдаем награду
    ptype = prize["type"]
    pval = prize["val"]
    if ptype == "money":
        await db.add_money(uid, pval)
    elif ptype == "coins":
        await db.add_coins_admin(uid, pval, reason="Колесо Фортуны AMG")
    elif ptype == "energy":
        cur_e = p["energy"]
        max_e = p["max_energy"]
        new_e = min(max_e, cur_e + pval)
        await db.update_player(uid, energy=new_e)
    elif ptype == "xp":
        await db.add_xp(uid, pval)
    elif ptype == "fine":
        await db.add_money(uid, -pval)

    gif_tag = f"<a href='{data.AMG_GIFS['wheel']}'>&#8205;</a>"
    await cb.message.edit_text(
        f"{gif_tag}🎰 <b>РУЛЕТКА ОСТАНОВИЛАСЬ!</b>\n\n"
        f"Гонщик: <b>{cb.from_user.first_name}</b>\n\n"
        f"🎉 <b>ТВОЙ ВЫИГРЫШ:</b>\n"
        f"👉 <b>{prize['text']}</b>\n\n"
        f"Приз уже зачислен на твой аккаунт! Следующая бесплатная попытка доступна завтра.",
        reply_markup=None
    )
    await cb.answer("🎉 Поздравляем с выигрышем!")


# ── Ночные Похождения по Автобану (/adventure, /trip) ──────────

ADVENTURE_STATES = {}  # user_id -> scenario_idx


@router.message(Command("adventure"))
@router.message(Command("trip"))
async def cmd_adventure(message: Message):
    if message.chat.type == "private":
        bot_info = await message.bot.get_me()
        from aiogram.types import InlineKeyboardButton as Btn, InlineKeyboardMarkup
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [Btn(text="➕ Добавить бота в группу", url=f"https://t.me/{bot_info.username}?startgroup=true")],
            [Btn(text="🏠 Меню", callback_data="menu")],
        ])
        return await message.answer(
            "🌃 <b>Ночные похождения банды проводятся в чатах команд!</b>\n\n"
            "Добавь бота в свою группу и отправляйтесь в рейд: <code>/adventure</code>",
            reply_markup=kb
        )

    uid = message.from_user.id
    pc = await db.get_selected_car(uid)
    if not pc:
        return await message.answer("Сначала выбери авто в /start!")

    p = await db.get_player(uid)
    if p["energy"] < 2:
        return await message.answer("⚡ Для ночного похождения нужно 2 единицы энергии! Восстанови или подожди.")

    # Выбираем случайный сценарий
    sc_idx = random.randint(0, len(data.ADVENTURE_SCENARIOS) - 1)
    scenario = data.ADVENTURE_SCENARIOS[sc_idx]
    ADVENTURE_STATES[uid] = sc_idx

    from kb import adventure_choice_kb
    gif_tag = f"<a href='{data.AMG_GIFS['autobahn']}'>&#8205;</a>"
    car = CAR_CATALOG[pc["car_key"]]

    await message.answer(
        f"{gif_tag}🌃 <b>НОЧНОЕ ПОХОЖДЕНИЕ AMG: {scenario['title'].upper()}</b>\n\n"
        f"🚗 Твой болид: <b>{car['name']}</b>\n\n"
        f"📖 <i>{scenario['desc']}</i>\n\n"
        f"<b>Сделай свой выбор:</b>",
        reply_markup=adventure_choice_kb(sc_idx, scenario["choices"])
    )


@router.callback_query(F.data.startswith("adv:choice:"))
async def cb_adventure_choice(cb: CallbackQuery):
    parts = cb.data.split(":")
    sc_idx = int(parts[2])
    ch_idx = int(parts[3])
    uid = cb.from_user.id

    p = await db.get_player(uid)
    pc = await db.get_selected_car(uid)
    if not pc or p["energy"] < 2:
        return await cb.answer("Недостаточно энергии (нужно 2 ⚡)!", show_alert=True)

    await db.use_energy(uid)
    await db.use_energy(uid)

    scenario = data.ADVENTURE_SCENARIOS[sc_idx]
    choice = scenario["choices"][ch_idx]
    car = CAR_CATALOG[pc["car_key"]]
    st = calc_stats(car, car_upgrades(pc))

    # Рассчитываем шанс успеха в зависимости от соответствия характеристик
    req = choice["req_stat"]
    chance = 0.70
    if req == "power" and st["power"] > 400:
        chance += 0.20
    elif req == "speed" and st["speed"] > 270:
        chance += 0.20
    elif req == "acceleration" and st["acceleration"] < 4.0:
        chance += 0.20
    elif req == "handling" and st["handling"] > 70:
        chance += 0.20

    is_success = random.random() < chance

    if is_success:
        await db.add_money(uid, choice["win_money"])
        await db.add_coins_admin(uid, choice["win_coins"], reason=f"Похождение: {scenario['title']}")
        await db.add_xp(uid, choice["win_xp"])
        gif_tag = f"<a href='{data.AMG_GIFS['drift']}'>&#8205;</a>"
        await cb.message.edit_text(
            f"{gif_tag}✅ <b>УСПЕХ! ВЫБОР СРАБОТАЛ ИДЕАЛЬНО!</b>\n\n"
            f"<i>{choice['success_text']}</i>\n\n"
            f"🎁 <b>Твоя добыча:</b>\n"
            f"• 💰 +${fmt(choice['win_money'])}\n"
            f"• 🪙 +{choice['win_coins']} монет AMG\n"
            f"• 📈 +{choice['win_xp']} XP\n\n"
            "Ночь удалась! Отправляйся в следующее похождение: <code>/adventure</code>",
            reply_markup=None
        )
    else:
        gif_tag = f"<a href='{data.AMG_GIFS['crash']}'>&#8205;</a>"
        await cb.message.edit_text(
            f"{gif_tag}⚠️ <b>НЕУДАЧА! ЧТО-ТО ПОШЛО НЕ ПО ПЛАНУ...</b>\n\n"
            "Соперники оказались быстрее, или на пути возникли непредвиденные помехи! "
            "К счастью, машина цела, но сорвать куш на этот раз не удалось.\n\n"
            "<i>Прокачай двигатель и подвеску в /menu ➡️ Тюнинг и повтори попытку!</i>",
            reply_markup=None
        )


# ── Драг-рейсинг 402м в чате (/drag) ──────────────────────────

DRAG_RACES = {}  # chat_id -> {challenger_id, challenger_name, opponent_id, opponent_name, state, start_time}


@router.message(Command("drag"))
async def cmd_drag(message: Message):
    if message.chat.type == "private":
        return await message.answer("🚦 Драг-рейсинг доступен только в группах! Добавь бота в чат и пиши /drag")

    chat_id = message.chat.id
    uid = message.from_user.id
    pc = await db.get_selected_car(uid)
    if not pc:
        return await message.answer("Сначала выбери авто в /start!")

    drag_id = f"{chat_id}_{random.randint(1000, 9999)}"
    DRAG_RACES[chat_id] = {
        "drag_id": drag_id,
        "challenger_id": uid,
        "challenger_name": message.from_user.first_name,
        "opponent_id": None,
        "opponent_name": None,
        "state": "waiting"
    }

    from kb import drag_ready_kb
    gif_tag = f"<a href='{data.AMG_GIFS['drag']}'>&#8205;</a>"
    car = CAR_CATALOG[pc["car_key"]]

    await message.answer(
        f"{gif_tag}🚦 <b>УЛИЧНЫЙ ДРАГ-РЕЙСИНГ НА 402 МЕТРА!</b> 🚦\n\n"
        f"🏁 На стартовой полосе: <b>{message.from_user.first_name}</b> на <b>{car['name']}</b>!\n\n"
        "Кто готов бросить вызов на четверть мили?\n"
        "Победитель забирает славу и <b>+25 🪙 монет</b>!\n\n"
        "Жми кнопку соперника! 👇",
        reply_markup=drag_ready_kb(drag_id)
    )


@router.callback_query(F.data.startswith("drag:join:"))
async def cb_drag_join(cb: CallbackQuery):
    chat_id = cb.message.chat.id
    drag = DRAG_RACES.get(chat_id)
    if not drag or drag["state"] != "waiting":
        return await cb.answer("Заезд уже начался или отменен!", show_alert=True)

    uid = cb.from_user.id
    if uid == drag["challenger_id"]:
        return await cb.answer("Ты уже на старте! Жди соперника.", show_alert=True)

    pc = await db.get_selected_car(uid)
    if not pc:
        return await cb.answer("Сначала выбери авто в /start!", show_alert=True)

    drag["opponent_id"] = uid
    drag["opponent_name"] = cb.from_user.first_name
    drag["state"] = "countdown"

    import asyncio
    from kb import drag_launch_kb

    car1 = drag["challenger_name"]
    car2 = drag["opponent_name"]
    await cb.message.edit_text(
        f"🚦 <b>ОБА БОЛИДА НА ПОЛОСЕ!</b>\n\n"
        f"🏎 <b>{car1}</b> против <b>{car2}</b>\n\n"
        "Внимание на светофор...\n"
        "🔴 🔴 🔴"
    )
    await asyncio.sleep(1.5)
    await cb.message.edit_text(
        f"🚦 <b>ПРОГРЕВ РЕЗИНЫ...</b>\n\n"
        f"🏎 <b>{car1}</b> против <b>{car2}</b>\n\n"
        "🔴 🔴 🟡"
    )
    await asyncio.sleep(1.5)

    import time
    drag["launch_time"] = time.time()
    drag["state"] = "launched"

    gif_tag = f"<a href='{data.AMG_GIFS['burnout']}'>&#8205;</a>"
    await cb.message.edit_text(
        f"{gif_tag}🟢 🟢 🟢 <b>ЗЕЛЁНЫЙ! ГАЗ В ПОЛ! СТАРТ!</b> 🟢 🟢 🟢\n\n"
        f"ЖМИ КНОПКУ ПЕРВЫМ! 👇",
        reply_markup=drag_launch_kb(drag["drag_id"])
    )


@router.callback_query(F.data.startswith("drag:launch:"))
async def cb_drag_launch(cb: CallbackQuery):
    chat_id = cb.message.chat.id
    drag = DRAG_RACES.get(chat_id)
    if not drag or drag["state"] != "launched":
        return await cb.answer("Заезд уже завершен!", show_alert=True)

    uid = cb.from_user.id
    if uid not in (drag["challenger_id"], drag["opponent_id"]):
        return await cb.answer("Ты не участвуешь в этом заезде!", show_alert=True)

    import time
    reaction = round(time.time() - drag["launch_time"], 3)
    drag["state"] = "finished"

    winner_name = cb.from_user.first_name
    loser_name = drag["opponent_name"] if uid == drag["challenger_id"] else drag["challenger_name"]

    # Награда
    await db.add_coins_admin(uid, 25, reason="Победа в Драг-рейсинге 402м")
    await db.add_money(uid, 30000)
    await db.add_xp(uid, 200)

    gif_tag = f"<a href='{data.AMG_GIFS['win']}'>&#8205;</a>"
    await cb.message.edit_text(
        f"{gif_tag}🏁 <b>ФИНИШ 402 МЕТРА! ПОБЕДА!</b>\n\n"
        f"🥇 <b>{winner_name}</b> показал молниеносную реакцию: <b>{reaction} сек</b>!\n"
        f"🥈 <i>{loser_name}</i> отстал на пол-корпуса.\n\n"
        f"💰 Награда победителю: <b>+25 🪙 монет</b>, <b>+$30,000</b> и <b>+200 XP</b>!\n\n"
        "Сыграть ещё: <code>/drag</code>"
    )
    DRAG_RACES.pop(chat_id, None)


