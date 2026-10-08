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
