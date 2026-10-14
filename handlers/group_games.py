import html
import logging
from datetime import datetime
import random
import time
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton as Btn

import db
import data
from data import CAR_CATALOG, fmt
from engine import calc_stats, car_upgrades
from kb import boss_kb
from utils import is_admin

logger = logging.getLogger("amg.group_games")

router = Router(name="group_games")

BOSS_COOLDOWN = 0        # Без таймаутов!
QUIZ_COOLDOWN = 3 * 3600  # 3 часа строго (защита от накрутки)
AIRDROP_COOLDOWN = 60     # 1 минута
CHASE_COOLDOWN = 0        # Без таймаутов!
TOURNAMENT_COOLDOWN = 60  # 1 минута
ROYALE_COOLDOWN = 60      # 1 минута
DRAG_COOLDOWN = 30        # 30 секунд


async def check_chat_cooldown(chat_id: int, game_key: str, cooldown_sec: int) -> tuple[bool, str]:
    """Проверяет кулдаун события в чате. Возвращает (активен_ли_кулдаун, строка_остатка_времени)."""
    now = time.time()
    last_ts = await db.get_cooldown(f"{game_key}:{chat_id}")
    if now - last_ts < cooldown_sec:
        rem = int(cooldown_sec - (now - last_ts))
        rem_h = rem // 3600
        rem_m = (rem % 3600) // 60
        rem_s = rem % 60
        if rem_h > 0:
            time_str = f"{rem_h} ч. {rem_m} мин."
        elif rem_m > 0:
            time_str = f"{rem_m} мин."
        else:
            time_str = f"{rem_s} сек."
        return True, time_str
    return False, ""


BOSS_NAMES = [
    ("Шеф полиции на броне-Гелике", "g63", 3000),
    ("Призрак автобана на AMG ONE", "amg_one", 5000),
    ("Король ночного Берлина на GT Black Series", "gt_bs", 4000),
    ("Стритрейсер-тяжеловес на GLE 63 S", "gle63s", 3500),
]


def get_boss_age_seconds(boss: dict) -> float:
    c = boss.get("created_at")
    if not c:
        return 0.0
    if isinstance(c, datetime):
        return max(0.0, (datetime.utcnow() - c.replace(tzinfo=None)).total_seconds())
    for fmt_str in (db.TS_FMT, "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            dt = datetime.strptime(str(c)[:19], fmt_str)
            return max(0.0, (datetime.utcnow() - dt).total_seconds())
        except Exception:
            pass
    return 0.0


@router.message(Command("boss", "resetboss", "boss_reset", "killboss"))
async def cmd_boss(message: Message):
    if message.chat.type == "private":
        return await message.answer("👾 Рейд на босса доступен только в группах! Добавь бота в чат и пиши /boss")

    chat_id = message.chat.id
    cmd_text = (message.text or "").strip().lower()
    is_reset_cmd = any(w in cmd_text for w in ("reset", "clear", "kill"))

    boss = await db.get_active_boss(chat_id)

    # Ручной сброс босса
    if is_reset_cmd:
        if not boss:
            return await message.answer("ℹ️ В этом чате сейчас нет активного босса.")

        uid = message.from_user.id
        is_user_adm = is_admin(uid)
        if not is_user_adm:
            try:
                member = await message.bot.get_chat_member(chat_id, uid)
                if member.status in ("creator", "administrator"):
                    is_user_adm = True
            except Exception:
                pass

        age = get_boss_age_seconds(boss)
        if not is_user_adm and age < 900:
            rem = int(900 - age) // 60
            return await message.answer(
                f"⏳ Сбросить босса может админ чата, либо любой игрок через {rem} мин. бездействия!"
            )

        await db.delete_boss(chat_id)
        return await message.answer(
            f"🏳️ <b>Босс «{boss['boss_name']}» успешно сброшен!</b>\n\n"
            f"Город свободен. Теперь вы можете вызвать нового свежего босса через /boss!"
        )

    if not boss:
        if BOSS_COOLDOWN > 0:
            on_cd, rem_t = await check_chat_cooldown(chat_id, "boss", BOSS_COOLDOWN)
            if on_cd:
                return await message.answer(
                    f"⏳ <b>Рейдовый босс в этом чате уже был повержен!</b>\n\n"
                    f"Следующий босс появится через: <b>{rem_t}</b>.\n"
                    f"<i>Пока ждёшь, устрой дуэль (/duel) или собери турнир (/tournament)!</i>"
                )
        boss_data = random.choice(data.BOSS_ROSTER)
        boss = await db.create_boss(chat_id, boss_data["name"], boss_data["car_key"], boss_data["hp"])
        car = CAR_CATALOG[boss_data["car_key"]]
        gif_tag = f"<a href='{data.AMG_GIFS['boss']}'>&#8205;</a>"
        await message.answer(
            f"{gif_tag}🚨 <b>ТРЕВОГА В ЧАТЕ! ПОЯВИЛСЯ РЕЙДОВЫЙ БОСС!</b>\n\n"
            f"👤 <b>{boss_data['name']}</b>\n"
            f"🚗 Машина: {car['emoji']} <b>{car['name']}</b>\n"
            f"❤️ Прочность: <b>{fmt(boss['current_hp'])}/{fmt(boss['max_hp'])} HP</b>\n"
            f"⚡ Способность: <i>{boss_data['ability']}</i>\n"
            f"💬 <i>{boss_data['phrase']}</i>\n\n"
            f"🎁 <b>Призовой фонд победы:</b> {boss_data['coins_pool']} 🪙 монет\n"
            f"🏆 Дополнительный трофей: <b>{boss_data['loot']}</b>\n\n"
            "Объединяйтесь всем чатом! Выбирайте обычный таран или мощный Нитро-удар! 👇",
            reply_markup=boss_kb(can_flee=False)
        )
    else:
        pct = int(boss['current_hp'] / boss['max_hp'] * 100)
        bar_len = max(0, min(10, int(boss['current_hp'] / boss['max_hp'] * 10)))
        bar = "▰" * bar_len + "▱" * (10 - bar_len)
        gif_tag = f"<a href='{data.AMG_GIFS['boss_rage']}'>&#8205;</a>" if pct <= 40 else f"<a href='{data.AMG_GIFS['boss']}'>&#8205;</a>"
        rage_note = "\n⚠️ <b>ВНИМАНИЕ: БОСС ВПАЛ В ЯРОСТЬ!</b> Контратаки усилены!" if pct <= 40 else ""
        can_flee = get_boss_age_seconds(boss) > 300
        await message.answer(
            f"{gif_tag}👾 <b>Босс: {boss['boss_name']}</b>\n"
            f"❤️ {bar} <b>{fmt(boss['current_hp'])}/{fmt(boss['max_hp'])} HP</b> ({pct}%){rage_note}\n\n"
            "Все на таран! Давите газ в пол! 👇",
            reply_markup=boss_kb(can_flee=can_flee)
        )


async def execute_boss_strike(cb: CallbackQuery, is_nitro: bool = False):
    """Общая логика нанесения урона боссу (обычный таран или нитро-удар)."""
    try:
        uid = cb.from_user.id
        chat_id = cb.message.chat.id
        boss = await db.get_active_boss(chat_id)
        if not boss:
            return await cb.answer("Босс уже повержен или скрылся!", show_alert=True)

        # 1. ОБЯЗАТЕЛЬНО восстанавливаем энергию игрока перед проверкой!
        await db.regen_energy(uid)
        p = await db.get_player(uid)
        if not p:
            return await cb.answer("Сначала запусти игру в /start!", show_alert=True)

        pc = await db.get_selected_car(uid)
        if not pc:
            return await cb.answer("Сначала выбери авто в /start!", show_alert=True)

        energy_cost = 2 if is_nitro else 1
        if p["energy"] < energy_cost:
            return await cb.answer(
                f"⚡ Нужно {energy_cost} энергии! У тебя сейчас {p['energy']}⚡.\n"
                f"Энергия пополняется бесплатно (+1 каждые 30 мин) или в /shop за 60 🪙.",
                show_alert=True
            )

        car = CAR_CATALOG.get(pc["car_key"], CAR_CATALOG["c180"])
        st = calc_stats(car, car_upgrades(pc))

        # Базовый урон от характеристик авто
        dmg_mult = random.uniform(0.85, 1.25)
        base_dmg = max(50, int(st["rating"] * dmg_mult))

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

        # Списываем энергию только при успешном нанесении урона
        for _ in range(energy_cost):
            await db.use_energy(uid)

        crit_alert = " 💥 КРИТ!" if is_crit else ""
        strike_type = "🔥 НИТРО" if is_nitro else "💥 ТАРАН"

        # Мгновенный отклик игроку с остатком HP босса
        if dead:
            await cb.answer(f"🏆 ФИНИШНЫЙ УДАР! -{fmt(base_dmg)} HP! БОСС УНИЧТОЖЕН!", show_alert=False)
        else:
            await cb.answer(f"{strike_type}: -{fmt(base_dmg)} HP! (Осталось: {fmt(cur_hp)} HP){crit_alert}", show_alert=False)

        if dead:
            # 1. Считываем участников рейда перед удалением босса
            damagers = await db.get_boss_damagers(chat_id)
            if not damagers:
                damagers = [{"user_id": uid, "first_name": cb.from_user.first_name, "damage": base_dmg}]

            await db.delete_boss(chat_id)
            await db.set_cooldown(f"boss:{chat_id}", time.time())

            # Определяем призовой фонд побежденного босса
            boss_info = next(
                (b for b in data.BOSS_ROSTER if b.get("name") == boss.get("boss_name") or b.get("car_key") == boss.get("boss_car")),
                None
            )
            total_pool = boss_info["coins_pool"] if boss_info else 500
            total_xp_pool = max(2500, int(total_pool * 5))
            total_damage = sum(d["damage"] for d in damagers) or 1

            boost = await db.get_chat_boost(chat_id)
            boost_mult = 2 if boost else 1
            boost_note = f"\n\n🔥 <b>Применён Буст чата x2! Награды удвоены спонсором {boost['sponsor_name']}!</b>" if boost else ""

            # Справедливое распределение призового фонда босса по доле урона!
            # Начисление НАПРЯМУЮ через add_coins (без дневных урезаний soft-cap!)
            user_rewards = {}
            for i, d in enumerate(damagers):
                target_uid = d["user_id"]
                dmg_share = d["damage"] / total_damage

                if len(damagers) == 1:
                    c_reward = total_pool
                    x_reward = total_xp_pool
                elif i == 0:
                    # 1 место: минимум 35% призового фонда или пропорционально урону
                    c_reward = max(int(total_pool * 0.35), int(total_pool * dmg_share))
                    x_reward = max(1200, int(total_xp_pool * dmg_share))
                elif i < 3:
                    c_reward = max(25, int(total_pool * dmg_share))
                    x_reward = max(600, int(total_xp_pool * dmg_share))
                else:
                    c_reward = max(15, int(total_pool * dmg_share))
                    x_reward = max(250, int(total_xp_pool * dmg_share))

                c_reward *= boost_mult
                x_reward *= boost_mult

                user_rewards[target_uid] = {"coins": c_reward, "xp": x_reward}
                await db.add_coins(target_uid, c_reward, reason=f"Победа над боссом {boss['boss_name']}")
                await db.add_xp(target_uid, x_reward)

            medals = ["🥇", "🥈", "🥉"]
            lines = []
            for i, d in enumerate(damagers[:8]):
                m = medals[i] if i < 3 else f"{i + 1}."
                safe_name = html.escape(d.get("first_name") or "Гонщик")
                rew = user_rewards.get(d["user_id"], {"coins": 0, "xp": 0})
                lines.append(f"{m} <b>{safe_name}</b> — <b>{fmt(d['damage'])}</b> HP (+{fmt(rew['coins'])} 🪙, +{fmt(rew['xp'])} XP)")

            # Редактируем старое сообщение босса, убирая кнопки
            try:
                killer_name = html.escape(cb.from_user.first_name)
                await cb.message.edit_text(
                    f"🏆 <b>БОСС «{boss['boss_name']}» ПОЛНОСТЬЮ УНИЧТОЖЕН!</b>\n\n"
                    f"💀 Победный таран нанёс: <b>{killer_name}</b>!\n"
                    f"🎉 Призовой фонд <b>{fmt(total_pool * boost_mult)} 🪙 монет</b> распределён между героями битвы!",
                    reply_markup=None
                )
            except Exception:
                pass

            gif_tag = f"<a href='{data.AMG_GIFS['win']}'>&#8205;</a>"
            await cb.message.answer(
                f"{gif_tag}🏆 <b>БОСС «{boss['boss_name']}» ПОЛНОСТЬЮ УНИЧТОЖЕН!</b>\n\n"
                f"🎉 Чат одержал сокрушительную победу! Призовой фонд <b>{fmt(total_pool * boost_mult)} 🪙 монет</b> распределён между всеми участниками битвы по нанесённому урону!{boost_note}\n\n"
                f"👑 <b>ГЕРОИ БИТВЫ И ПОЛУЧЕННЫЕ НАГРАДЫ:</b>\n" + ("\n".join(lines) if lines else "—")
            )
        else:
            # Обновляем сообщение босса в чате
            pct = int(cur_hp / boss['max_hp'] * 100)
            bar_len = max(0, min(10, int(cur_hp / boss['max_hp'] * 10)))
            bar = "▰" * bar_len + "▱" * (10 - bar_len)
            gif_tag = f"<a href='{data.AMG_GIFS['boss_rage']}'>&#8205;</a>" if pct <= 40 else f"<a href='{data.AMG_GIFS['boss']}'>&#8205;</a>"
            rage_warning = "\n⚠️ <b>ФАЗА ЯРОСТИ:</b> Босс огрызается и выпускает клубы дыма!" if pct <= 40 else ""
            can_flee = get_boss_age_seconds(boss) > 900
            attacker_name = html.escape(cb.from_user.first_name)

            try:
                await cb.message.edit_text(
                    f"{gif_tag}👾 <b>Босс: {boss['boss_name']}</b>\n"
                    f"❤️ {bar} <b>{fmt(cur_hp)}/{fmt(boss['max_hp'])} HP</b> ({pct}%){rage_warning}\n\n"
                    f"⚡ Последняя атака: <b>{attacker_name}</b> ({strike_type} -{fmt(base_dmg)} HP!{crit_alert})\n\n"
                    "Продолжайте натиск! 👇",
                    reply_markup=boss_kb(can_flee=can_flee)
                )
            except Exception:
                pass

    except Exception as e:
        logger.exception("Error in execute_boss_strike: %s", e)
        try:
            await cb.answer("⚠️ Ошибка атаки. Попробуйте ещё раз.", show_alert=True)
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
        return await cb.answer("Босс уже повержен или скрылся!", show_alert=True)
    pct = int(boss['current_hp'] / boss['max_hp'] * 100)
    bar_len = max(0, min(10, int(boss['current_hp'] / boss['max_hp'] * 10)))
    bar = "▰" * bar_len + "▱" * (10 - bar_len)
    gif_tag = f"<a href='{data.AMG_GIFS['boss_rage']}'>&#8205;</a>" if pct <= 40 else f"<a href='{data.AMG_GIFS['boss']}'>&#8205;</a>"
    can_flee = get_boss_age_seconds(boss) > 900
    try:
        await cb.message.edit_text(
            f"{gif_tag}👾 <b>Босс: {boss['boss_name']}</b>\n"
            f"❤️ {bar} <b>{fmt(boss['current_hp'])}/{fmt(boss['max_hp'])} HP</b> ({pct}%)\n\n"
            "Все на таран! Давите газ в пол! 👇",
            reply_markup=boss_kb(can_flee=can_flee)
        )
    except Exception:
        pass
    await cb.answer(f"❤️ Текущее HP: {fmt(boss['current_hp'])}/{fmt(boss['max_hp'])} HP ({pct}%)", show_alert=True)


@router.callback_query(F.data == "boss:stats")
async def cb_boss_stats(cb: CallbackQuery):
    chat_id = cb.message.chat.id
    damagers = await db.get_boss_damagers(chat_id)
    if not damagers:
        return await cb.answer("Ещё никто не нанёс урон!", show_alert=True)
    medals = ["🥇", "🥈", "🥉"]
    lines = [f"{medals[i] if i < 3 else str(i+1)+'.'} {d['first_name']} — {fmt(d['damage'])} HP" for i, d in enumerate(damagers[:10])]
    await cb.answer("\n".join(lines), show_alert=True)


@router.callback_query(F.data == "boss:flee")
async def cb_boss_flee(cb: CallbackQuery):
    chat_id = cb.message.chat.id
    boss = await db.get_active_boss(chat_id)
    if not boss:
        return await cb.answer("Босс уже повержен или не активен!", show_alert=True)

    uid = cb.from_user.id
    is_user_adm = is_admin(uid)
    if not is_user_adm:
        try:
            member = await cb.bot.get_chat_member(chat_id, uid)
            if member.status in ("creator", "administrator"):
                is_user_adm = True
        except Exception:
            pass

    age = get_boss_age_seconds(boss)
    if not is_user_adm and age < 900:
        rem = int(900 - age) // 60
        return await cb.answer(f"⏳ Сбросить босса можно через {rem} мин. бездействия (или это может сделать админ чата)!", show_alert=True)

    await db.delete_boss(chat_id)
    await cb.answer("🏳️ Босс успешно сброшен!", show_alert=True)
    try:
        user_name = html.escape(cb.from_user.first_name)
        await cb.message.edit_text(
            f"💨 <b>РЕЙД ПРЕКРАЩЁН!</b>\n\n"
            f"👤 Игрок <b>{user_name}</b> отменил текущего босса.\n"
            f"Босс скрылся в тумане. Теперь вы можете вызвать нового босса командой /boss!",
            reply_markup=None
        )
    except Exception:
        pass



# ── Групповой Турнир / Гран-при чата (/tournament, /grouprace) ───────────

TOURNAMENTS: dict = {}  # chat_id -> {status, participants: [user_id], names: {uid: name}, cars: {uid: pc}}


async def start_tournament_recruitment(chat_id: int, organizer_name: str, send_fn):
    on_cd, rem_t = await check_chat_cooldown(chat_id, "tournament", TOURNAMENT_COOLDOWN)
    if on_cd:
        return await send_fn(f"⏳ <b>Гран-при чата уже проводился недавно!</b>\n\nСледующий заезд будет доступен через: <b>{rem_t}</b>.")

    if chat_id in TOURNAMENTS and TOURNAMENTS[chat_id]["status"] == "recruiting":
        return await send_fn("⚠️ Регистрация на Гран-при чата уже открыта! Жми кнопку ниже.")

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
    await send_fn(
        f"{gif_tag}🏆 <b>ГРАН-ПРИ ЧАТА ОБЪЯВЛЕН!</b>\n\n"
        f"Организатор: <b>{organizer_name}</b>\n\n"
        "Нажмите кнопку <b>«Участвовать»</b>, чтобы занять место на стартовой решетке.\n"
        "Каждый участник получает свой уникальный гоночный цвет 🟠🟡🟢🔵🟣🔴⚫️⚪️!\n"
        "Победители забирают кубки, монеты 🪙 и славу всего чата!\n\n"
        "Участников: <b>0</b>",
        reply_markup=kb
    )


@router.message(Command("tournament", "grouprace"))
async def cmd_tournament(message: Message):
    if message.chat.type == "private":
        return await message.answer("🏁 Гран-при и групповые заезды доступны только в группах! Добавь бота в чат и пиши /grouprace или /tournament")
    await start_tournament_recruitment(message.chat.id, message.from_user.first_name, message.answer)


@router.callback_query(F.data == "tourn:create")
async def cb_tourn_create(cb: CallbackQuery):
    await cb.answer()
    if cb.message.chat.type == "private":
        return await cb.message.answer("🏁 Заезды команд проводятся в группах! Добавь бота в свой чат.")
    await start_tournament_recruitment(cb.message.chat.id, cb.from_user.first_name, cb.message.answer)


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
    status_msg = await cb.message.edit_text("🚦 <b>3... 2... 1... ЗЕЛЕНЫЙ СВЕТ! СТАРТ ГРАН-ПРИ!</b>\nПелотон срывается с решетки в облаке дыма!")
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

    # Этап 1: Старт и первый сектор
    s1_scores = {}
    for uid in t["participants"]:
        pc = t["cars"][uid]
        car = CAR_CATALOG[pc["car_key"]]
        st = calc_stats(car, car_upgrades(pc))
        # Ускорение решает на старте
        accel_score = (15 - st["acceleration"]) * 20 * random.uniform(0.85, 1.25) + st["power"] * 0.1
        s1_scores[uid] = accel_score

    order_s1 = sorted(t["participants"], key=lambda u: s1_scores[u], reverse=True)
    leader_s1 = order_s1[0]
    lead_s1_col = participant_colors[leader_s1]
    lead_s1_name = t["names"][leader_s1]

    s1_grid = "\n".join(
        f"{i+1}. {participant_colors[u]} <b>{t['names'][u]}</b> ({CAR_CATALOG[t['cars'][u]['car_key']]['name']})"
        for i, u in enumerate(order_s1)
    )

    try:
        gif_tag = f"<a href='{data.AMG_GIFS['race']}'>&#8205;</a>"
        await status_msg.edit_text(
            f"{gif_tag}🚦 <b>ЭТАП 1: РАЗГОН И ПЕРВЫЙ СЕКТОР!</b>\n\n"
            f"⚡ Вперед вырывается: {lead_s1_col} <b>{lead_s1_name}</b>!\n\n"
            f"<b>Позиции в пелотоне:</b>\n{s1_grid}\n\n"
            "<i>Машины приближаются к связке скоростных поворотов...</i>"
        )
    except Exception:
        pass

    await asyncio.sleep(2.5)

    # Этап 2: Поворот и борьба
    s2_scores = {}
    for uid in t["participants"]:
        pc = t["cars"][uid]
        car = CAR_CATALOG[pc["car_key"]]
        st = calc_stats(car, car_upgrades(pc))
        turn_score = (st["handling"] * 1.5 + (3000 - st["weight"]) * 0.05) * random.uniform(0.85, 1.25)
        s2_scores[uid] = s1_scores[uid] + turn_score

    order_s2 = sorted(t["participants"], key=lambda u: s2_scores[u], reverse=True)
    leader_s2 = order_s2[0]
    lead_s2_col = participant_colors[leader_s2]
    lead_s2_name = t["names"][leader_s2]

    overtake_comment = (
        f"🔥 <b>СЕНСАЦИОННЫЙ ОБГОН!</b> {lead_s2_col} <b>{lead_s2_name}</b> режет апекс и вырывается на 1-е место!"
        if leader_s2 != leader_s1
        else f"🛡 {lead_s2_col} <b>{lead_s2_name}</b> мастерски держит траекторию и блокирует атаки соперников!"
    )

    s2_grid = "\n".join(
        f"{i+1}. {participant_colors[u]} <b>{t['names'][u]}</b>"
        for i, u in enumerate(order_s2)
    )

    try:
        gif_tag = f"<a href='{data.AMG_GIFS['drift']}'>&#8205;</a>"
        await status_msg.edit_text(
            f"{gif_tag}↩️ <b>ЭТАП 2: ШПИЛЬКА «КАРУСЕЛЬ» В ЗАНОСЕ!</b>\n\n"
            f"{overtake_comment}\n\n"
            f"<b>Позиции перед финишной прямой:</b>\n{s2_grid}\n\n"
            "<i>Педаль в пол на выходе! Впереди клетчатый флаг!</i>"
        )
    except Exception:
        pass

    await asyncio.sleep(2.5)

    # Финал: Максималка и спринт к финишу
    final_scores = []
    for uid in t["participants"]:
        pc = t["cars"][uid]
        car = CAR_CATALOG[pc["car_key"]]
        st = calc_stats(car, car_upgrades(pc))
        sprint_score = (st["speed"] * 0.8 + st["power"] * 0.4) * random.uniform(0.85, 1.25)
        total = s2_scores[uid] + sprint_score
        final_scores.append((total, uid, t["names"][uid], car["name"]))

    final_scores.sort(key=lambda x: x[0], reverse=True)

    boost = await db.get_chat_boost(chat_id)
    boost_mult = 2 if boost else 1
    boost_note = f"\n🔥 <b>Применён Буст чата x2! Награды удвоены спонсором {boost['sponsor_name']}!</b>\n" if boost else ""

    # Выдаем щедрые награды
    medals = ["🥇", "🥈", "🥉"]
    res_lines = []
    for i, (_, uid, name, car_name) in enumerate(final_scores):
        m = medals[i] if i < 3 else f"{i + 1}."
        col = participant_colors.get(uid, "🏎")
        if i == 0:
            c_g = await db.grant_coins(uid, 20 * boost_mult, reason="1 место в Гран-при чата")
            await db.add_xp(uid, 350 * boost_mult)
            reward_txt = f" (+{c_g} 🪙, +{350 * boost_mult} XP)"
        elif i == 1:
            c_g = await db.grant_coins(uid, 12 * boost_mult, reason="2 место в Гран-при чата")
            await db.add_xp(uid, 200 * boost_mult)
            reward_txt = f" (+{c_g} 🪙, +{200 * boost_mult} XP)"
        elif i == 2:
            c_g = await db.grant_coins(uid, 7 * boost_mult, reason="3 место в Гран-при чата")
            await db.add_xp(uid, 100 * boost_mult)
            reward_txt = f" (+{c_g} 🪙, +{100 * boost_mult} XP)"
        else:
            c_g = await db.grant_coins(uid, 3 * boost_mult, reason="Участие в Гран-при")
            await db.add_xp(uid, 40 * boost_mult)
            reward_txt = f" (+{c_g} 🪙, +{40 * boost_mult} XP)"

        res_lines.append(f"{m} {col} <b>{name}</b> ({car_name}){reward_txt}")

    winner_uid = final_scores[0][1]
    winner_name = final_scores[0][2]
    win_col = participant_colors.get(winner_uid, "🏎")
    gif_tag = f"<a href='{data.AMG_GIFS['win']}'>&#8205;</a>"
    try:
        await status_msg.edit_text(
            f"{gif_tag}🏁 <b>ФИНИШ ГРАН-ПРИ ЧАТА!</b>\n\n"
            f"🏆 Абсолютный чемпион: {win_col} <b>{winner_name}</b>!\n\n{boost_note}"
            f"📋 <b>Итоговый протокол заезда:</b>\n" + "\n".join(res_lines) +
            "\n\n<i>Запустить следующий заезд: /grouprace или /tournament</i>"
        )
    except Exception:
        pass
    TOURNAMENTS.pop(chat_id, None)
    await db.set_cooldown(f"tournament:{chat_id}", time.time())


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


@router.callback_query(F.data == "chase:restart")
async def cb_chase_restart(cb: CallbackQuery):
    chat_id = cb.message.chat.id
    if chat_id in CHASES:
        return await cb.answer("Погоня уже идёт! Участвуйте!", show_alert=True)
    await cb.answer("🚨 Новая облава! Погнали!")

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton as Btn
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [Btn(text="💨 Врубить форсаж!", callback_data="chase:nitro"),
         Btn(text="🛡 Прикрыть хвост!", callback_data="chase:block")],
        [Btn(text="↩️ Резкий вираж!", callback_data="chase:drift")],
    ])

    CHASES[chat_id] = {
        "distance": 100,
        "heat": 0,
        "crew": set(),
    }

    gif_tag = f"<a href='{data.AMG_GIFS['crash']}'>&#8205;</a>"
    await cb.message.answer(
        f"{gif_tag}🚨 <b>НОВАЯ ПОЛИЦЕЙСКАЯ ПОГОНЯ!</b>\n\n"
        f"Инициатор вылазки: <b>{cb.from_user.first_name}</b>\n\n"
        "Вся банда снова в деле! Никаких задержек — уходим от перехватчиков:\n"
        "Дистанция отрыва: <b>100 / 250 м</b>\n"
        "Уровень тревоги: <b>15%</b>\n\n"
        "Жмите кнопки! 👇",
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

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton as Btn
    restart_kb = InlineKeyboardMarkup(inline_keyboard=[
        [Btn(text="🚨 Начать новую погоню!", callback_data="chase:restart")]
    ])

    if ch["distance"] >= 250:
        # Успешный побег (БЕЗ ТАЙМАУТОВ!)
        gif_tag = f"<a href='{data.AMG_GIFS['win']}'>&#8205;</a>"
        crew_count = len(ch["crew"])
        boost = await db.get_chat_boost(chat_id)
        boost_mult = 2 if boost else 1
        boost_note = f"\n🔥 <b>Применён Буст чата x2! Награды удвоены спонсором {boost['sponsor_name']}!</b>" if boost else ""

        for u in ch["crew"]:
            await db.grant_coins(u, 12 * boost_mult, reason="Успешный уход от погони")
            await db.add_xp(u, 150 * boost_mult)
        CHASES.pop(chat_id, None)
        await cb.message.edit_text(
            f"{gif_tag}🏆 <b>БАНДА УШЛА В ОТРЫВ!</b>\n\n"
            f"Полиция потеряла след в ночном городе! Все участники ({crew_count} чел.) "
            f"получили награды (монеты 🪙 и опыт XP)!{boost_note}\n\n"
            "⚡ <i>Тайм-аутов нет — начинайте новую погоню кнопкой ниже или /chase!</i>",
            reply_markup=restart_kb
        )
    elif ch["heat"] >= 100:
        # Провал (БЕЗ ТАЙМАУТОВ!)
        gif_tag = f"<a href='{data.AMG_GIFS['crash']}'>&#8205;</a>"
        CHASES.pop(chat_id, None)
        await cb.message.edit_text(
            f"{gif_tag}🚓 <b>ПЕРЕХВАТ! БАНДА ЗАБЛОКИРОВАНА!</b>\n\n"
            "Полицейские выставили шипы и окружили колонну.\n\n"
            "⚡ <i>Тайм-аутов нет — реванш доступен сразу кнопкой ниже или /chase!</i>",
            reply_markup=restart_kb
        )
    else:
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
    on_cd, rem_t = await check_chat_cooldown(chat_id, "quiz", QUIZ_COOLDOWN)
    if on_cd:
        return await message.answer(
            f"⏳ <b>АВТО-ВИКТОРИНА AMG НЕДОСТУПНА!</b>\n\n"
            f"Викторина проводится строго <b>раз в 3 часа</b>.\n"
            f"Следующая викторина в этом чате будет доступна через: <b>{rem_t}</b>.\n\n"
            f"<i>Пока ждёшь, устрой дуэль (/duel), собери Гран-при (/tournament) или проверь одиночный заезд (/race)!</i>"
        )

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
        "active": True,
        "attempts": set(),
    }
    await db.set_cooldown(f"quiz:{chat_id}", time.time())

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton as Btn
    rows = []
    for i, opt in enumerate(shuffled_opts):
        rows.append([Btn(text=f"{chr(65+i)}. {opt}", callback_data=f"quiz:{i}")])

    await message.answer(
        "🧠 <b>АВТО-ВИКТОРИНА AMG ДЛЯ ЧАТА!</b>\n\n"
        f"<b>Вопрос:</b>\n{q_data['q']}\n\n"
        "<i>Кто первым нажмет правильный ответ — забирает +20 🪙 монет и +150 XP!</i>\n"
        "⚠️ <i>У каждого участника ровно одна попытка ответа.</i>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
    )


@router.callback_query(F.data.startswith("quiz:"))
async def cb_quiz_answer(cb: CallbackQuery):
    chat_id = cb.message.chat.id
    qz = ACTIVE_QUIZZES.get(chat_id)
    if not qz or not qz.get("active"):
        return await cb.answer("Эта викторина уже завершена! Следующая через 3 часа.", show_alert=True)

    uid = cb.from_user.id
    if uid in qz.get("attempts", set()):
        return await cb.answer("❌ Ты уже дал свой ответ! Один вопрос — одна попытка.", show_alert=True)
    qz.setdefault("attempts", set()).add(uid)

    ans_idx = int(cb.data.split(":")[1])
    uname = cb.from_user.first_name

    if ans_idx == qz["correct"]:
        qz["active"] = False
        boost = await db.get_chat_boost(chat_id)
        boost_mult = 2 if boost else 1
        boost_note = f"\n🔥 <i>(Применён Буст чата x2 от спонсора {boost['sponsor_name']}!)</i>" if boost else ""

        earned = await db.grant_coins(uid, 20 * boost_mult, reason="Победа в чат-викторине")
        await db.add_xp(uid, 150 * boost_mult)
        await cb.answer("🎉 ПРАВИЛЬНО! Ты выиграл!", show_alert=True)
        fact_text = qz["q"]["fact"]
        await cb.message.edit_text(
            f"🏆 <b>ПОБЕДИТЕЛЬ ВИКТОРИНЫ: {uname}!</b>\n\n"
            f"✅ <b>Верный ответ:</b> {qz['q']['opts'][qz['q']['correct']]}\n\n"
            f"💡 <i>{fact_text}</i>\n\n"
            f"💰 Награда <b>+{earned} 🪙 монет</b> и <b>+{150 * boost_mult} XP</b> начислена {uname}!{boost_note}\n\n"
            "⏳ <i>Следующая авто-викторина будет доступна через <b>3 часа</b>.</i>"
        )
        ACTIVE_QUIZZES.pop(chat_id, None)
    else:
        await cb.answer("❌ Неверно! Твоя попытка исчерпана.", show_alert=True)


# ── 2. Аирдроп контейнера с лутом (/airdrop, /drop) ──────────

AIRDROPS: dict = {}  # chat_id -> {"participants": set, "names": dict, "status": str}


@router.message(Command("airdrop", "drop"))
async def cmd_airdrop(message: Message):
    if message.chat.type == "private":
        return await message.answer("📦 Аирдроп доступен только в группах! Добавь бота в чат и пиши /airdrop")

    chat_id = message.chat.id
    if chat_id in AIRDROPS and AIRDROPS[chat_id]["status"] == "waiting":
        return await message.answer("⚠️ В чате уже сброшен контейнер! Жмите кнопку ниже, чтобы взломать.")

    on_cd, rem_t = await check_chat_cooldown(chat_id, "airdrop", AIRDROP_COOLDOWN)
    if on_cd:
        return await message.answer(
            f"⏳ <b>Контейнер с лутом уже сбрасывался недавно!</b>\n\n"
            f"Следующий аирдроп будет доступен через: <b>{rem_t}</b>."
        )

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
    boost = await db.get_chat_boost(chat_id)
    boost_mult = 2 if boost else 1
    boost_note = f"\n🔥 <b>Применён Буст чата x2! Награды удвоены спонсором {boost['sponsor_name']}!</b>\n" if boost else ""

    for i, uid in enumerate(plist):
        name = dr["names"][uid]
        m = medals[i] if i < 3 else "📦"
        if i == 0:
            coins, xp = 16, 300
        elif i == 1:
            coins, xp = 10, 200
        elif i == 2:
            coins, xp = 6, 150
        else:
            coins, xp = 3, 80

        c_g = await db.grant_coins(uid, coins * boost_mult, reason="Аирдроп контейнера в чате")
        await db.add_xp(uid, xp * boost_mult)
        res_lines.append(f"{m} <b>{name}</b> — <b>+{c_g} 🪙</b>, +{xp * boost_mult} XP")

    gif_tag = f"<a href='{data.AMG_GIFS['win']}'>&#8205;</a>"
    await cb.message.edit_text(
        f"{gif_tag}🎉 <b>КОНТЕЙНЕР AMG PERFORMANCE ВСКРЫТ!</b>\n\n{boost_note}"
        "Лут поделён между участниками рейда:\n\n"
        + "\n".join(res_lines) +
        "\n\n<i>Запустить новый дроп: /airdrop</i>"
    )
    AIRDROPS.pop(chat_id, None)
    await db.set_cooldown(f"airdrop:{chat_id}", time.time())


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

    on_cd, rem_t = await check_chat_cooldown(chat_id, "royale", ROYALE_COOLDOWN)
    if on_cd:
        return await message.answer(
            f"⏳ <b>Королевская битва уже проходила недавно!</b>\n\n"
            f"Следующая битва на выбывание будет доступна через: <b>{rem_t}</b>."
        )

    ROYALES[chat_id] = {
        "participants": [],
        "names": {},
        "cars": {},
        "status": "recruiting"
    }

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton as Btn
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [Btn(text="🏎 Занять место на старте!", callback_data="royale:join")],
        [Btn(text="🟢 СТАРТ ВЫБЫВАНИЯ (мин. 2)", callback_data="royale:start")],
    ])

    gif_tag = f"<a href='{data.AMG_GIFS['race']}'>&#8205;</a>"
    await message.answer(
        f"{gif_tag}👑 <b>КОРОЛЕВСКАЯ БИТВА НА ВЫБЫВАНИЕ (ROYALE)!</b>\n\n"
        f"Организатор: <b>{message.from_user.first_name}</b>\n\n"
        "Правила просты: каждый круг самый неудачливый гонщик вылетает из гонки!\n"
        "Выживает только один — <b>Король Автобана</b> забирает джекпот: <b>+25 🪙 монет</b>!\n\n"
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
    w_pc = ry["cars"][winner_id]
    winner_car = CAR_CATALOG[w_pc["car_key"]]["name"]
    w_plate = f" <code>[{w_pc['plate']}]</code>" if w_pc.get("plate") else ""

    # Награда победителю
    boost = await db.get_chat_boost(chat_id)
    boost_mult = 2 if boost else 1
    boost_note = f"\n🔥 <i>(Применён Буст чата x2 от спонсора {boost['sponsor_name']}!)</i>" if boost else ""

    earned = await db.grant_coins(winner_id, 25 * boost_mult, reason="1 место в Royal Выбывании")
    await db.add_xp(winner_id, 500 * boost_mult)

    gif_tag = f"<a href='{data.AMG_GIFS['win']}'>&#8205;</a>"
    log_text = "\n".join(rounds_log)
    await cb.message.edit_text(
        f"{gif_tag}👑 <b>ФИНИШ БИТВЫ НА ВЫБЫВАНИЕ!</b>\n\n"
        f"<b>Хроника заезда:</b>\n{log_text}\n\n"
        f"🏆 <b>ЕДИНСТВЕННЫЙ ВЫЖИВШИЙ ЧЕМПИОН:</b>\n"
        f"🥇 <b>{winner_name}</b> на <b>{winner_car}</b>{w_plate}!\n\n"
        f"💰 Награда победителя: <b>+{earned} 🪙 монет</b> и <b>+{500 * boost_mult} XP</b>!{boost_note}\n"
        "Сыграть ещё: <code>/royale</code>"
    )
    ROYALES.pop(chat_id, None)
    await db.set_cooldown(f"royale:{chat_id}", time.time())


# ── Колесо Фортуны AMG (/wheel, /spin) ──────────────────────────

@router.message(Command("wheel"))
@router.message(Command("spin"))
async def cmd_wheel(message: Message):
    if message.chat.type == "private":
        return await message.answer("🎰 Колесо Фортуны доступно только в командном чате! Добавь бота в группу и пиши /wheel")
    gif_tag = f"<a href='{data.AMG_GIFS['wheel']}'>&#8205;</a>"
    from kb import wheel_kb
    uid = message.from_user.id
    p = await db.get_player(uid)
    today = db.now_str()[:10]
    extra = p.get("extra_spins", 0) if p else 0
    is_spinned = bool(p and p.get("last_wheel_spin") == today)
    bot_info = await message.bot.get_me()

    if is_spinned and extra == 0:
        spin_note = (
            "⏳ <b>Бесплатный спин на сегодня уже использован!</b>\n"
            "Не хочешь ждать 24 часа? Возьми доп. вращения за Telegram Stars ⭐️ без очереди:"
        )
    elif is_spinned and extra > 0:
        spin_note = (
            f"🎰 <b>Бесплатный спин использован, но у тебя есть {extra} доп. спин(ов)!</b>\n"
            "Жми кнопку ниже, чтобы крутить рулетку прямо сейчас:"
        )
    else:
        spin_note = "Каждый гонщик может крутить рулетку <b>1 раз в сутки бесплатно</b>!"

    await message.answer(
        f"{gif_tag}🎰 <b>КОЛЕСО ФОРТУНЫ MERCEDES-AMG</b> 🎰\n\n"
        "Испытай удачу на сходке стритрейсеров!\n"
        f"{spin_note}\n\n"
        "🎁 <b>Возможные призы:</b>\n"
        "• До <b>150 🪙 золотых монет</b>\n"
        "• Дополнительная ⚡ энергия и 📈 опыт\n"
        "• <i>(Осторожно: есть шанс нарваться на штраф от ДПС!)</i>\n\n"
        "Выбирай действие ниже! 👇",
        reply_markup=wheel_kb(extra, is_spinned, bot_info.username if message.chat.type != "private" else "")
    )


async def execute_wheel_spin(cb: CallbackQuery, is_extra: bool = False):
    uid = cb.from_user.id
    today = db.now_str()[:10]
    p = await db.get_player(uid)
    if not p:
        return await cb.answer("Сначала напиши /start!", show_alert=True)

    if is_extra:
        if p.get("extra_spins", 0) <= 0:
            return await cb.answer("У тебя нет дополнительных спинов!", show_alert=True)
        await db.increment(uid, extra_spins=-1)
    else:
        await db.update_player(uid, last_wheel_spin=today)

    weights = [item["weight"] for item in data.WHEEL_PRIZES]
    prize = random.choices(data.WHEEL_PRIZES, weights=weights, k=1)[0]

    ptype = prize["type"]
    pval = prize["val"]
    if ptype == "coins":
        await db.grant_coins(uid, pval, reason="Колесо Фортуны AMG")
    elif ptype == "energy":
        cur_e = p["energy"]
        max_e = p["max_energy"]
        new_e = min(max_e, cur_e + pval)
        await db.update_player(uid, energy=new_e)
    elif ptype == "xp":
        await db.add_xp(uid, pval)
    elif ptype == "fine":
        await db.spend_coins(uid, pval)

    p_upd = await db.get_player(uid)
    rem_extra = p_upd.get("extra_spins", 0)
    bot_info = await cb.bot.get_me()
    is_grp = cb.message.chat.type != "private"
    from kb import wheel_kb

    gif_tag = f"<a href='{data.AMG_GIFS['wheel']}'>&#8205;</a>"
    extra_txt = f"\n\n🎰 <i>Осталось бонусных спинов: <b>{rem_extra}</b></i>" if rem_extra > 0 else ""

    await cb.message.edit_text(
        f"{gif_tag}🎰 <b>РУЛЕТКА ОСТАНОВИЛАСЬ!</b>\n\n"
        f"Гонщик: <b>{cb.from_user.first_name}</b>\n\n"
        f"🎉 <b>ТВОЙ ВЫИГРЫШ:</b>\n"
        f"👉 <b>{prize['text']}</b>\n\n"
        f"Приз уже зачислен на твой аккаунт!{extra_txt}",
        reply_markup=wheel_kb(rem_extra, True, bot_info.username if is_grp else "")
    )
    await cb.answer("🎉 Поздравляем с выигрышем!")


@router.callback_query(F.data == "wheel:spin")
async def cb_wheel_spin(cb: CallbackQuery):
    if cb.message.chat.type == "private":
        return await cb.answer("🎰 Колесо Фортуны доступно только в командном чате! Добавь бота в группу и пиши /wheel", show_alert=True)
    uid = cb.from_user.id
    today = db.now_str()[:10]
    p = await db.get_player(uid)
    if not p:
        return await cb.answer("Сначала напиши /start!", show_alert=True)

    if p.get("last_wheel_spin") == today:
        extra = p.get("extra_spins", 0)
        bot_info = await cb.bot.get_me()
        is_grp = cb.message.chat.type != "private"
        from kb import wheel_kb
        if extra > 0:
            await cb.answer("Крутим дополнительный спин!")
            return await execute_wheel_spin(cb, is_extra=True)
        else:
            await cb.answer("⏳ Бесплатный спин уже использован!", show_alert=True)
            gif_tag = f"<a href='{data.AMG_GIFS['wheel']}'>&#8205;</a>"
            return await cb.message.edit_text(
                f"{gif_tag}⏳ <b>БЕСПЛАТНЫЙ СПИН НА СЕГОДНЯ УЖЕ ИСПОЛЬЗОВАН!</b>\n\n"
                f"Гонщик: <b>{cb.from_user.first_name}</b>\n\n"
                "Не хочешь ждать 24 часа? Забирай дополнительные спины в 1 клик через Telegram Stars ⭐️:\n\n"
                "• <b>1 спин</b> — <b>9 ⭐️</b> (+15 монет 🪙)\n"
                "• <b>3 спина</b> — <b>19 ⭐️</b> (+35 монет 🪙) [Выгода х3 🔥]\n\n"
                "Выбивай монеты, энергию и опыт прямо сейчас! 👇",
                reply_markup=wheel_kb(0, True, bot_info.username if is_grp else "")
            )

    await execute_wheel_spin(cb, is_extra=False)


@router.callback_query(F.data == "wheel:spin_extra")
async def cb_wheel_spin_extra(cb: CallbackQuery):
    if cb.message.chat.type == "private":
        return await cb.answer("🎰 Колесо Фортуны доступно только в командном чате! Добавь бота в группу и пиши /wheel", show_alert=True)
    await execute_wheel_spin(cb, is_extra=True)


# ── Ночные Похождения по Автобану (/adventure, /trip) ──────────

ADVENTURE_STATES = {}  # user_id -> scenario_idx


@router.message(Command("adventure"))
@router.message(Command("trip"))
async def cmd_adventure(message: Message):
    return await message.answer("🤝 Одиночные ночные выезды убраны — играйте командой в групповом чате: /boss, /chase, /tournament, /royale, /drag, /airdrop, /quiz, /wheel")

    uid = message.from_user.id
    today = db.now_str()[:10]
    adv_count = await db.get_cooldown(f"adv_cnt:{uid}:{today}")
    if adv_count >= 3:
        return await message.answer(
            "⏳ <b>ЛИМИТ ПОХОЖДЕНИЙ:</b> Ты уже совершил 3 ночных выезда сегодня!\n"
            "Возвращайся за новыми приключениями завтра."
        )

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
        f"🚗 Твой болид: <b>{car['name']}</b>\n"
        f"📊 Поездка: <b>{int(adv_count) + 1}/3 за сегодня</b>\n\n"
        f"📖 <i>{scenario['desc']}</i>\n\n"
        f"<b>Сделай свой выбор:</b>",
        reply_markup=adventure_choice_kb(sc_idx, scenario["choices"])
    )


@router.callback_query(F.data.startswith("adv:choice:"))
async def cb_adventure_choice(cb: CallbackQuery):
    return await cb.answer("🤝 Одиночные ночные выезды убраны — играйте командой в групповом чате: /boss, /chase, /tournament, /royale, /drag, /airdrop, /quiz, /wheel", show_alert=True)
    parts = cb.data.split(":")
    sc_idx = int(parts[2])
    ch_idx = int(parts[3])
    uid = cb.from_user.id

    p = await db.get_player(uid)
    pc = await db.get_selected_car(uid)
    if not pc or p["energy"] < 2:
        return await cb.answer("Недостаточно энергии (нужно 2 ⚡)!", show_alert=True)

    today = db.now_str()[:10]
    adv_count = await db.get_cooldown(f"adv_cnt:{uid}:{today}")
    await db.set_cooldown(f"adv_cnt:{uid}:{today}", adv_count + 1)

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
        c_win = await db.grant_coins(uid, choice["win_coins"], reason=f"Похождение: {scenario['title']}")
        await db.add_xp(uid, choice["win_xp"])
        gif_tag = f"<a href='{data.AMG_GIFS['drift']}'>&#8205;</a>"
        await cb.message.edit_text(
            f"{gif_tag}✅ <b>УСПЕХ! ВЫБОР СРАБОТАЛ ИДЕАЛЬНО!</b>\n\n"
            f"<i>{choice['success_text']}</i>\n\n"
            f"🎁 <b>Твоя добыча:</b>\n"
            f"• 🪙 +{c_win} монет AMG\n"
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
    on_cd, rem_t = await check_chat_cooldown(chat_id, "drag", DRAG_COOLDOWN)
    if on_cd:
        return await message.answer(
            f"⏳ <b>Драг-рейсинг на 402м уже проводился недавно!</b>\n\n"
            f"Следующий заезд будет доступен через: <b>{rem_t}</b>."
        )

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
    boost = await db.get_chat_boost(chat_id)
    boost_mult = 2 if boost else 1
    boost_note = f"\n🔥 <i>(Применён Буст чата x2 от спонсора {boost['sponsor_name']}!)</i>" if boost else ""

    c_drag = await db.grant_coins(uid, 15 * boost_mult, reason="Победа в Драг-рейсинге 402м")
    await db.add_xp(uid, 200 * boost_mult)

    gif_tag = f"<a href='{data.AMG_GIFS['win']}'>&#8205;</a>"
    await cb.message.edit_text(
        f"{gif_tag}🏁 <b>ФИНИШ 402 МЕТРА! ПОБЕДА!</b>\n\n"
        f"🥇 <b>{winner_name}</b> показал молниеносную реакцию: <b>{reaction} сек</b>!\n"
        f"🥈 <i>{loser_name}</i> отстал на пол-корпуса.\n\n"
        f"💰 Награда победителю: <b>+{c_drag} 🪙 монет</b> и <b>+{200 * boost_mult} XP</b>!{boost_note}\n\n"
        "Сыграть ещё: <code>/drag</code>"
    )
    DRAG_RACES.pop(chat_id, None)
    await db.set_cooldown(f"drag:{chat_id}", time.time())


# ── Буст для всей банды / Счастливые часы (/boost) ──────────

@router.message(Command("boost"))
async def cmd_boost(message: Message):
    chat_id = message.chat.id
    if message.chat.type == "private":
        return await message.answer(
            "🔥 <b>БУСТ ДЛЯ ВСЕЙ БАНДЫ (x2 НАГРАДЫ)</b>\n\n"
            "Эту команду нужно вводить в групповом чате вашей банды!\n"
            "Добавь бота в группу или напиши <code>/boost</code> там, чтобы запустить Счастливые Часы с удвоенными монетами 🪙 и опытом 📈 для всех участников."
        )

    boost = await db.get_chat_boost(chat_id)
    bot_info = await message.bot.get_me()
    url = f"https://t.me/{bot_info.username}?start=boost_{chat_id}"

    if boost:
        until_dt = datetime.strptime(boost["boost_until"], db.TS_FMT)
        rem_min = max(1, int((until_dt - datetime.utcnow()).total_seconds() // 60))
        rem_str = f"{rem_min // 60} ч. {rem_min % 60} мин." if rem_min >= 60 else f"{rem_min} мин."
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [Btn(text="🔥 Продлить буст чата x2 (29 ⭐️)", url=url)]
        ])
        await message.answer(
            f"🔥 <b>СЧАСТЛИВЫЕ ЧАСЫ В ЧАТЕ УЖЕ АКТИВНЫ!</b> 🔥\n\n"
            f"👑 <b>Почётный спонсор банды:</b> {boost['sponsor_name']}\n"
            f"⏳ <b>Осталось времени:</b> <b>{rem_str}</b>\n\n"
            f"🎁 <b>Эффект:</b> В 2 РАЗА БОЛЬШЕ монет 🪙 и опыта во всех играх чата (/boss, /drag, /tournament, /royale, /quiz)!\n\n"
            f"Хочешь продлить буст ещё на 2 часа? Жми кнопку ниже:",
            reply_markup=kb
        )
    else:
        p = await db.get_player(message.from_user.id)
        has_token = bool(p and p.get("chat_boosts_owned", 0) > 0)
        rows = []
        if has_token:
            rows.append([Btn(text="🔥 Активировать свой Буст банды", callback_data=f"boost_activate:{chat_id}")])
        rows.append([Btn(text="🚀 Запустить Буст чата x2 (29 ⭐️)", url=url)])
        kb = InlineKeyboardMarkup(inline_keyboard=rows)

        await message.answer(
            "🔥 <b>БУСТ ДЛЯ ВСЕЙ БАНДЫ / СЧАСТЛИВЫЕ ЧАСЫ (x2)</b> 🔥\n\n"
            "Сделай щедрый подгон для всех гонщиков этого чата!\n\n"
            "⭐️ <b>Что даёт буст чата:</b>\n"
            "• <b>x2 МОНЕТЫ 🪙 и x2 ОПЫТ</b> для ВСЕХ участников чата\n"
            "• Действует <b>2 часа</b> на все активности:\n"
            "  👾 Босс-рейды (/boss)\n"
            "  🏁 Дрэг 402м (/drag)\n"
            "  🏆 Гран-при турниры (/tournament)\n"
            "  👑 Королевская битва (/royale)\n"
            "  🧠 Авто-квиз (/quiz) и 📦 Аирдропы (/airdrop)\n"
            "• Бот торжественно поздравит тебя и объявит <b>Спонсором Банды</b> на весь чат! 👑\n\n"
            "Запусти Счастливые Часы всего за <b>29 ⭐️</b> 👇",
            reply_markup=kb
        )


@router.callback_query(F.data.startswith("boost_activate:"))
async def cb_boost_activate(cb: CallbackQuery):
    chat_id = int(cb.data.split(":")[1])
    uid = cb.from_user.id
    p = await db.get_player(uid)
    if not p or p.get("chat_boosts_owned", 0) <= 0:
        return await cb.answer("У тебя нет готовых жетонов буста чата!", show_alert=True)

    await db.increment(uid, chat_boosts_owned=-1)
    await db.set_chat_boost(chat_id, hours=2, sponsor_id=uid, sponsor_name=cb.from_user.first_name)
    await cb.answer("🔥 Буст банды x2 успешно запущен!", show_alert=True)
    await cb.message.answer(
        f"🎉 <b>СЧАСТЛИВЫЕ ЧАСЫ АКТИВИРОВАНЫ! БУСТ x2 НА 2 ЧАСА!</b> 🔥\n\n"
        f"👑 <b>Спонсор банды:</b> {cb.from_user.first_name} (@{cb.from_user.username or '—'})\n\n"
        f"💰 Теперь все победы и заезды в чате приносят <b>В 2 РАЗА БОЛЬШЕ МОНЕТ 🪙 И ОПЫТА!</b>\n"
        f"Газ в пол! 🏎💨"
    )



