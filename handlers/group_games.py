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

