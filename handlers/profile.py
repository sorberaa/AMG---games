from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

import db
from data import ACHIEVEMENTS_DEF, CAR_CATALOG, fmt, xp_for_level
from engine import get_daily_reward
from kb import back_kb, daily_kb, profile_kb, top_kb
from utils import award_achievements, safe_edit, send_menu

router = Router(name="profile")


async def profile_text(uid: int) -> str:
    await db.regen_energy(uid)
    p = await db.get_player(uid)
    cars = await db.get_player_cars(uid)
    ach = await db.get_achievements(uid)
    pc = await db.get_selected_car(uid)
    wr = round(p["wins"] / p["races_total"] * 100) if p["races_total"] else 0
    need = xp_for_level(p["level"])
    bar_len = int(p["xp"] / need * 10) if need else 0
    bar = "▰" * bar_len + "▱" * (10 - bar_len)
    return (
        f"👤 <b>{p['first_name']}</b>\n\n"
        f"📊 Уровень <b>{p['level']}</b>\n{bar} {p['xp']}/{need} XP\n\n"
        f"💰 Деньги: <b>${fmt(p['money'])}</b>\n"
        f"🪙 Монеты: <b>{fmt(p['coins'])}</b>\n"
        f"⚡ Энергия: {p['energy']}/{p['max_energy']}\n"
        f"⭐ Репутация: {p['reputation']}\n\n"
        f"🏁 Гонок: {p['races_total']} · 🏆 {p['wins']} · 💀 {p['losses']}\n"
        f"📈 Винрейт: {wr}% · ⚔️ PvP-побед: {p['pvp_wins']}\n"
        f"🚗 Машин: {len(cars)} · Основная: {CAR_CATALOG[pc['car_key']]['name'] if pc else '—'}\n"
        f"🔥 Стрик: {p['daily_streak']} дн. · 🏅 Достижений: {len(ach)}/{len(ACHIEVEMENTS_DEF)}"
    )


@router.message(Command("profile"))
async def cmd_profile(message: Message):
    await send_menu(message, message.from_user.id, await profile_text(message.from_user.id), profile_kb())


@router.callback_query(F.data == "profile")
async def cb_profile(cb: CallbackQuery):
    await cb.answer()
    await safe_edit(cb, await profile_text(cb.from_user.id), profile_kb())


@router.callback_query(F.data == "profile_ach")
async def cb_ach(cb: CallbackQuery):
    await cb.answer()
    have = set(await db.get_achievements(cb.from_user.id))
    lines = [f"{'✅' if k in have else '🔒'} {a['emoji']} <b>{a['name']}</b> — <i>{a['description']}</i>"
             for k, a in ACHIEVEMENTS_DEF.items()]
    await safe_edit(cb, f"🏅 <b>Достижения</b> ({len(have)}/{len(ACHIEVEMENTS_DEF)})\n\n" + "\n".join(lines),
                    back_kb("profile"))


# ── Топ ──────────────────────────────────────────────────────

TOP_LABELS = {"wins": ("🏆", "побед"), "money": ("💰", "$"), "level": ("📈", "ур."),
              "reputation": ("⭐", "реп."), "coins": ("🪙", "монет")}


async def top_text(sort: str) -> str:
    players = await db.get_top_players(sort)
    emoji, label = TOP_LABELS.get(sort, TOP_LABELS["wins"])
    medals = ["🥇", "🥈", "🥉"]
    lines = []
    for i, p in enumerate(players):
        pos = medals[i] if i < 3 else f"{i + 1}."
        lines.append(f"{pos} {p['first_name']} — <b>{fmt(p[sort])}</b> {label}")
    return f"{emoji} <b>Топ гонщиков</b>\n\n" + ("\n".join(lines) or "Пока пусто")


@router.message(Command("top"))
async def cmd_top(message: Message):
    await send_menu(message, message.from_user.id, await top_text("wins"), top_kb("wins"))


@router.callback_query(F.data.startswith("top"))
async def cb_top(cb: CallbackQuery):
    await cb.answer()
    sort = cb.data.split(":")[1] if ":" in cb.data else "wins"
    if sort not in TOP_LABELS:
        sort = "wins"
    await safe_edit(cb, await top_text(sort), top_kb(sort))


# ── Бонус дня ────────────────────────────────────────────────

def _today() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d")


def _yesterday() -> str:
    return (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")


def _next_streak(p: dict) -> int:
    return p["daily_streak"] + 1 if p["last_daily"] == _yesterday() else 1


async def daily_view(uid: int):
    p = await db.get_player(uid)
    if p["last_daily"] == _today():
        now = datetime.utcnow()
        left = (datetime(now.year, now.month, now.day) + timedelta(days=1)) - now
        h, m = left.seconds // 3600, left.seconds % 3600 // 60
        return (f"🎁 <b>Бонус дня</b>\n\n✅ Сегодня уже получено!\n🔥 Стрик: {p['daily_streak']} дн.\n"
                f"⏳ Следующий через {h} ч {m} мин"), back_kb()
    streak = _next_streak(p)
    r = get_daily_reward(streak)
    days = []
    for d in range(1, 8):
        cur = (streak - 1) % 7 + 1
        days.append("🟩" if d < cur else "🎁" if d == cur else "⬜")
    bonus = f"\n{r['bonus']}" if r["bonus"] else ""
    return (f"🎁 <b>Бонус дня</b>\n\n{''.join(days)}\nДень {(streak - 1) % 7 + 1} из 7 · стрик {streak}\n\n"
            f"💰 ${fmt(r['money'])}\n📈 {r['xp']} XP\n🪙 ~{r['coins']} монет{bonus}\n\n"
            "<i>Не пропускай дни — награда растёт!</i>"), daily_kb()


@router.message(Command("daily"))
async def cmd_daily(message: Message):
    text, kb = await daily_view(message.from_user.id)
    await send_menu(message, message.from_user.id, text, kb)


@router.callback_query(F.data == "daily")
async def cb_daily(cb: CallbackQuery):
    await cb.answer()
    text, kb = await daily_view(cb.from_user.id)
    await safe_edit(cb, text, kb)


@router.callback_query(F.data == "daily_claim")
async def cb_daily_claim(cb: CallbackQuery):
    uid = cb.from_user.id
    p = await db.get_player(uid)
    if p["last_daily"] == _today():
        return await cb.answer("Ты уже забрал награду сегодня!", show_alert=True)
    streak = _next_streak(p)
    await db.update_player(uid, last_daily=_today(), daily_streak=streak)
    r = get_daily_reward(streak)
    await db.add_money(uid, r["money"])
    lvl, up = await db.add_xp(uid, r["xp"])
    coins = await db.grant_coins(uid, r["coins"])
    extra = []
    if r["energy"]:
        await db.regen_energy(uid)
        await db.increment(uid, energy=r["energy"])
        extra.append(f"⚡ +{r['energy']} энергии")
    if r["bonus"] and "кейс" in r["bonus"]:
        from handlers.shop import roll_case
        _, kind, value = roll_case("case_basic")
        if kind == "money":
            await db.add_money(uid, value)
            extra.append(f"📦 Кейс: ${fmt(value)}")
        elif kind == "xp":
            await db.add_xp(uid, value)
            extra.append(f"📦 Кейс: {value} XP")
        else:
            await db.add_car(uid, value)
            extra.append(f"📦 Кейс: {CAR_CATALOG[value]['name']}!")
    await cb.answer("🎁 Награда получена!")
    ach = await award_achievements(uid)
    lines = [f"💰 +${fmt(r['money'])}", f"📈 +{r['xp']} XP"]
    if coins:
        lines.append(f"🪙 +{coins}")
    lines += extra
    lvl_t = f"\n🆙 <b>Новый уровень: {lvl}!</b>" if up else ""
    await safe_edit(cb, f"🎁 <b>Бонус дня получен!</b>\n🔥 Стрик: {streak} дн.\n\n" + "\n".join(lines) + lvl_t + ach,
                    back_kb())

