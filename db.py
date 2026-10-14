"""Асинхронный слой БД (SQLite + PostgreSQL)."""
import os
import re
import json
import logging
import random
from datetime import datetime, timedelta

import aiosqlite
try:
    import asyncpg
except ImportError:
    asyncpg = None

from config import DATABASE_PATH, DATABASE_URL, COINS_SOFT_CAP, COINS_HARD_CAP, COINS_MAX_DAY
from data import xp_for_level, ENERGY_REGEN_MINUTES


logger = logging.getLogger("amg.db")
TS_FMT = "%Y-%m-%d %H:%M:%S"
BACKUP_PATH = "data/backup_amg_game.json"

_pg_pool = None
_is_pg = False


def is_postgres() -> bool:
    return _is_pg and _pg_pool is not None


SCHEMA = """
CREATE TABLE IF NOT EXISTS players (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    level INTEGER DEFAULT 1,
    xp INTEGER DEFAULT 0,
    money INTEGER DEFAULT 500,
    coins INTEGER DEFAULT 500,
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
    salt_boost_until TEXT DEFAULT NULL,
    last_salt_boost_date TEXT DEFAULT NULL,
    gold_wrap INTEGER DEFAULT 0,
    defeated_opponents INTEGER DEFAULT 0,
    easy_races_today INTEGER DEFAULT 0,
    easy_races_date TEXT DEFAULT NULL,
    last_wheel_spin TEXT DEFAULT NULL,
    last_adventure TEXT DEFAULT NULL,
    vip_until TEXT DEFAULT NULL,
    nitro_boost_until TEXT DEFAULT NULL,
    stars_spent INTEGER DEFAULT 0,
    custom_plates INTEGER DEFAULT 0,
    extra_spins INTEGER DEFAULT 0,
    chat_boosts_owned INTEGER DEFAULT 0,
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
    exhaust_level INTEGER DEFAULT 0,
    transmission_level INTEGER DEFAULT 0,
    brakes_level INTEGER DEFAULT 0,
    intercooler_level INTEGER DEFAULT 0,
    intake_level INTEGER DEFAULT 0,
    downpipe_level INTEGER DEFAULT 0,
    total_races INTEGER DEFAULT 0,
    total_wins INTEGER DEFAULT 0,
    color TEXT DEFAULT NULL,
    plate TEXT DEFAULT NULL,
    purchased_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS races (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    challenger_id INTEGER NOT NULL,
    opponent_id INTEGER DEFAULT NULL,
    challenger_car_id INTEGER NOT NULL,
    opponent_car_id INTEGER DEFAULT NULL,
    bet INTEGER DEFAULT 0,
    bet_type TEXT DEFAULT 'coins',
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
    rage_phase INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS boss_damage (
    chat_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    damage INTEGER DEFAULT 0,
    PRIMARY KEY (chat_id, user_id)
);
CREATE TABLE IF NOT EXISTS withdrawals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    amount INTEGER NOT NULL,
    wallet_info TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS game_cooldowns (
    target_key TEXT PRIMARY KEY,
    last_ts REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS stars_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    pack_key TEXT NOT NULL,
    stars_amount INTEGER NOT NULL,
    telegram_charge_id TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS chat_boosts (
    chat_id INTEGER PRIMARY KEY,
    boost_until TEXT NOT NULL,
    sponsor_id INTEGER NOT NULL,
    sponsor_name TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);
"""


PG_SCHEMA = """
CREATE TABLE IF NOT EXISTS players (
    user_id BIGINT PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    level INTEGER DEFAULT 1,
    xp INTEGER DEFAULT 0,
    money INTEGER DEFAULT 500,
    coins INTEGER DEFAULT 500,
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
    salt_boost_until TEXT DEFAULT NULL,
    last_salt_boost_date TEXT DEFAULT NULL,
    gold_wrap INTEGER DEFAULT 0,
    defeated_opponents INTEGER DEFAULT 0,
    easy_races_today INTEGER DEFAULT 0,
    easy_races_date TEXT DEFAULT NULL,
    last_wheel_spin TEXT DEFAULT NULL,
    last_adventure TEXT DEFAULT NULL,
    vip_until TEXT DEFAULT NULL,
    nitro_boost_until TEXT DEFAULT NULL,
    stars_spent INTEGER DEFAULT 0,
    custom_plates INTEGER DEFAULT 0,
    extra_spins INTEGER DEFAULT 0,
    chat_boosts_owned INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS player_cars (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    car_key TEXT NOT NULL,
    engine_level INTEGER DEFAULT 0,
    turbo_level INTEGER DEFAULT 0,
    suspension_level INTEGER DEFAULT 0,
    tires_level INTEGER DEFAULT 0,
    nitro_level INTEGER DEFAULT 0,
    ecu_level INTEGER DEFAULT 0,
    body_kit_level INTEGER DEFAULT 0,
    exhaust_level INTEGER DEFAULT 0,
    transmission_level INTEGER DEFAULT 0,
    brakes_level INTEGER DEFAULT 0,
    intercooler_level INTEGER DEFAULT 0,
    intake_level INTEGER DEFAULT 0,
    downpipe_level INTEGER DEFAULT 0,
    total_races INTEGER DEFAULT 0,
    total_wins INTEGER DEFAULT 0,
    color TEXT DEFAULT NULL,
    plate TEXT DEFAULT NULL,
    purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS races (
    id SERIAL PRIMARY KEY,
    challenger_id BIGINT NOT NULL,
    opponent_id BIGINT DEFAULT NULL,
    challenger_car_id INTEGER NOT NULL,
    opponent_car_id INTEGER DEFAULT NULL,
    bet INTEGER DEFAULT 0,
    bet_type TEXT DEFAULT 'coins',
    status TEXT DEFAULT 'pending',
    winner_id BIGINT DEFAULT NULL,
    chat_id BIGINT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS achievements (
    user_id BIGINT NOT NULL,
    achievement_key TEXT NOT NULL,
    unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, achievement_key)
);

CREATE TABLE IF NOT EXISTS coin_transactions (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    amount INTEGER NOT NULL,
    reason TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bosses (
    chat_id BIGINT PRIMARY KEY,
    boss_name TEXT NOT NULL,
    boss_car TEXT NOT NULL,
    max_hp INTEGER NOT NULL,
    current_hp INTEGER NOT NULL,
    rage_phase INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS boss_damage (
    chat_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    damage INTEGER DEFAULT 0,
    PRIMARY KEY (chat_id, user_id)
);

CREATE TABLE IF NOT EXISTS withdrawals (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    amount INTEGER NOT NULL,
    wallet_info TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS game_cooldowns (
    target_key TEXT PRIMARY KEY,
    last_ts REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS stars_transactions (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    pack_key TEXT NOT NULL,
    stars_amount INTEGER NOT NULL,
    telegram_charge_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chat_boosts (
    chat_id BIGINT PRIMARY KEY,
    boost_until TEXT NOT NULL,
    sponsor_id BIGINT NOT NULL,
    sponsor_name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

UPGRADE_COLUMNS = {
    "engine", "turbo", "exhaust", "transmission", "suspension",
    "brakes", "tires", "intercooler", "intake", "downpipe", "nitro", "ecu", "body_kit"
}
PLAYER_COLUMNS = {
    "username", "first_name", "level", "xp", "money", "coins", "coins_today", "coins_date",
    "reputation", "wins", "losses", "races_total", "pvp_wins", "daily_streak", "last_daily",
    "selected_car_id", "energy", "max_energy", "last_energy_update", "is_admin", "is_banned",
    "has_insurance", "last_coin_duel", "chat_nitro_until", "salt_boost_until", "last_salt_boost_date", "gold_wrap", "defeated_opponents",
    "easy_races_today", "easy_races_date", "last_wheel_spin", "last_adventure", "vip_until", "nitro_boost_until", "stars_spent",
    "custom_plates", "extra_spins", "chat_boosts_owned"
}



def now_str() -> str:
    return datetime.utcnow().strftime(TS_FMT)


def to_pg_query(sql: str) -> str:
    # 1. Replace INSERT OR IGNORE INTO
    sql = re.sub(r'INSERT\s+OR\s+IGNORE\s+INTO\s+([a-zA-Z0-9_]+)', r'INSERT INTO \1', sql, flags=re.IGNORECASE)
    if 'ON CONFLICT' not in sql.upper() and re.search(r'INSERT\s+INTO\s+(players|achievements)\b', sql, re.IGNORECASE):
        sql += ' ON CONFLICT DO NOTHING'
        
    # 2. Fix multi-arg scalar MAX(a, b) and MIN(a, b) -> GREATEST / LEAST
    sql = re.sub(r'\bMAX\s*\(\s*([^,()]+)\s*,\s*([^)]+)\)', r'GREATEST(\1, \2)', sql, flags=re.IGNORECASE)
    sql = re.sub(r'\bMIN\s*\(\s*([^,()]+)\s*,\s*([^)]+)\)', r'LEAST(\1, \2)', sql, flags=re.IGNORECASE)
    
    # 3. Replace ? placeholders with $1, $2, ...
    parts = sql.split('?')
    if len(parts) > 1:
        res = []
        for i, part in enumerate(parts[:-1]):
            res.append(part)
            res.append(f"${i+1}")
        res.append(parts[-1])
        sql = "".join(res)
        
    # 4. Handle auto-id return
    if re.search(r'INSERT\s+INTO\s+(player_cars|races|withdrawals|coin_transactions)\b', sql, re.IGNORECASE):
        if 'RETURNING' not in sql.upper():
            sql += ' RETURNING id'
            
    return sql


class PGCursorWrapper:
    def __init__(self, rows: list, rowcount: int = 0, lastrowid: int | None = None):
        self._rows = rows
        self._idx = 0
        self.rowcount = rowcount
        self.lastrowid = lastrowid

    async def fetchone(self):
        if self._idx < len(self._rows):
            r = self._rows[self._idx]
            self._idx += 1
            return r
        return None

    async def fetchall(self):
        r = self._rows[self._idx:]
        self._idx = len(self._rows)
        return r


class PGConnWrapper:
    def __init__(self, conn):
        self.conn = conn
        self.row_factory = None

    async def execute(self, sql: str, params: tuple | list = ()):
        if isinstance(params, (tuple, list)):
            p_list = list(params)
        else:
            p_list = [params] if params is not None else []

        pg_sql = to_pg_query(sql)

        if "RETURNING ID" in pg_sql.upper():
            rows = await self.conn.fetch(pg_sql, *p_list)
            lastrowid = rows[0]["id"] if rows else None
            return PGCursorWrapper(rows, len(rows), lastrowid)

        stripped = pg_sql.strip().upper()
        if stripped.startswith("SELECT") or stripped.startswith("WITH"):
            rows = await self.conn.fetch(pg_sql, *p_list)
            return PGCursorWrapper(rows, len(rows))

        status = await self.conn.execute(pg_sql, *p_list)
        rowcount = 0
        if status:
            parts = status.split()
            if parts and parts[-1].isdigit():
                rowcount = int(parts[-1])
        return PGCursorWrapper([], rowcount)

    async def executescript(self, script: str):
        await self.conn.execute(script)

    async def commit(self):
        pass


class PGConnContext:
    def __init__(self, pool):
        self.pool = pool
        self.conn = None
        self.tx = None

    async def __aenter__(self):
        self.conn = await self.pool.acquire()
        self.tx = self.conn.transaction()
        await self.tx.start()
        return PGConnWrapper(self.conn)

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type is not None:
                await self.tx.rollback()
            else:
                await self.tx.commit()
        except Exception:
            pass
        finally:
            await self.pool.release(self.conn)


def _connect():
    if _is_pg and _pg_pool is not None:
        return PGConnContext(_pg_pool)
    return aiosqlite.connect(DATABASE_PATH, timeout=30)


async def backup_sqlite_to_json():
    """Сохраняет полный снимок базы в JSON-файл для восстановления при перезапусках."""
    try:
        if is_postgres():
            return
        if not os.path.exists(DATABASE_PATH):
            return
        async with aiosqlite.connect(DATABASE_PATH) as s_db:
            s_db.row_factory = aiosqlite.Row
            data = {}
            for table in ["players", "player_cars", "races", "achievements", "game_cooldowns", "bosses", "withdrawals", "chat_boosts"]:
                try:
                    cur = await s_db.execute(f"SELECT * FROM {table}")
                    rows = [dict(r) for r in await cur.fetchall()]
                    data[table] = rows
                except Exception:
                    pass
            d = os.path.dirname(BACKUP_PATH)
            if d:
                os.makedirs(d, exist_ok=True)
            with open(BACKUP_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"Failed to backup SQLite to JSON: {e}")


async def restore_sqlite_from_json():
    """Восстанавливает базу данных из JSON, если SQLite пуст или был стёрт."""
    try:
        if is_postgres():
            return
        if not os.path.exists(BACKUP_PATH):
            return
        async with aiosqlite.connect(DATABASE_PATH) as s_db:
            cur = await s_db.execute("SELECT COUNT(*) FROM players")
            row = await cur.fetchone()
            if row and row[0] > 0:
                return  # База уже не пуста
            
            with open(BACKUP_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            players = data.get("players", [])
            if not players:
                return
            logger.info(f"Обнаружен резервный бэкап! Восстанавливаем {len(players)} игроков...")
            for p in players:
                cols = [col for col, val in p.items() if val is not None]
                placeholders = ["?"] * len(cols)
                vals = [p[col] for col in cols]
                q = f"INSERT OR IGNORE INTO players ({', '.join(cols)}) VALUES ({', '.join(placeholders)})"
                await s_db.execute(q, vals)

            for car in data.get("player_cars", []):
                cols = [col for col, val in car.items() if val is not None]
                placeholders = ["?"] * len(cols)
                vals = [car[col] for col in cols]
                q = f"INSERT OR IGNORE INTO player_cars ({', '.join(cols)}) VALUES ({', '.join(placeholders)})"
                await s_db.execute(q, vals)

            for a in data.get("achievements", []):
                await s_db.execute("INSERT OR IGNORE INTO achievements (user_id, achievement_key) VALUES (?, ?)",
                                   (a["user_id"], a["achievement_key"]))
                
            for cd in data.get("game_cooldowns", []):
                await s_db.execute("INSERT OR REPLACE INTO game_cooldowns (target_key, last_ts) VALUES (?, ?)",
                                   (cd["target_key"], cd["last_ts"]))
            await s_db.commit()
            logger.info("Успешно восстановлено из резервного бэкапа!")
    except Exception as e:
        logger.warning(f"Failed to restore from backup JSON: {e}")


async def migrate_sqlite_to_pg(sqlite_path: str):
    if not os.path.exists(sqlite_path) or _pg_pool is None:
        return
    logger.info(f"Проверка данных SQLite в {sqlite_path} для переноса в PostgreSQL...")
    try:
        async with aiosqlite.connect(sqlite_path) as sdb:
            sdb.row_factory = aiosqlite.Row
            cur = await sdb.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='players'")
            if not await cur.fetchone():
                return
            cur = await sdb.execute("SELECT * FROM players")
            players = [dict(r) for r in await cur.fetchall()]
            if not players:
                return
            logger.info(f"Найдено {len(players)} игроков в SQLite! Переносим в PostgreSQL...")
            async with _pg_pool.acquire() as conn:
                for p in players:
                    cols = [k for k in p.keys() if p[k] is not None]
                    placeholders = [f"${i+1}" for i in range(len(cols))]
                    vals = [p[c] for c in cols]
                    q = f"INSERT INTO players ({', '.join(cols)}) VALUES ({', '.join(placeholders)}) ON CONFLICT (user_id) DO NOTHING"
                    await conn.execute(q, *vals)

                cur = await sdb.execute("SELECT * FROM player_cars")
                cars = [dict(r) for r in await cur.fetchall()]
                for c in cars:
                    cols = [k for k in c.keys() if c[k] is not None and k != 'id']
                    placeholders = [f"${i+1}" for i in range(len(cols))]
                    vals = [c[k] for c in cols]
                    q = f"INSERT INTO player_cars ({', '.join(cols)}) VALUES ({', '.join(placeholders)})"
                    await conn.execute(q, *vals)

                cur = await sdb.execute("SELECT * FROM achievements")
                achs = [dict(r) for r in await cur.fetchall()]
                for a in achs:
                    await conn.execute(
                        "INSERT INTO achievements (user_id, achievement_key) VALUES ($1, $2) ON CONFLICT DO NOTHING",
                        a["user_id"], a["achievement_key"]
                    )

                cur = await sdb.execute("SELECT * FROM game_cooldowns")
                cds = [dict(r) for r in await cur.fetchall()]
                for cd in cds:
                    await conn.execute(
                        "INSERT INTO game_cooldowns (target_key, last_ts) VALUES ($1, $2) ON CONFLICT (target_key) DO UPDATE SET last_ts = excluded.last_ts",
                        cd["target_key"], cd["last_ts"]
                    )
            logger.info("Миграция существующих данных в PostgreSQL успешно завершена!")
    except Exception as e:
        logger.warning(f"Ошибка миграции SQLite -> PostgreSQL: {e}")


async def get_db_status() -> dict:
    if is_postgres():
        async with _connect() as s_db:
            cur = await s_db.execute("SELECT COUNT(*) FROM players")
            p_cnt = (await cur.fetchone())[0]
            cur = await s_db.execute("SELECT COUNT(*) FROM player_cars")
            c_cnt = (await cur.fetchone())[0]
        return {
            "engine": "PostgreSQL 🐘",
            "persistent": True,
            "status_text": "Постоянная облачная база данных (данные защищены от перезапусков и обновлений)",
            "players": p_cnt,
            "cars": c_cnt,
        }
    else:
        async with _connect() as s_db:
            cur = await s_db.execute("SELECT COUNT(*) FROM players")
            p_cnt = (await cur.fetchone())[0]
            cur = await s_db.execute("SELECT COUNT(*) FROM player_cars")
            c_cnt = (await cur.fetchone())[0]
        return {
            "engine": "SQLite 📁",
            "persistent": False,
            "path": DATABASE_PATH,
            "status_text": "Локальный SQLite файл (подключите PostgreSQL в render.yaml/DATABASE_URL для 100% сохранности)",
            "players": p_cnt,
            "cars": c_cnt,
        }


async def init_db() -> None:
    global _pg_pool, _is_pg

    if DATABASE_URL and asyncpg:
        try:
            logger.info("Подключение к PostgreSQL базе данных...")
            try:
                _pg_pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10, timeout=30)
            except Exception as ssl_err:
                logger.info(f"Прямое подключение требует SSL ({ssl_err}), повтор с ssl='require'...")
                _pg_pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10, timeout=30, ssl="require")

            _is_pg = True
            logger.info("✅ Успешно подключено к PostgreSQL! Все данные игроков сохраняются надежно.")

            async with _pg_pool.acquire() as conn:
                await conn.execute(PG_SCHEMA)
                for col, typ in [
                    ("vip_until", "TEXT DEFAULT NULL"),
                    ("nitro_boost_until", "TEXT DEFAULT NULL"),
                    ("stars_spent", "INTEGER DEFAULT 0"),
                    ("custom_plates", "INTEGER DEFAULT 0"),
                    ("extra_spins", "INTEGER DEFAULT 0"),
                    ("chat_boosts_owned", "INTEGER DEFAULT 0"),
                ]:
                    try:
                        await conn.execute(f"ALTER TABLE players ADD COLUMN IF NOT EXISTS {col} {typ}")
                    except Exception:
                        pass
                try:
                    await conn.execute("ALTER TABLE player_cars ADD COLUMN IF NOT EXISTS plate TEXT DEFAULT NULL")
                except Exception:
                    pass

                # Миграция типов столбцов на BIGINT для поддержки 64-битных Telegram ID (группы и новые юзеры)
                for alter_sql in [
                    "ALTER TABLE bosses ALTER COLUMN chat_id TYPE BIGINT",
                    "ALTER TABLE boss_damage ALTER COLUMN chat_id TYPE BIGINT",
                    "ALTER TABLE boss_damage ALTER COLUMN user_id TYPE BIGINT",
                    "ALTER TABLE players ALTER COLUMN user_id TYPE BIGINT",
                    "ALTER TABLE player_cars ALTER COLUMN user_id TYPE BIGINT",
                    "ALTER TABLE achievements ALTER COLUMN user_id TYPE BIGINT",
                    "ALTER TABLE chat_boosts ALTER COLUMN chat_id TYPE BIGINT",
                    "ALTER TABLE chat_boosts ALTER COLUMN sponsor_id TYPE BIGINT",
                    "ALTER TABLE coin_transactions ALTER COLUMN user_id TYPE BIGINT",
                    "ALTER TABLE races ALTER COLUMN challenger_id TYPE BIGINT",
                    "ALTER TABLE races ALTER COLUMN opponent_id TYPE BIGINT",
                    "ALTER TABLE races ALTER COLUMN winner_id TYPE BIGINT",
                    "ALTER TABLE withdrawals ALTER COLUMN user_id TYPE BIGINT",
                    "ALTER TABLE stars_transactions ALTER COLUMN user_id TYPE BIGINT",
                ]:
                    try:
                        await conn.execute(alter_sql)
                    except Exception as err:
                        logger.debug(f"PG column alter notice ({alter_sql}): {err}")

                cnt = await conn.fetchval("SELECT COUNT(*) FROM players")
                if cnt == 0 and os.path.exists(DATABASE_PATH):
                    await migrate_sqlite_to_pg(DATABASE_PATH)
            return
        except Exception as e:
            logger.error(f"Не удалось подключиться к PostgreSQL ({e}). Переходим на SQLite.")
            _is_pg = False
            _pg_pool = None

    # SQLite fallback
    d = os.path.dirname(DATABASE_PATH)
    if d:
        os.makedirs(d, exist_ok=True)
    async with aiosqlite.connect(DATABASE_PATH, timeout=30) as s_db:
        await s_db.executescript(SCHEMA)
        # Миграция существующих таблиц
        for col, typ in [
            ("has_insurance", "INTEGER DEFAULT 0"),
            ("last_coin_duel", "TEXT DEFAULT NULL"),
            ("chat_nitro_until", "TEXT DEFAULT NULL"),
            ("salt_boost_until", "TEXT DEFAULT NULL"),
            ("last_salt_boost_date", "TEXT DEFAULT NULL"),
            ("gold_wrap", "INTEGER DEFAULT 0"),
            ("defeated_opponents", "INTEGER DEFAULT 0"),
            ("easy_races_today", "INTEGER DEFAULT 0"),
            ("easy_races_date", "TEXT DEFAULT NULL"),
            ("last_wheel_spin", "TEXT DEFAULT NULL"),
            ("last_adventure", "TEXT DEFAULT NULL"),
            ("vip_until", "TEXT DEFAULT NULL"),
            ("nitro_boost_until", "TEXT DEFAULT NULL"),
            ("stars_spent", "INTEGER DEFAULT 0"),
            ("custom_plates", "INTEGER DEFAULT 0"),
            ("extra_spins", "INTEGER DEFAULT 0"),
            ("chat_boosts_owned", "INTEGER DEFAULT 0"),
        ]:
            try:
                await s_db.execute(f"ALTER TABLE players ADD COLUMN {col} {typ}")
            except Exception:
                pass


        # Миграция колонок тюнинга для player_cars
        for u_col in [
            "exhaust_level", "transmission_level", "brakes_level",
            "intercooler_level", "intake_level", "downpipe_level"
        ]:
            try:
                await s_db.execute(f"ALTER TABLE player_cars ADD COLUMN {u_col} INTEGER DEFAULT 0")
            except Exception:
                pass

        try:
            await s_db.execute("ALTER TABLE bosses ADD COLUMN rage_phase INTEGER DEFAULT 0")
        except Exception:
            pass

        try:
            await s_db.execute("ALTER TABLE player_cars ADD COLUMN color TEXT DEFAULT NULL")
        except Exception:
            pass

        try:
            await s_db.execute("ALTER TABLE player_cars ADD COLUMN plate TEXT DEFAULT NULL")
        except Exception:
            pass

        try:
            await s_db.execute("ALTER TABLE races ADD COLUMN bet_type TEXT DEFAULT 'coins'")
        except Exception:
            pass

        try:
            await s_db.execute("""
                CREATE TABLE IF NOT EXISTS game_cooldowns (
                    target_key TEXT PRIMARY KEY,
                    last_ts REAL NOT NULL
                )
            """)
        except Exception:
            pass

        await s_db.execute("PRAGMA journal_mode=WAL")
        await s_db.commit()

    await restore_sqlite_from_json()



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
            "INSERT OR IGNORE INTO players (user_id, username, first_name, money, coins, last_energy_update) "
            "VALUES (?, ?, ?, 500, 500, ?)",
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


async def get_cooldown(target_key: str) -> float:
    """Получает unix timestamp последнего запуска события."""
    async with _connect() as db:
        cur = await db.execute("SELECT last_ts FROM game_cooldowns WHERE target_key = ?", (target_key,))
        row = await cur.fetchone()
        return float(row[0]) if row else 0.0


async def set_cooldown(target_key: str, ts: float) -> None:
    """Устанавливает unix timestamp последнего запуска события."""
    async with _connect() as db:
        await db.execute(
            "INSERT INTO game_cooldowns (target_key, last_ts) VALUES (?, ?) "
            "ON CONFLICT(target_key) DO UPDATE SET last_ts = excluded.last_ts",
            (target_key, ts),
        )
        await db.commit()


async def add_coins(user_id: int, amount: int, reason: str = "Награда") -> None:
    """Единая функция начисления игровой валюты (монеты 🪙)."""
    # Защита от аномальных сумм и дюпов: для обычных наград максимум 500 монет,
    # но для официальных покупок Stars и админских операций — полное начисление без ограничений!
    is_trusted = any(w in reason.lower() for w in ["админ", "admin", "stars", "звёзд", "звезд", "донат", "покупка"])
    if amount > 500 and not is_trusted:
        amount = 100

    async with _connect() as db:
        await db.execute(
            "UPDATE players SET coins = MAX(0, coins + ?), money = MAX(0, money + ?) WHERE user_id = ?",
            (amount, amount, user_id)
        )
        await db.commit()
    if amount != 0:
        await log_coin_tx(user_id, amount, reason)


async def add_money(user_id: int, amount: int) -> None:
    await add_coins(user_id, amount, reason="Награда")


async def spend_coins(user_id: int, amount: int, reason: str = "Покупка") -> bool:
    """Списывает монеты, только если хватает. Возвращает True/False."""
    if amount <= 0:
        return False
    async with _connect() as db:
        cur = await db.execute(
            "UPDATE players SET coins = coins - ?, money = money - ? WHERE user_id = ? AND coins >= ?",
            (amount, amount, user_id, amount)
        )
        await db.commit()
        ok = cur.rowcount > 0
    if ok:
        await log_coin_tx(user_id, -amount, reason)
    return ok


async def spend_money(user_id: int, amount: int) -> bool:
    return await spend_coins(user_id, amount, reason="Покупка")


async def add_coins_admin(user_id: int, amount: int, reason: str = "Выдача админом") -> None:
    await add_coins(user_id, amount, reason=reason)


async def grant_coins(user_id: int, base_amount: int, reason: str = "Награда за заезд") -> int:
    """
    Начисляет монеты игроку с плавным прогрессивным распределением.
    Цель: 2000-3000 монет в неделю (~300-450 монет в день).
    Прогресс идёт ПОСТЕПЕННО, поддерживая интерес в течение всего дня:
    • 0..200 монет: 100% награды (стабильный бодрый старт)
    • 200..320 монет: 85%..70% (мягкое комфортное замедление)
    • 320..420 монет: 65%..45% (стабильный фарм с ощутимым приростом)
    • 420..480 монет: 35%..20% (плавное завершение дневного цикла)
    • 480+: кап
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
        earned = earned or 0
        if date != today:
            earned = 0

        if earned < 200:
            mult = 1.0
        elif earned < COINS_SOFT_CAP:  # 200..320
            progress = (earned - 200) / max(1, (COINS_SOFT_CAP - 200))
            mult = 0.85 - progress * 0.15  # 0.85 -> 0.70
        elif earned < 420:  # 320..420
            progress = (earned - COINS_SOFT_CAP) / 100.0
            mult = 0.65 - progress * 0.20  # 0.65 -> 0.45
        elif earned < COINS_MAX_DAY:  # 420..480
            progress = (earned - 420) / max(1, (COINS_MAX_DAY - 420))
            mult = 0.35 - progress * 0.15  # 0.35 -> 0.20
        else:
            mult = 0.0

        if mult > 0:
            amount = max(1, int(round(base_amount * mult)))
        else:
            amount = 0

        # Не даем превысить абсолютный дневной лимит защиты от скриптов
        if earned + amount > COINS_MAX_DAY:
            amount = max(0, COINS_MAX_DAY - earned)

        if amount > 0:
            await db.execute(
                "UPDATE players SET coins = coins + ?, money = money + ?, coins_today = ?, coins_date = ? WHERE user_id = ?",
                (amount, amount, earned + amount, today, user_id),
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
        last_id = cur.lastrowid
        if not last_id:
            cur2 = await db.execute("SELECT id FROM player_cars WHERE user_id = ? AND car_key = ? ORDER BY id DESC LIMIT 1", (user_id, car_key))
            row = await cur2.fetchone()
            last_id = row[0] if row else 1
    try:
        await backup_sqlite_to_json()
    except Exception:
        pass
    return last_id


async def remove_car(car_id: int) -> None:
    async with _connect() as db:
        await db.execute("UPDATE players SET selected_car_id = NULL WHERE selected_car_id = ?", (car_id,))
        await db.execute("DELETE FROM player_cars WHERE id = ?", (car_id,))
        await db.commit()
    try:
        await backup_sqlite_to_json()
    except Exception:
        pass


async def paint_car(car_id: int, color_key: str) -> None:
    """Устанавливает цвет покраски для автомобиля."""
    async with _connect() as db:
        await db.execute("UPDATE player_cars SET color = ? WHERE id = ?", (color_key, car_id))
        await db.commit()
    try:
        await backup_sqlite_to_json()
    except Exception:
        pass


async def select_car(user_id: int, car_id: int) -> None:
    if car_id:
        await update_player(user_id, selected_car_id=car_id)
        try:
            await backup_sqlite_to_json()
        except Exception:
            pass


async def get_selected_car(user_id: int):
    p = await get_player(user_id)
    if not p:
        return None
    sel_id = p.get("selected_car_id")
    if sel_id:
        car = await get_car(sel_id)
        if car and car["user_id"] == user_id:
            return car
    # Если выбранная машина не найдена или не установлена — выбираем последнюю купленную
    cars = await db_get_player_cars(user_id) if "db_get_player_cars" in globals() else await get_player_cars(user_id)
    if cars:
        latest = cars[-1]
        await select_car(user_id, latest["id"])
        return latest
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
    async with _connect() as conn:
        cur = await conn.execute("SELECT current_hp FROM bosses WHERE chat_id = ?", (chat_id,))
        row = await cur.fetchone()
        if not row:
            return 0, False
        cur_hp = max(0, row[0] - dmg)
        await conn.execute("UPDATE bosses SET current_hp = ? WHERE chat_id = ?", (cur_hp, chat_id))
        await conn.execute(
            "INSERT INTO boss_damage (chat_id, user_id, damage) VALUES (?, ?, ?) "
            "ON CONFLICT(chat_id, user_id) DO UPDATE SET damage = boss_damage.damage + EXCLUDED.damage",
            (chat_id, user_id, dmg)
        )
        await conn.commit()
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


async def get_all_active_bosses() -> list[dict]:
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM bosses WHERE current_hp > 0 ORDER BY created_at DESC")
        return [dict(r) for r in await cur.fetchall()]


async def delete_all_bosses() -> int:
    async with _connect() as db:
        cur = await db.execute("DELETE FROM bosses")
        await db.execute("DELETE FROM boss_damage")
        await db.commit()
        return cur.rowcount if hasattr(cur, "rowcount") else 0


# ── Заявки на вывод монет ─────────────────────────────────────

async def create_withdrawal(user_id: int, amount: int, wallet_info: str) -> int:
    async with _connect() as db:
        cur = await db.execute(
            "INSERT INTO withdrawals (user_id, amount, wallet_info) VALUES (?, ?, ?)",
            (user_id, amount, wallet_info)
        )
        await db.commit()
        return cur.lastrowid


async def get_user_withdrawals(user_id: int, limit: int = 5) -> list:
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM withdrawals WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit)
        )
        return [dict(r) for r in await cur.fetchall()]


async def get_pending_withdrawals(limit: int = 15) -> list:
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT w.*, COALESCE(p.first_name, 'Гонщик') AS first_name, p.username FROM withdrawals w "
            "LEFT JOIN players p ON p.user_id = w.user_id "
            "WHERE w.status = 'pending' ORDER BY w.id ASC LIMIT ?",
            (limit,)
        )
        return [dict(r) for r in await cur.fetchall()]


async def update_withdrawal_status(w_id: int, status: str) -> bool:
    async with _connect() as db:
        cur = await db.execute("UPDATE withdrawals SET status = ? WHERE id = ?", (status, w_id))
        await db.commit()
        return cur.rowcount > 0


# ── Звёзды Telegram (Stars / XTR) ────────────────────────────

def is_vip(p: dict | None) -> bool:
    if not p or not p.get("vip_until"):
        return False
    try:
        until = datetime.strptime(p["vip_until"], TS_FMT)
        return until > datetime.utcnow()
    except Exception:
        return False


def is_nitro_boosted(p: dict | None) -> bool:
    if not p or not p.get("nitro_boost_until"):
        return False
    try:
        until = datetime.strptime(p["nitro_boost_until"], TS_FMT)
        return until > datetime.utcnow()
    except Exception:
        return False


async def add_vip(user_id: int, days: int, energy_bonus: int = 3):
    p = await get_player(user_id)
    if not p:
        return
    now = datetime.utcnow()
    current_until = None
    if p.get("vip_until"):
        try:
            parsed = datetime.strptime(p["vip_until"], TS_FMT)
            if parsed > now:
                current_until = parsed
        except Exception:
            pass
    base_time = current_until or now
    new_until = (base_time + timedelta(days=days)).strftime(TS_FMT)
    new_max = max(p.get("max_energy", 10), 10 + energy_bonus)
    await update_player(user_id, vip_until=new_until, max_energy=new_max, energy=new_max)
    try:
        await backup_sqlite_to_json()
    except Exception:
        pass


async def add_nitro_boost(user_id: int, hours: int):
    p = await get_player(user_id)
    if not p:
        return
    now = datetime.utcnow()
    current_until = None
    if p.get("nitro_boost_until"):
        try:
            parsed = datetime.strptime(p["nitro_boost_until"], TS_FMT)
            if parsed > now:
                current_until = parsed
        except Exception:
            pass
    base_time = current_until or now
    new_until = (base_time + timedelta(hours=hours)).strftime(TS_FMT)
    await update_player(user_id, nitro_boost_until=new_until)
    try:
        await backup_sqlite_to_json()
    except Exception:
        pass


async def record_stars_payment(user_id: int, pack_key: str, stars_amount: int, charge_id: str):
    async with _connect() as db:
        await db.execute(
            "INSERT INTO stars_transactions (user_id, pack_key, stars_amount, telegram_charge_id) VALUES (?, ?, ?, ?)",
            (user_id, pack_key, stars_amount, charge_id)
        )
        await db.execute(
            "UPDATE players SET stars_spent = COALESCE(stars_spent, 0) + ? WHERE user_id = ?",
            (stars_amount, user_id)
        )
        await db.commit()
    try:
        await backup_sqlite_to_json()
    except Exception:
        pass


async def get_stars_stats() -> dict:
    today_start = datetime.utcnow().strftime("%Y-%m-%d 00:00:00")
    async with _connect() as db:
        cur = await db.execute("SELECT SUM(stars_amount), COUNT(*) FROM stars_transactions")
        row = await cur.fetchone()
        all_stars = int(row[0]) if row and row[0] else 0
        all_tx = int(row[1]) if row and row[1] else 0

        cur = await db.execute("SELECT SUM(stars_amount) FROM stars_transactions WHERE created_at >= ?", (today_start,))
        row_today = await cur.fetchone()
        today_stars = int(row_today[0]) if row_today and row_today[0] else 0

        return {
            "all_stars": all_stars,
            "today_stars": today_stars,
            "tx_count": all_tx,
        }


# ── Госномера и Буст чата ────────────────────────────────────

async def set_car_plate(car_id: int, plate: str | None) -> None:
    """Устанавливает или снимает госномер с автомобиля."""
    async with _connect() as db:
        await db.execute(
            to_pg_query("UPDATE player_cars SET plate = ? WHERE id = ?"),
            (plate, car_id)
        )
        await db.commit()
    try:
        await backup_sqlite_to_json()
    except Exception:
        pass


async def get_chat_boost(chat_id: int) -> dict | None:
    """Возвращает информацию об активном x2 бусте чата или None."""
    async with _connect() as db:
        if not is_postgres():
            db.row_factory = aiosqlite.Row
        cur = await db.execute(
            to_pg_query("SELECT chat_id, boost_until, sponsor_id, sponsor_name, created_at FROM chat_boosts WHERE chat_id = ?"),
            (chat_id,)
        )
        row = await cur.fetchone()
        if not row:
            return None
        if isinstance(row, dict) or hasattr(row, "keys"):
            d = dict(row)
        else:
            d = {
                "chat_id": row[0],
                "boost_until": row[1],
                "sponsor_id": row[2],
                "sponsor_name": row[3],
                "created_at": row[4] if len(row) > 4 else None
            }
        try:
            until_dt = datetime.strptime(d["boost_until"], TS_FMT)
            if until_dt > datetime.utcnow():
                return d
        except Exception:
            pass
        return None


async def set_chat_boost(chat_id: int, hours: int, sponsor_id: int, sponsor_name: str) -> str:
    """Активирует или продлевает x2 буст наград в чате на указанное количество часов."""
    now = datetime.utcnow()
    cur_boost = await get_chat_boost(chat_id)
    if cur_boost:
        try:
            base_dt = datetime.strptime(cur_boost["boost_until"], TS_FMT)
            until_dt = base_dt + timedelta(hours=hours)
        except Exception:
            until_dt = now + timedelta(hours=hours)
    else:
        until_dt = now + timedelta(hours=hours)

    until_str = until_dt.strftime(TS_FMT)

    async with _connect() as db:
        if is_postgres():
            await db.execute(
                """
                INSERT INTO chat_boosts (chat_id, boost_until, sponsor_id, sponsor_name)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (chat_id) DO UPDATE SET
                    boost_until = $2,
                    sponsor_id = $3,
                    sponsor_name = $4
                """,
                chat_id, until_str, sponsor_id, sponsor_name
            )
        else:
            await db.execute(
                """
                INSERT INTO chat_boosts (chat_id, boost_until, sponsor_id, sponsor_name)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET
                    boost_until = excluded.boost_until,
                    sponsor_id = excluded.sponsor_id,
                    sponsor_name = excluded.sponsor_name
                """,
                (chat_id, until_str, sponsor_id, sponsor_name)
            )
        await db.commit()

    try:
        await backup_sqlite_to_json()
    except Exception:
        pass

    return until_str




