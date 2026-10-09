"""Асинхронный слой БД (SQLite)."""
import os
import random
from datetime import datetime, timedelta

import aiosqlite

from config import DATABASE_PATH, COINS_SOFT_CAP, COINS_HARD_CAP
from data import xp_for_level, ENERGY_REGEN_MINUTES

TS_FMT = "%Y-%m-%d %H:%M:%S"

SCHEMA = """
CREATE TABLE IF NOT EXISTS players (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    level INTEGER DEFAULT 1,
    xp INTEGER DEFAULT 0,
    money INTEGER DEFAULT 50000,
    coins INTEGER DEFAULT 0,
    coins_today INTEGER DEFAULT 0,
    coins_date TEXT DEFAULT NULL,
    reputation INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    races_total INTEGER DEFAULT 0,
    pvp_wins INTEGER DEFAULT 0,
    daily_streak INTEGER DEFAULT 0,
    last_daily TEXT DEFAULT NULL,
    selected_car_id INTEGER DEFAULT NULL,
    energy INTEGER DEFAULT 10,
    max_energy INTEGER DEFAULT 10,
    last_energy_update TEXT DEFAULT NULL,
    is_admin INTEGER DEFAULT 0,
    is_banned INTEGER DEFAULT 0,
    has_insurance INTEGER DEFAULT 0,
    last_coin_duel TEXT DEFAULT NULL,
    chat_nitro_until TEXT DEFAULT NULL,
    gold_wrap INTEGER DEFAULT 0,
    defeated_opponents INTEGER DEFAULT 0,
    easy_races_today INTEGER DEFAULT 0,
    easy_races_date TEXT DEFAULT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS player_cars (

    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    car_key TEXT NOT NULL,
    engine_level INTEGER DEFAULT 0,
    turbo_level INTEGER DEFAULT 0,
    suspension_level INTEGER DEFAULT 0,
    tires_level INTEGER DEFAULT 0,
    nitro_level INTEGER DEFAULT 0,
    ecu_level INTEGER DEFAULT 0,
    body_kit_level INTEGER DEFAULT 0,
    total_races INTEGER DEFAULT 0,
    total_wins INTEGER DEFAULT 0,
    purchased_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS races (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    challenger_id INTEGER NOT NULL,
    opponent_id INTEGER DEFAULT NULL,
    challenger_car_id INTEGER NOT NULL,
    opponent_car_id INTEGER DEFAULT NULL,
    bet INTEGER DEFAULT 0,
    bet_type TEXT DEFAULT 'money',
    status TEXT DEFAULT 'pending',
    winner_id INTEGER DEFAULT NULL,
    chat_id INTEGER DEFAULT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS achievements (
    user_id INTEGER NOT NULL,
    achievement_key TEXT NOT NULL,
    unlocked_at TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (user_id, achievement_key)
);
CREATE TABLE IF NOT EXISTS coin_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    amount INTEGER NOT NULL,
    reason TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS bosses (
    chat_id INTEGER PRIMARY KEY,
    boss_name TEXT NOT NULL,
    boss_car TEXT NOT NULL,
    max_hp INTEGER NOT NULL,
    current_hp INTEGER NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS boss_damage (
    chat_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    damage INTEGER DEFAULT 0,
    PRIMARY KEY (chat_id, user_id)
);
"""

UPGRADE_COLUMNS = {"engine", "turbo", "suspension", "tires", "nitro", "ecu", "body_kit"}
PLAYER_COLUMNS = {
    "username", "first_name", "level", "xp", "money", "coins", "coins_today", "coins_date",
    "reputation", "wins", "losses", "races_total", "pvp_wins", "daily_streak", "last_daily",
    "selected_car_id", "energy", "max_energy", "last_energy_update", "is_admin", "is_banned",
    "has_insurance", "last_coin_duel", "chat_nitro_until", "gold_wrap", "defeated_opponents",
    "easy_races_today", "easy_races_date"
}


def now_str() -> str:
    return datetime.utcnow().strftime(TS_FMT)


def _connect():
    return aiosqlite.connect(DATABASE_PATH, timeout=30)


async def init_db() -> None:
    d = os.path.dirname(DATABASE_PATH)
    if d:
        os.makedirs(d, exist_ok=True)
    async with _connect() as db:
        await db.executescript(SCHEMA)
        # Миграция существующих таблиц
        for col, typ in [
            ("has_insurance", "INTEGER DEFAULT 0"),
            ("last_coin_duel", "TEXT DEFAULT NULL"),
            ("chat_nitro_until", "TEXT DEFAULT NULL"),
            ("gold_wrap", "INTEGER DEFAULT 0"),
            ("defeated_opponents", "INTEGER DEFAULT 0"),
            ("easy_races_today", "INTEGER DEFAULT 0"),
            ("easy_races_date", "TEXT DEFAULT NULL"),
        ]:
            try:
                await db.execute(f"ALTER TABLE players ADD COLUMN {col} {typ}")
            except Exception:
                pass


        try:
            await db.execute("ALTER TABLE races ADD COLUMN bet_type TEXT DEFAULT 'money'")
        except Exception:
            pass
        await db.execute("PRAGMA journal_mode=WAL")
        await db.commit()



# ── Игроки ───────────────────────────────────────────────────

async def get_player(user_id: int):
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM players WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        return dict(row) if row else None

async def get_player_by_username(username: str):
    uname = username.lstrip("@").strip().lower()
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM players WHERE LOWER(username) = ?", (uname,))
        row = await cur.fetchone()
        return dict(row) if row else None


async def create_player(user_id: int, username, first_name: str) -> dict:
    async with _connect() as db:
        await db.execute(
            "INSERT OR IGNORE INTO players (user_id, username, first_name, last_energy_update) "
            "VALUES (?, ?, ?, ?)",
            (user_id, username, first_name, now_str()),
        )
        await db.commit()
    return await get_player(user_id)


async def update_player(user_id: int, **kwargs) -> None:
    kwargs = {k: v for k, v in kwargs.items() if k in PLAYER_COLUMNS}
    if not kwargs:
        return
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    async with _connect() as db:
        await db.execute(f"UPDATE players SET {sets} WHERE user_id = ?", (*kwargs.values(), user_id))
        await db.commit()


async def increment(user_id: int, **kwargs) -> None:
    """Атомарно прибавляет значения к числовым полям."""
    kwargs = {k: v for k, v in kwargs.items() if k in PLAYER_COLUMNS}
    if not kwargs:
        return
    sets = ", ".join(f"{k} = {k} + ?" for k in kwargs)
    async with _connect() as db:
        await db.execute(f"UPDATE players SET {sets} WHERE user_id = ?", (*kwargs.values(), user_id))
        await db.commit()


async def add_money(user_id: int, amount: int) -> None:
    async with _connect() as db:
        await db.execute("UPDATE players SET money = MAX(0, money + ?) WHERE user_id = ?", (amount, user_id))
        await db.commit()


async def spend_money(user_id: int, amount: int) -> bool:
    """Списывает деньги, только если хватает. Возвращает успех."""
    async with _connect() as db:
        cur = await db.execute(
            "UPDATE players SET money = money - ? WHERE user_id = ? AND money >= ?", (amount, user_id, amount)
        )
        await db.commit()
        return cur.rowcount > 0


async def log_coin_tx(user_id: int, amount: int, reason: str):
    try:
        async with _connect() as db:
            await db.execute(
                "INSERT INTO coin_transactions (user_id, amount, reason) VALUES (?, ?, ?)",
                (user_id, amount, reason)
            )
            await db.commit()
    except Exception:
        pass


async def spend_coins(user_id: int, amount: int, reason: str = "Покупка") -> bool:
    async with _connect() as db:
        cur = await db.execute(
            "UPDATE players SET coins = coins - ? WHERE user_id = ? AND coins >= ?", (amount, user_id, amount)
        )
        await db.commit()
        ok = cur.rowcount > 0
    if ok:
        await log_coin_tx(user_id, -amount, reason)
    return ok


async def add_coins_admin(user_id: int, amount: int, reason: str = "Выдача админом") -> None:
    """Выдача монет админом — без лимитов."""
    async with _connect() as db:
        await db.execute("UPDATE players SET coins = MAX(0, coins + ?) WHERE user_id = ?", (amount, user_id))
        await db.commit()
    await log_coin_tx(user_id, amount, reason)


async def grant_coins(user_id: int, base_amount: int, reason: str = "Награда за заезд") -> int:
    """
    Начисляет монеты с СКРЫТЫМ дневным лимитом (~500/день).
    До COINS_SOFT_CAP — полная награда, затем награда плавно падает,
    после COINS_HARD_CAP — изредка 0–1 монета. Игрок видит только итоговую цифру.
    Возвращает фактически начисленное количество.
    """
    if base_amount <= 0:
        return 0
    today = datetime.utcnow().strftime("%Y-%m-%d")
    async with _connect() as db:
        cur = await db.execute("SELECT coins_today, coins_date FROM players WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        if not row:
            return 0
        earned, date = row
        if date != today:
            earned = 0

        if earned < COINS_SOFT_CAP:
            amount = min(base_amount, COINS_SOFT_CAP - earned) + max(
                0, int((base_amount - (COINS_SOFT_CAP - earned)) * 0.5)
            )
        elif earned < COINS_HARD_CAP:
            left = (COINS_HARD_CAP - earned) / (COINS_HARD_CAP - COINS_SOFT_CAP)
            amount = max(1, int(base_amount * left * random.uniform(0.3, 0.6)))
        else:
            amount = 1 if random.random() < 0.25 else 0

        await db.execute(
            "UPDATE players SET coins = coins + ?, coins_today = ?, coins_date = ? WHERE user_id = ?",
            (amount, earned + amount, today, user_id),
        )
        await db.commit()
    if amount > 0:
        await log_coin_tx(user_id, amount, reason)
    return amount



async def add_xp(user_id: int, amount: int):
    """Возвращает (новый_уровень, был_ли_апгрейд)."""
    player = await get_player(user_id)
    if not player:
        return 1, False
    xp = player["xp"] + amount
    level = player["level"]
    leveled = False
    while xp >= xp_for_level(level):
        xp -= xp_for_level(level)
        level += 1
        leveled = True
    await update_player(user_id, xp=xp, level=level)
    return level, leveled


# ── Энергия ──────────────────────────────────────────────────

async def regen_energy(user_id: int) -> int:
    p = await get_player(user_id)
    if not p:
        return 0
    energy, max_e = p["energy"], p["max_energy"]
    try:
        last = datetime.strptime(p["last_energy_update"], TS_FMT)
    except (TypeError, ValueError):
        last = datetime.utcnow()
    now = datetime.utcnow()
    if energy >= max_e:
        await update_player(user_id, last_energy_update=now_str())
        return energy
    ticks = int((now - last).total_seconds() // (ENERGY_REGEN_MINUTES * 60))
    if ticks > 0:
        energy = min(max_e, energy + ticks)
        new_last = now if energy >= max_e else last + timedelta(minutes=ticks * ENERGY_REGEN_MINUTES)
        await update_player(user_id, energy=energy, last_energy_update=new_last.strftime(TS_FMT))
    return energy


async def minutes_to_next_energy(user_id: int) -> int:
    p = await get_player(user_id)
    if not p or p["energy"] >= p["max_energy"]:
        return 0
    try:
        last = datetime.strptime(p["last_energy_update"], TS_FMT)
    except (TypeError, ValueError):
        return 0
    passed = (datetime.utcnow() - last).total_seconds() / 60
    return max(1, int(ENERGY_REGEN_MINUTES - passed % ENERGY_REGEN_MINUTES))


async def use_energy(user_id: int) -> bool:
    await regen_energy(user_id)
    async with _connect() as db:
        cur = await db.execute(
            "UPDATE players SET energy = energy - 1 WHERE user_id = ? AND energy > 0", (user_id,)
        )
        await db.commit()
        return cur.rowcount > 0


# ── Машины ───────────────────────────────────────────────────

async def get_player_cars(user_id: int) -> list:
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM player_cars WHERE user_id = ? ORDER BY id", (user_id,))
        return [dict(r) for r in await cur.fetchall()]


async def get_car(car_id: int):
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM player_cars WHERE id = ?", (car_id,))
        row = await cur.fetchone()
        return dict(row) if row else None


async def add_car(user_id: int, car_key: str) -> int:
    async with _connect() as db:
        cur = await db.execute("INSERT INTO player_cars (user_id, car_key) VALUES (?, ?)", (user_id, car_key))
        await db.commit()
        return cur.lastrowid


async def remove_car(car_id: int) -> None:
    async with _connect() as db:
        await db.execute("UPDATE players SET selected_car_id = NULL WHERE selected_car_id = ?", (car_id,))
        await db.execute("DELETE FROM player_cars WHERE id = ?", (car_id,))
        await db.commit()


async def select_car(user_id: int, car_id: int) -> None:
    await update_player(user_id, selected_car_id=car_id)


async def get_selected_car(user_id: int):
    p = await get_player(user_id)
    if not p or not p["selected_car_id"]:
        return None
    car = await get_car(p["selected_car_id"])
    if car and car["user_id"] == user_id:
        return car
    return None


async def upgrade_car(car_id: int, upgrade_type: str, new_level: int) -> None:
    if upgrade_type not in UPGRADE_COLUMNS:
        raise ValueError("bad upgrade type")
    async with _connect() as db:
        await db.execute(f"UPDATE player_cars SET {upgrade_type}_level = ? WHERE id = ?", (new_level, car_id))
        await db.commit()


async def car_race_result(car_id: int, won: bool) -> None:
    async with _connect() as db:
        await db.execute(
            "UPDATE player_cars SET total_races = total_races + 1, total_wins = total_wins + ? WHERE id = ?",
            (1 if won else 0, car_id),
        )
        await db.commit()


async def player_has_car_key(user_id: int, car_key: str) -> bool:
    async with _connect() as db:
        cur = await db.execute("SELECT 1 FROM player_cars WHERE user_id = ? AND car_key = ? LIMIT 1", (user_id, car_key))
        return await cur.fetchone() is not None


async def count_cars(user_id: int) -> int:
    async with _connect() as db:
        cur = await db.execute("SELECT COUNT(*) FROM player_cars WHERE user_id = ?", (user_id,))
        return (await cur.fetchone())[0]


# ── Гонки PvP ────────────────────────────────────────────────

async def create_race(challenger_id: int, car_id: int, bet: int, chat_id: int) -> int:
    async with _connect() as db:
        cur = await db.execute(
            "INSERT INTO races (challenger_id, challenger_car_id, bet, chat_id) VALUES (?, ?, ?, ?)",
            (challenger_id, car_id, bet, chat_id),
        )
        await db.commit()
        return cur.lastrowid


async def lock_race(race_id: int, opponent_id: int, opponent_car_id: int) -> bool:
    """Атомарно забирает вызов (защита от двойного принятия)."""
    async with _connect() as db:
        cur = await db.execute(
            "UPDATE races SET opponent_id = ?, opponent_car_id = ?, status = 'active' "
            "WHERE id = ? AND status = 'pending'",
            (opponent_id, opponent_car_id, race_id),
        )
        await db.commit()
        return cur.rowcount > 0


async def finish_race(race_id: int, winner_id: int) -> None:
    async with _connect() as db:
        await db.execute("UPDATE races SET winner_id = ?, status = 'finished' WHERE id = ?", (winner_id, race_id))
        await db.commit()


async def cancel_race(race_id: int) -> bool:
    async with _connect() as db:
        cur = await db.execute("UPDATE races SET status = 'cancelled' WHERE id = ? AND status = 'pending'", (race_id,))
        await db.commit()
        return cur.rowcount > 0


async def get_race(race_id: int):
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM races WHERE id = ?", (race_id,))
        row = await cur.fetchone()
        return dict(row) if row else None


async def get_pending_races(exclude_user: int, limit: int = 10) -> list:
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT r.*, p.first_name AS challenger_name FROM races r "
            "JOIN players p ON p.user_id = r.challenger_id "
            "WHERE r.status = 'pending' AND r.challenger_id != ? ORDER BY r.id DESC LIMIT ?",
            (exclude_user, limit),
        )
        return [dict(r) for r in await cur.fetchall()]


async def count_user_pending(user_id: int) -> int:
    async with _connect() as db:
        cur = await db.execute("SELECT COUNT(*) FROM races WHERE challenger_id = ? AND status = 'pending'", (user_id,))
        return (await cur.fetchone())[0]


# ── Достижения / топ ─────────────────────────────────────────

async def add_achievement(user_id: int, key: str) -> bool:
    async with _connect() as db:
        cur = await db.execute(
            "INSERT OR IGNORE INTO achievements (user_id, achievement_key) VALUES (?, ?)", (user_id, key)
        )
        await db.commit()
        return cur.rowcount > 0


async def get_achievements(user_id: int) -> list:
    async with _connect() as db:
        cur = await db.execute("SELECT achievement_key FROM achievements WHERE user_id = ?", (user_id,))
        return [r[0] for r in await cur.fetchall()]


async def get_top_players(sort_by: str = "wins", limit: int = 10) -> list:
    if sort_by not in {"wins", "money", "level", "reputation", "coins"}:
        sort_by = "wins"
    order = "level DESC, xp DESC" if sort_by == "level" else f"{sort_by} DESC"
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(f"SELECT * FROM players WHERE is_banned = 0 ORDER BY {order} LIMIT ?", (limit,))
        return [dict(r) for r in await cur.fetchall()]


async def get_all_players() -> list:
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM players ORDER BY level DESC, wins DESC")
        return [dict(r) for r in await cur.fetchall()]


async def get_admin_ids() -> list:
    async with _connect() as db:
        cur = await db.execute("SELECT user_id FROM players WHERE is_admin = 1")
        return [r[0] for r in await cur.fetchall()]


async def server_stats() -> dict:
    today = datetime.utcnow().strftime("%Y-%m-%d")
    async with _connect() as db:
        async def one(q, *a):
            c = await db.execute(q, a)
            return (await c.fetchone())[0] or 0
        return {
            "players": await one("SELECT COUNT(*) FROM players"),
            "active_today": await one("SELECT COUNT(*) FROM players WHERE coins_date = ? OR last_daily = ?", today, today),
            "banned": await one("SELECT COUNT(*) FROM players WHERE is_banned = 1"),
            "races": await one("SELECT SUM(races_total) FROM players"),
            "money": await one("SELECT SUM(money) FROM players"),
            "coins": await one("SELECT SUM(coins) FROM players"),
            "coins_today": await one("SELECT SUM(coins_today) FROM players WHERE coins_date = ?", today),
            "cars": await one("SELECT COUNT(*) FROM player_cars"),
            "avg_level": await one("SELECT AVG(level) FROM players"),
            "pvp": await one("SELECT COUNT(*) FROM races WHERE status = 'finished'"),
        }


# ── Логи монет и Боссы ───────────────────────────────────────

async def get_recent_coin_txs(limit: int = 15) -> list:
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT t.*, p.first_name, p.username FROM coin_transactions t "
            "LEFT JOIN players p ON p.user_id = t.user_id ORDER BY t.id DESC LIMIT ?",
            (limit,)
        )
        return [dict(r) for r in await cur.fetchall()]


async def get_coin_flow_stats() -> dict:
    today = datetime.utcnow().strftime("%Y-%m-%d")
    async with _connect() as db:
        async def val(q, *a):
            c = await db.execute(q, a)
            return (await c.fetchone())[0] or 0
        in_today = await val("SELECT SUM(amount) FROM coin_transactions WHERE amount > 0 AND created_at >= ?", today)
        out_today = await val("SELECT SUM(-amount) FROM coin_transactions WHERE amount < 0 AND created_at >= ?", today)
        in_all = await val("SELECT SUM(amount) FROM coin_transactions WHERE amount > 0")
        out_all = await val("SELECT SUM(-amount) FROM coin_transactions WHERE amount < 0")
        return {
            "in_today": in_today,
            "out_today": out_today,
            "in_all": in_all,
            "out_all": out_all
        }


async def get_active_boss(chat_id: int) -> dict | None:
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM bosses WHERE chat_id = ? AND current_hp > 0", (chat_id,))
        row = await cur.fetchone()
        return dict(row) if row else None


async def create_boss(chat_id: int, boss_name: str, boss_car: str, max_hp: int) -> dict:
    async with _connect() as db:
        await db.execute("DELETE FROM bosses WHERE chat_id = ?", (chat_id,))
        await db.execute("DELETE FROM boss_damage WHERE chat_id = ?", (chat_id,))
        await db.execute(
            "INSERT INTO bosses (chat_id, boss_name, boss_car, max_hp, current_hp) VALUES (?, ?, ?, ?, ?)",
            (chat_id, boss_name, boss_car, max_hp, max_hp)
        )
        await db.commit()
    return await get_active_boss(chat_id)


async def damage_boss(chat_id: int, user_id: int, dmg: int) -> tuple[int, bool]:
    """Наносит урон боссу. Возвращает (остаток_hp, повержен_ли)."""
    async with _connect() as db:
        cur = await db.execute("SELECT current_hp FROM bosses WHERE chat_id = ?", (chat_id,))
        row = await cur.fetchone()
        if not row:
            return 0, False
        cur_hp = max(0, row[0] - dmg)
        await db.execute("UPDATE bosses SET current_hp = ? WHERE chat_id = ?", (cur_hp, chat_id))
        await db.execute(
            "INSERT INTO boss_damage (chat_id, user_id, damage) VALUES (?, ?, ?) "
            "ON CONFLICT(chat_id, user_id) DO UPDATE SET damage = damage + ?",
            (chat_id, user_id, dmg, dmg)
        )
        await db.commit()
        return cur_hp, cur_hp == 0


async def get_boss_damagers(chat_id: int) -> list:
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT d.damage, p.user_id, p.first_name FROM boss_damage d "
            "JOIN players p ON p.user_id = d.user_id WHERE d.chat_id = ? ORDER BY d.damage DESC",
            (chat_id,)
        )
        return [dict(r) for r in await cur.fetchall()]


async def delete_boss(chat_id: int):
    async with _connect() as db:
        await db.execute("DELETE FROM bosses WHERE chat_id = ?", (chat_id,))
        await db.execute("DELETE FROM boss_damage WHERE chat_id = ?", (chat_id,))
        await db.commit()


