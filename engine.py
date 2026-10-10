"""Игровой движок: статы, симуляция гонок, награды, достижения."""
import random

from data import CAR_CATALOG, UPGRADE_BONUSES, UPGRADE_DEFS, DAILY_REWARDS, assign_unique_colors, CAR_COLORS

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
    ("🚦 СТАРТ", {"accel": 0.65, "power": 0.25}, 0.2),
    ("🛣 ПРЯМАЯ", {"speed": 0.45, "power": 0.40}, 0.25),
    ("↩️ ПОВОРОТ", {"handling": 0.65, "weight": 0.25}, 0.2),
    ("🏎 СПРИНТ", {"power": 0.45, "accel": 0.40}, 0.25),
    ("🏁 ФИНИШ", {"speed": 0.3, "power": 0.3, "accel": 0.2, "handling": 0.2}, 0.15),
]

PHRASES = {
    "🚦 СТАРТ": [
        "{c_a} <b>{a}</b> сорвался с лаунча как ракета!",
        "{c_a} <b>{a}</b> идеально поймал момент сцепления шин!",
        "{c_b} {b} слегка пробуксовал, {c_a} <b>{a}</b> вырывается на корпус вперёд!"
    ],
    "🛣 ПРЯМАЯ": [
        "На длинной прямой {c_a} <b>{a}</b> развивает бешеную тягу V8 Biturbo!",
        "{c_a} <b>{a}</b> ловит слипстрим и обходит соперника на скорости 270 км/ч!",
        "Стрелка спидометра зашкаливает: {c_a} <b>{a}</b> летит впереди!"
    ],
    "↩️ ПОВОРОТ": [
        "↩️ {c_a} <b>{a}</b> филигранно срезает апекс по идеальной траектории!",
        "↩️ {c_b} {b} сносит заднюю ось! {c_a} <b>{a}</b> прошивает поворот!",
        "↩️ Позднее торможение: {c_a} <b>{a}</b> удерживает внутренний радиус!"
    ],
    "🏎 СПРИНТ": [
        "🏎 {c_a} <b>{a}</b> врубает баллон нитро и открывает дроссели на 100%!",
        "🏎 Рёв прямоточного выхлопа AMG: {c_a} <b>{a}</b> держит газ в полу!",
        "🏎 Борьба на пределе сцепления: {c_a} <b>{a}</b> штурмует прямик!"
    ],
    "🏁 ФИНИШ": [
        "🏁 {c_a} <b>{a}</b> первым влетает под клетчатый флаг!",
        "🏁 Финишная черта! {c_a} <b>{a}</b> забирает заезд!",
        "🏁 Считанные доли секунды — и {c_a} <b>{a}</b> вырывает победу!"
    ],
}

CLOSE = ["🔥 Борьба нос в нос!", "⚡ Разрыв в миллиметры!", "💥 Никто не уступает!"]


def _norm(s: dict) -> dict:
    return {
        "power": s["power"] / 10,
        "speed": s["speed"] / 3.5,
        "accel": (15 - s["acceleration"]) * 8,
        "handling": s["handling"],
        "weight": (3000 - s["weight"]) / 20,
    }


def simulate_race(
    s1: dict,
    s2: dict,
    name1: str,
    name2: str,
    p1_insured: bool = False,
    p2_insured: bool = False,
    p1_immune: bool = False,
    p2_immune: bool = False,
    p1_color: str = None,
    p2_color: str = None
) -> dict:
    # Присваиваем каждому участнику УНИКАЛЬНЫЙ цвет
    c1, c2 = assign_unique_colors(p1_color, p2_color)

    # 1% шанс аварии
    p1_crash = (random.random() < 0.01) and (not p1_immune)
    p2_crash = (random.random() < 0.01) and (not p2_immune)

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
                "narrative": f"💥 <b>АВАРИЯ НА СКОРОСТИ 280 КМ/Ч!</b>\nБолид {c1} <b>{name1}</b> развернуло в отбойник! Гонка окончена.",
                "margin": "из-за вылета соперника! 🚨",
                "color1": c1,
                "color2": c2
            }
        elif crashed_2 and not crashed_1:
            return {
                "winner": 1,
                "crashed": 2,
                "insurance_saved": 0,
                "narrative": f"💥 <b>АВАРИЯ НА СКОРОСТИ 280 КМ/Ч!</b>\nБолид {c2} <b>{name2}</b> занесло в ограждение! Гонка окончена.",
                "margin": "из-за вылета соперника! 🚨",
                "color1": c1,
                "color2": c2
            }
        elif insurance_saved_1 or insurance_saved_2:
            saved_name = f"{c1} {name1}" if insurance_saved_1 else f"{c2} {name2}"
            saved_note = f"🛡 <i>Страховка AMG спасла {saved_name} от крушения! Системы удержали курс.</i>\n\n"
        else:
            saved_note = ""
    else:
        saved_note = ""

    n1, n2 = _norm(s1), _norm(s2)
    total1 = total2 = 0.0
    lines = []
    prev_leader_idx = None

    for r_idx, (rname, weights, rnd_w) in enumerate(ROUNDS, start=1):
        base1 = sum(n1[k] * w for k, w in weights.items())
        base2 = sum(n2[k] * w for k, w in weights.items())
        avg = (base1 + base2) / 2 or 1

        # Динамика на повороте: увеличиваем влияние управляемости для интриги
        if "ПОВОРОТ" in rname:
            turn_rnd = random.uniform(0.75, 1.25)
            sc1 = base1 * turn_rnd + avg * rnd_w * 1.8 * random.random()
            sc2 = base2 * (2.0 - turn_rnd) + avg * rnd_w * 1.8 * random.random()
        else:
            sc1 = base1 * random.uniform(0.85, 1.15) + avg * rnd_w * 1.5 * random.random()
            sc2 = base2 * random.uniform(0.85, 1.15) + avg * rnd_w * 1.5 * random.random()

        total1 += sc1
        total2 += sc2

        round_winner = 1 if sc1 >= sc2 else 2
        overall_leader = 1 if total1 >= total2 else 2

        # Данные лидера и преследователя
        if round_winner == 1:
            a_name, b_name = name1, name2
            c_a, c_b = c1, c2
        else:
            a_name, b_name = name2, name1
            c_a, c_b = c2, c1

        # Формируем интригующее описание
        is_overtake = (prev_leader_idx is not None and overall_leader != prev_leader_idx)
        prev_leader_idx = overall_leader

        if is_overtake and "ПОВОРОТ" in rname:
            overtake_desc = f"⚡ <b>ПЕРЕХВАТ ЛИДЕРСТВА В ПОВОРОТЕ!</b> {c_a} <b>{a_name}</b> ныряет по внутреннему радиусу и вырывается вперёд!"
            text = overtake_desc
        elif is_overtake and "ПРЯМАЯ" in rname:
            overtake_desc = f"🚀 <b>ОБГОН НА ПРЯМОЙ!</b> {c_a} <b>{a_name}</b> на слипстриме обходит {c_b} {b_name}!"
            text = overtake_desc
        else:
            text = random.choice(PHRASES[rname]).format(a=a_name, b=b_name, c_a=c_a, c_b=c_b)

        # Вычисляем разрыв
        diff = abs(total1 - total2) / max(total1, total2, 1)
        if diff < 0.03:
            text = random.choice(CLOSE) + " " + text

        # Кто сейчас лидирует в гонке
        leader_color = c1 if overall_leader == 1 else c2
        leader_name = name1 if overall_leader == 1 else name2
        gap_meters = max(1, int(diff * 80))

        # Визуальная шкала дистанции
        if diff < 0.02:
            track_bar = f"<code>[🏁 ─── {c1}🏎 {c2}🏎 БОК О БОК! ───]</code>"
        elif overall_leader == 1:
            track_bar = f"<code>[🏁 ── {c1}🏎 ── +{gap_meters}м ── {c2}🏎 ──]</code>"
        else:
            track_bar = f"<code>[🏁 ── {c2}🏎 ── +{gap_meters}м ── {c1}🏎 ──]</code>"

        status_line = f"🥇 <b>ВЕДЁТ:</b> {leader_color} <b>{leader_name}</b>"
        lines.append(f"<b>{rname}</b>\n{text}\n{track_bar}\n{status_line}")

    winner = 1 if total1 >= total2 else 2
    gap = abs(total1 - total2) / max(total1, total2)
    margin = "с огромным отрывом! 🔥" if gap > 0.12 else "в упорной борьбе! 💪" if gap > 0.04 else "на волоске! 😱"

    return {
        "winner": winner,
        "crashed": 0,
        "insurance_saved": 1 if (p1_crash and p1_insured) else (2 if (p2_crash and p2_insured) else 0),
        "narrative": saved_note + "\n\n".join(lines),
        "round_steps": lines,
        "saved_note": saved_note,
        "margin": margin,
        "color1": c1,
        "color2": c2
    }





def calc_rewards(level: int, race_type: str, mult: float = 1.0, won: bool = True, car_rating: int = 150) -> dict:
    """
    Награды зависят от уровня, множителя противника И КЛАССА/РЕЙТИНГА ТАЧКИ (Аура тачки):
    Базовая C180 (рейтинг ~140) дает обычный доход.
    Топ спорткары и гиперкары (рейтинг 250 - 500+) дают в разы больше денег и монет!
    """
    aura_mult = max(0.8, car_rating / 160.0)

    xp = (30 + level * 6) * mult
    money = (600 + level * 160) * mult * aura_mult
    rep = int((5 + level) * aura_mult)
    coins = random.randint(8, 15) * mult * (aura_mult ** 0.8)

    if race_type == "pvp":
        xp *= 1.3
        money *= 1.5
        coins *= 1.3

    if not won:
        return {"xp": int(xp * 0.3), "money": int(money * 0.15), "rep": 0, "coins": random.randint(1, 3)}
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

