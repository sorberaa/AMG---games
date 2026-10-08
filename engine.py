"""Игровой движок: статы, симуляция гонок, награды, достижения."""
import random

from data import CAR_CATALOG, UPGRADE_BONUSES, UPGRADE_DEFS, DAILY_REWARDS

STAT_KEYS = ("power", "speed", "acceleration", "handling", "weight")


def calc_stats(car: dict, upgrades: dict) -> dict:
    """car — запись из CAR_CATALOG, upgrades — {'engine': 2, ...} или строка player_cars."""
    pct = {"power_pct": 0, "speed_pct": 0, "accel_pct": 0, "handling_pct": 0, "weight_pct": 0}
    for key in UPGRADE_DEFS:
        lvl = upgrades.get(key, upgrades.get(f"{key}_level", 0)) or 0
        if lvl > 0:
            for k, v in UPGRADE_BONUSES[key][lvl - 1].items():
                pct[k] += v
    s = {
        "power": car["power"] * (1 + pct["power_pct"] / 100),
        "speed": car["speed"] * (1 + pct["speed_pct"] / 100),
        "acceleration": max(1.8, car["acceleration"] * (1 - pct["accel_pct"] / 100)),
        "handling": min(150, car["handling"] * (1 + pct["handling_pct"] / 100)),
        "weight": car["weight"] * (1 + pct["weight_pct"] / 100),
    }
    s["rating"] = int(s["power"] * 0.3 + s["speed"] * 0.25 + (15 - s["acceleration"]) * 20 * 0.25 + s["handling"] * 0.2)
    return s


def car_upgrades(player_car: dict) -> dict:
    return {k: player_car.get(f"{k}_level", 0) for k in UPGRADE_DEFS}


ROUNDS = [
    ("🚦 СТАРТ", {"accel": 0.6, "power": 0.2}, 0.2),
    ("🛣 ПРЯМАЯ", {"speed": 0.4, "power": 0.35}, 0.25),
    ("↩️ ПОВОРОТ", {"handling": 0.55, "weight": 0.25}, 0.2),
    ("🏎 СПРИНТ", {"power": 0.4, "accel": 0.35}, 0.25),
    ("🏁 ФИНИШ", {"speed": 0.25, "power": 0.25, "accel": 0.2, "handling": 0.15}, 0.15),
]

PHRASES = {
    "🚦 СТАРТ": ["{a} срывается с места с визгом шин!", "{a} идеально ловит старт!", "{b} буксует, {a} уходит вперёд!"],
    "🛣 ПРЯМАЯ": ["{a} давит в пол — стрелка за 250!", "На прямой {a} показывает мощь V8!", "{a} уходит в отрыв на прямой!"],
    "↩️ ПОВОРОТ": ["{a} проходит поворот как по рельсам!", "{b} заносит, {a} пользуется моментом!", "{a} тормозит позже всех и выигрывает метры!"],
    "🏎 СПРИНТ": ["{a} врубает нитро! 💨", "{a} выжимает всё из мотора!", "Рёв выхлопа — {a} снова впереди!"],
    "🏁 ФИНИШ": ["{a} первым пересекает черту!", "Фотофиниш... и это {a}!", "{a} вырывает победу на последних метрах!"],
}
CLOSE = ["Борьба нос к носу!", "Разница — считанные сантиметры!", "Никто не уступает!"]


def _norm(s: dict) -> dict:
    return {
        "power": s["power"] / 10,
        "speed": s["speed"] / 3.5,
        "accel": (15 - s["acceleration"]) * 8,
        "handling": s["handling"],
        "weight": (3000 - s["weight"]) / 20,
    }


def simulate_race(s1: dict, s2: dict, name1: str, name2: str, p1_insured: bool = False, p2_insured: bool = False) -> dict:
    # 1% шанс аварии для каждого участника
    p1_crash = random.random() < 0.01
    p2_crash = random.random() < 0.01

    if p1_crash or p2_crash:
        crashed_1 = p1_crash
        crashed_2 = p2_crash
        insurance_saved_1 = False
        insurance_saved_2 = False

        if crashed_1 and p1_insured:
            insurance_saved_1 = True
            crashed_1 = False
        if crashed_2 and p2_insured:
            insurance_saved_2 = True
            crashed_2 = False

        if crashed_1 and not crashed_2:
            return {
                "winner": 2,
                "crashed": 1,
                "insurance_saved": 0,
                "narrative": f"💥 <b>АВАРИЯ НА СКОРОСТИ 280 КМ/Ч!</b>\nМашину <b>{name1}</b> развернуло в отбойник! Гонка окончена.",
                "margin": "из-за вылета соперника! 🚨"
            }
        elif crashed_2 and not crashed_1:
            return {
                "winner": 1,
                "crashed": 2,
                "insurance_saved": 0,
                "narrative": f"💥 <b>АВАРИЯ НА СКОРОСТИ 280 КМ/Ч!</b>\nМашину <b>{name2}</b> занесло в ограждение! Гонка окончена.",
                "margin": "из-за вылета соперника! 🚨"
            }
        elif insurance_saved_1 or insurance_saved_2:
            saved_name = name1 if insurance_saved_1 else name2
            saved_note = f"🛡 <i>Страховка AMG спасла {saved_name} от крушения! Системы удержали курс.</i>\n\n"
        else:
            saved_note = ""
    else:
        saved_note = ""

    n1, n2 = _norm(s1), _norm(s2)
    total1 = total2 = 0.0
    lines = []
    for rname, weights, rnd_w in ROUNDS:
        base1 = sum(n1[k] * w for k, w in weights.items())
        base2 = sum(n2[k] * w for k, w in weights.items())
        avg = (base1 + base2) / 2 or 1
        sc1 = base1 * random.uniform(0.85, 1.15) + avg * rnd_w * 1.5 * random.random()
        sc2 = base2 * random.uniform(0.85, 1.15) + avg * rnd_w * 1.5 * random.random()
        total1 += sc1
        total2 += sc2
        a, b = (name1, name2) if sc1 >= sc2 else (name2, name1)
        diff = abs(sc1 - sc2) / max(sc1, sc2, 1)
        text = random.choice(PHRASES[rname]).format(a=f"<b>{a}</b>", b=b)
        if diff < 0.03:
            text = random.choice(CLOSE) + " " + text
        leader = name1 if total1 >= total2 else name2
        lines.append(f"<b>{rname}</b>\n{text}\n<i>Лидирует: {leader}</i>")
    winner = 1 if total1 >= total2 else 2
    gap = abs(total1 - total2) / max(total1, total2)
    margin = "с огромным отрывом! 🔥" if gap > 0.12 else "в упорной борьбе! 💪" if gap > 0.04 else "на волоске! 😱"
    return {
        "winner": winner,
        "crashed": 0,
        "insurance_saved": 1 if (p1_crash and p1_insured) else (2 if (p2_crash and p2_insured) else 0),
        "narrative": saved_note + "\n\n".join(lines),
        "margin": margin
    }



def calc_rewards(level: int, race_type: str, mult: float = 1.0, won: bool = True) -> dict:
    xp = (30 + level * 5) * mult
    money = (500 + level * 150) * mult
    rep = 5 + level
    coins = random.randint(8, 15) * mult
    if race_type == "pvp":
        xp *= 1.3
        money *= 1.5
        coins *= 1.3
    if not won:
        return {"xp": int(xp * 0.3), "money": int(money * 0.15), "rep": 0, "coins": random.randint(1, 4)}
    return {"xp": int(xp), "money": int(money), "rep": int(rep), "coins": int(coins)}


def get_daily_reward(streak: int) -> dict:
    return DAILY_REWARDS[(max(1, streak) - 1) % len(DAILY_REWARDS)]


def check_achievements(player: dict, cars: list, current: list, extra: set = None) -> list:
    keys = {c["car_key"] for c in cars}
    classes = {CAR_CATALOG[k]["cls"] for k in keys if k in CAR_CATALOG}
    full_tune = any(all(c.get(f"{u}_level", 0) >= d["max_level"] for u, d in UPGRADE_DEFS.items()) for c in cars)
    cond = {
        "first_race": player["races_total"] >= 1,
        "first_win": player["wins"] >= 1,
        "ten_wins": player["wins"] >= 10,
        "fifty_wins": player["wins"] >= 50,
        "hundred_wins": player["wins"] >= 100,
        "buy_first_car": len(cars) >= 2,
        "five_cars": len(cars) >= 5,
        "ten_cars": len(cars) >= 10,
        "class_s_car": "S" in classes,
        "class_ss_car": "SS" in classes,
        "amg_one_owner": "amg_one" in keys,
        "level_10": player["level"] >= 10,
        "level_25": player["level"] >= 25,
        "millionaire": player["money"] >= 1_000_000,
        "streak_7": player["daily_streak"] >= 7,
        "pvp_win": player.get("pvp_wins", 0) >= 1,
        "full_tune": full_tune,
    }
    for e in (extra or set()):
        cond[e] = True
    return [k for k, ok in cond.items() if ok and k not in current]

