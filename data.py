"""Игровые данные AMG Racing."""

CAR_CLASSES = ["D", "C", "B", "A", "S", "SS"]
CAR_CLASS_NAMES = {"D": "Начальный", "C": "Любитель", "B": "Продвинутый",
                   "A": "Эксперт", "S": "Мастер", "SS": "Легенда"}
CAR_CLASS_EMOJIS = {"D": "🟢", "C": "🔵", "B": "🟡", "A": "🟠", "S": "⭐", "SS": "💎"}

# Палитра фирменных цветов Mercedes-AMG
CAR_COLORS = {
    "red":    {"name": "Красный (Designo Cardinal)", "emoji": "🔴", "price": 150},
    "yellow": {"name": "Жёлтый (Solarbeam Yellow)",   "emoji": "🟡", "price": 200},
    "green":  {"name": "Зелёный (Green Hell Magno)",  "emoji": "🟢", "price": 300},
    "blue":   {"name": "Синий (Brilliant Blue)",      "emoji": "🔵", "price": 200},
    "purple": {"name": "Фиолетовый (Mystic Purple)",  "emoji": "🟣", "price": 250},
    "orange": {"name": "Оранжевый (Copper Orange)",   "emoji": "🟠", "price": 250},
    "black":  {"name": "Чёрный (Obsidian Black)",     "emoji": "⚫", "price": 150},
    "white":  {"name": "Белый (Polar White)",         "emoji": "⚪", "price": 100},
    "brown":  {"name": "Бронзовый (Citrine Brown)",   "emoji": "🟤", "price": 180},
    "grey":   {"name": "Матовый серый (Selenite Magno)", "emoji": "🔘", "price": 220},
}
COLOR_PALETTE = ["🔴", "🟡", "🟢", "🔵", "🟣", "🟠", "⚫", "⚪", "🟤", "🔘"]


def assign_unique_colors(p1_pref: str = None, p2_pref: str = None) -> tuple:
    """
    Выдает уникальные цвета участникам заезда.
    Если у игрока есть покрашенная тачка, пытается выдать его цвет.
    Гарантирует, что у обоих соперников разные цвета!
    """
    import random
    palette = list(COLOR_PALETTE)

    c1 = None
    if p1_pref and p1_pref in CAR_COLORS:
        c1 = CAR_COLORS[p1_pref]["emoji"]
    elif p1_pref in COLOR_PALETTE:
        c1 = p1_pref
    else:
        c1 = random.choice(palette)

    avail = [c for c in palette if c != c1]

    c2 = None
    if p2_pref and p2_pref in CAR_COLORS:
        cand2 = CAR_COLORS[p2_pref]["emoji"]
        c2 = cand2 if cand2 in avail else random.choice(avail)
    elif p2_pref in avail:
        c2 = p2_pref
    else:
        c2 = random.choice(avail)

    return c1, c2


def _car(name, cls, emoji, price, lvl, power, speed, accel, handling, weight, desc):
    return dict(name=name, cls=cls, emoji=emoji, price=price, level_req=lvl, power=power,
                speed=speed, acceleration=accel, handling=handling, weight=weight, desc=desc)


CAR_CATALOG = {
    "c180":    _car("Mercedes C180", "D", "🚗", 0, 1, 156, 230, 8.2, 50, 1500, "Скромный старт. Каждая легенда с чего-то начинала."),
    "a35":     _car("Mercedes-AMG A35", "D", "🏎", 300, 1, 306, 250, 4.7, 60, 1555, "Заряженный хэтч с полным приводом."),
    "c43":     _car("Mercedes-AMG C43", "C", "🏎", 550, 2, 390, 250, 4.7, 65, 1660, "Спокойный снаружи, злой внутри."),
    "cla45":   _car("Mercedes-AMG CLA 45 S", "C", "🏎", 650, 3, 421, 270, 4.0, 68, 1630, "Самый мощный серийный 2.0 турбо в мире."),
    "e53":     _car("Mercedes-AMG E53", "B", "🏎", 1200, 4, 435, 270, 4.4, 70, 1880, "Гибридный бизнес-снаряд."),
    "c63":     _car("Mercedes-AMG C63 S", "B", "🏎", 1500, 5, 510, 290, 3.9, 72, 1740, "Битурбо V8 и легендарный рёв."),
    "g63":     _car("Mercedes-AMG G63", "B", "🚙", 1800, 5, 585, 220, 4.5, 45, 2560, "Гелик. Объяснения не нужны."),
    "cls53":   _car("Mercedes-AMG CLS 53", "A", "🏎", 2800, 7, 435, 270, 4.3, 73, 1870, "Четырёхдверное купе с характером."),
    "e63s":    _car("Mercedes-AMG E63 S", "A", "🏎", 3000, 8, 612, 300, 3.4, 75, 1960, "Седан, который рвёт суперкары."),
    "gt53":    _car("Mercedes-AMG GT 53", "A", "🏎", 3200, 8, 435, 285, 4.1, 76, 1910, "Комфорт GT и скорость AMG."),
    "gle63s":  _car("Mercedes-AMG GLE 63 S", "A", "🚙", 3500, 9, 612, 280, 3.8, 55, 2370, "Кроссовер-ракета."),
    "s63":     _car("Mercedes-AMG S63", "A", "🏎", 4000, 10, 612, 290, 3.5, 68, 2150, "Роскошь на скорости 290."),
    "amg_gt":  _car("Mercedes-AMG GT", "S", "🏎", 5000, 12, 585, 312, 3.6, 82, 1615, "Длинный капот, короткая корма, чистый драйв."),
    "sl63":    _car("Mercedes-AMG SL 63", "S", "🏎", 5500, 12, 585, 315, 3.6, 80, 1790, "Родстер для тех, кто любит ветер."),
    "amg_gts": _car("Mercedes-AMG GT S", "S", "🏎", 6000, 13, 522, 310, 3.7, 84, 1645, "Острая версия GT."),
    "gt63s":   _car("Mercedes-AMG GT 63 S", "S", "🏎", 7000, 15, 639, 315, 3.2, 78, 2100, "Четыре двери, 639 сил."),
    "gt63se":  _car("Mercedes-AMG GT 63 S E Performance", "S", "⚡", 8500, 16, 843, 316, 2.9, 80, 2280, "Гибридный монстр на 843 силы."),
    "amg_gtr": _car("Mercedes-AMG GT R", "SS", "🏎", 10000, 18, 585, 318, 3.6, 90, 1555, "Зелёный ад. Зверь с Нюрбургринга."),
    "gtr_pro": _car("Mercedes-AMG GT R PRO", "SS", "🏎", 12000, 20, 585, 318, 3.6, 95, 1500, "Трековая версия GT R."),
    "gt_bs":   _car("Mercedes-AMG GT Black Series", "SS", "🏎", 15000, 22, 730, 325, 3.2, 92, 1435, "Рекордсмен Нордшляйфе."),
    "amg_one": _car("Mercedes-AMG ONE", "SS", "👑", 30000, 25, 1063, 352, 2.9, 95, 1695, "Болид Формулы-1 с номерами."),
    "amg_gts_star": _car("AMG GT S «Star Edition»", "S", "🌟", 6000, 1, 540, 315, 3.5, 86, 1620, "Эксклюзивная версия GT S в звёздной матовой ливрее."),
    "gt_bs_star":   _car("AMG GT Black Series «Star Edition»", "SS", "👑", 15000, 1, 740, 328, 3.1, 94, 1420, "Королевский гиперкар Black Series в лимитированном звёздном исполнении."),
}


UPGRADE_DEFS = {
    "engine":       {"name": "Двигатель", "emoji": "🔧", "max_level": 5, "mult": 1.0},
    "turbo":        {"name": "Турбина", "emoji": "🌀", "max_level": 5, "mult": 1.2},
    "exhaust":      {"name": "Выхлоп AMG Sport", "emoji": "💨", "max_level": 5, "mult": 0.85},
    "transmission": {"name": "КПП SpeedShift", "emoji": "🕹", "max_level": 5, "mult": 0.95},
    "suspension":   {"name": "Подвеска Ride Control", "emoji": "🔩", "max_level": 5, "mult": 0.8},
    "brakes":       {"name": "Карбон-керамика Brembo", "emoji": "🛑", "max_level": 5, "mult": 0.85},
    "tires":        {"name": "Слики Michelin Pilot", "emoji": "🛞", "max_level": 5, "mult": 0.65},
    "intercooler":  {"name": "Интеркулер Race", "emoji": "❄️", "max_level": 5, "mult": 0.9},
    "intake":       {"name": "Карбоновый впуск", "emoji": "🌪", "max_level": 5, "mult": 0.75},
    "downpipe":     {"name": "Спортивный Даунпайп", "emoji": "🔥", "max_level": 5, "mult": 1.05},
    "nitro":        {"name": "Закись азота (NOS)", "emoji": "⚡", "max_level": 5, "mult": 1.15},
    "ecu":          {"name": "Чип-тюнинг Stage", "emoji": "💻", "max_level": 5, "mult": 0.9},
    "body_kit":     {"name": "Аэро-обвес Black Series", "emoji": "🎨", "max_level": 5, "mult": 0.7},
}


def _b(p=0, s=0, a=0, h=0, w=0):
    return {"power_pct": p, "speed_pct": s, "accel_pct": a, "handling_pct": h, "weight_pct": w}


UPGRADE_BONUSES = {
    "engine":       [_b(5, 1), _b(10, 2), _b(16, 3), _b(22, 4), _b(30, 5)],
    "turbo":        [_b(4, 2), _b(8, 4), _b(13, 6), _b(18, 8), _b(25, 10)],
    "exhaust":      [_b(p=4, s=2), _b(p=8, s=3), _b(p=12, s=5), _b(p=16, s=7), _b(p=22, s=9)],
    "transmission": [_b(a=4, s=1), _b(a=8, s=2), _b(a=13, s=4), _b(a=18, s=6), _b(a=24, s=8)],
    "suspension":   [_b(h=5, a=1), _b(h=10, a=2), _b(h=16, a=3), _b(h=22, a=4), _b(h=30, a=5)],
    "brakes":       [_b(h=4, a=2), _b(h=8, a=4), _b(h=14, a=6), _b(h=20, a=8), _b(h=28, a=10)],
    "tires":        [_b(h=3, a=3), _b(h=6, a=5), _b(h=10, a=8), _b(h=14, a=11), _b(h=18, a=15)],
    "intercooler":  [_b(p=3, s=2), _b(p=6, s=4), _b(p=10, s=6), _b(p=14, s=8), _b(p=18, s=10)],
    "intake":       [_b(p=2, a=2), _b(p=5, a=4), _b(p=8, a=6), _b(p=12, a=8), _b(p=16, a=11)],
    "downpipe":     [_b(p=4, a=2), _b(p=8, a=4), _b(p=12, a=6), _b(p=17, a=8), _b(p=22, a=11)],
    "nitro":        [_b(a=5), _b(a=10), _b(a=16), _b(a=22), _b(a=30)],
    "ecu":          [_b(3, 2, 1), _b(6, 4, 2), _b(10, 6, 3), _b(14, 8, 4), _b(18, 11, 5)],
    "body_kit":     [_b(s=1, w=-2), _b(s=2, w=-4), _b(s=3, w=-6), _b(s=4, w=-9), _b(s=6, w=-12)],
}

ACHIEVEMENTS_DEF = {
    "first_race":    {"name": "Первый заезд", "emoji": "🏁", "description": "Проведи первую гонку"},
    "first_win":     {"name": "Первая победа", "emoji": "🥇", "description": "Выиграй гонку"},
    "ten_wins":      {"name": "Десять побед", "emoji": "🔥", "description": "Выиграй 10 гонок"},
    "fifty_wins":    {"name": "Полтинник", "emoji": "💪", "description": "Выиграй 50 гонок"},
    "hundred_wins":  {"name": "Сотня", "emoji": "💯", "description": "Выиграй 100 гонок"},
    "buy_first_car": {"name": "Первая покупка", "emoji": "🛒", "description": "Купи машину в салоне"},
    "five_cars":     {"name": "Коллекционер", "emoji": "🚗", "description": "Собери 5 машин"},
    "ten_cars":      {"name": "Автопарк", "emoji": "🏢", "description": "Собери 10 машин"},
    "class_s_car":   {"name": "Мастер класса S", "emoji": "⭐", "description": "Купи машину класса S"},
    "class_ss_car":  {"name": "Легенда", "emoji": "💎", "description": "Купи машину класса SS"},
    "amg_one_owner": {"name": "Владелец ONE", "emoji": "👑", "description": "Получи Mercedes-AMG ONE"},
    "level_10":      {"name": "Опытный", "emoji": "📈", "description": "Достигни 10 уровня"},
    "level_25":      {"name": "Ветеран", "emoji": "🎖", "description": "Достигни 25 уровня"},
    "millionaire":   {"name": "Казначей", "emoji": "💰", "description": "Накопи 10 000 монет"},
    "streak_7":      {"name": "Недельный стрик", "emoji": "📅", "description": "Заходи 7 дней подряд"},
    "pvp_win":       {"name": "Дуэлянт", "emoji": "⚔️", "description": "Выиграй PvP-дуэль"},
    "ghost_slayer":  {"name": "Охотник на призраков", "emoji": "👻", "description": "Обгони Призрака на AMG ONE"},
    "full_tune":     {"name": "Полный фарш", "emoji": "🛠", "description": "Прокачай всё на машине до MAX"},
}

STREET_OPPONENTS = [
    {"name": "Сосед по району", "car_key": "c180", "difficulty": "easy", "bonus_mult": 0.5,
     "upgrades": {}},
    {"name": "Новичок", "car_key": "a35", "difficulty": "easy", "bonus_mult": 0.8,
     "upgrades": {}},
    {"name": "Стритрейсер", "car_key": "c63", "difficulty": "medium", "bonus_mult": 1.0,
     "upgrades": {"engine": 1, "tires": 1}},
    {"name": "Уличный гонщик", "car_key": "e63s", "difficulty": "medium", "bonus_mult": 1.2,
     "upgrades": {"engine": 2, "turbo": 1, "tires": 2}},
    {"name": "Дрифтер", "car_key": "amg_gt", "difficulty": "hard", "bonus_mult": 1.5,
     "upgrades": {"engine": 2, "turbo": 2, "suspension": 3, "tires": 3}},
    {"name": "Король улиц", "car_key": "gt63s", "difficulty": "hard", "bonus_mult": 1.8,
     "upgrades": {"engine": 3, "turbo": 3, "suspension": 3, "tires": 3, "nitro": 3, "ecu": 2}},
    {"name": "Призрак", "car_key": "amg_one", "difficulty": "extreme", "bonus_mult": 2.5,
     "upgrades": {k: 4 for k in UPGRADE_DEFS}},
]
DIFFICULTY_EMOJI = {"easy": "🟢", "medium": "🟡", "hard": "🔴", "extreme": "💀"}

DAILY_REWARDS = [
    {"coins": 15, "xp": 50, "energy": 0, "bonus": None},
    {"coins": 20, "xp": 75, "energy": 0, "bonus": None},
    {"coins": 30, "xp": 100, "energy": 2, "bonus": "⚡ +2 энергии"},
    {"coins": 40, "xp": 150, "energy": 0, "bonus": None},
    {"coins": 50, "xp": 200, "energy": 5, "bonus": "⚡ +5 энергии"},
    {"coins": 65, "xp": 300, "energy": 0, "bonus": None},
    {"coins": 80, "xp": 500, "energy": 0, "bonus": "🎁 Бесплатный кейс"},
]

# Магазин за монеты 🪙
COIN_SHOP = {
    "energy_refill": {"name": "⚡ Полная энергия", "price": 60, "desc": "Восстанавливает энергию до максимума"},
    "energy_plus":   {"name": "🔋 +1 к макс. энергии", "price": 400, "desc": "Навсегда +1 к максимуму (до 25)"},
    "case_basic":    {"name": "📦 Обычный кейс", "price": 100, "desc": "Монеты, XP или машина класса D–B"},
    "case_elite":    {"name": "🎁 Элитный кейс", "price": 350, "desc": "Крупные призы и шанс на класс A–SS"},
    "case_legendary":{"name": "👑 Легендарный ларец ONE", "price": 750, "desc": "Шанс выбить гиперкар AMG ONE и тысячи монет"},
    "xp_boost":      {"name": "📈 +500 XP", "price": 120, "desc": "Мгновенно +500 опыта"},
    "insurance":     {"name": "🛡 Страховка AMG", "price": 150, "desc": "Защищает машину от аварии (спасет 1 раз)"},
    "chat_nitro":    {"name": "⚡ Нитро для чата", "price": 80, "desc": "+10% скорости во всех командных гонках чата на 24ч"},
    "gold_wrap":     {"name": "✨ Золотой винил", "price": 250, "desc": "+15% к авторитету и наградам в чате"},
}

# Магазин Звёзд Telegram (Stars ⭐️ / XTR)
STARS_PACKS = {
    "energy_nitro": {
        "id": "energy_nitro",
        "title": "⚡ Полный бак + Нитро",
        "stars": 15,
        "emoji": "⚡",
        "badge": "Экспресс ⚡",
        "short_desc": "Энергия 10/10 + Нитро на 2 часа",
        "desc": "Мгновенное пополнение энергии до максимума + эффект «Нитро-ускоритель» (+15% к скорости) на 2 часа во всех заездах!",
        "bonus_coins": 0,
        "bonus_money": 5000,
        "bonus_xp": 100,
        "refill_energy": True,
        "nitro_hours": 2,
    },
    "coins_150": {
        "id": "coins_150",
        "title": "🪙 Мешочек монет (150 🪙)",
        "stars": 25,
        "emoji": "🪙",
        "badge": "Быстрый старт",
        "short_desc": "+150 монет 🪙 прямо на баланс",
        "desc": "Быстрое пополнение баланса: 150 монет 🪙 на покупку тачек, тюнинг деталей и ставки в дуэлях!",
        "bonus_coins": 150,
        "bonus_money": 15000,
        "bonus_xp": 300,
    },
    "case_star": {
        "id": "case_star",
        "title": "🧰 Звёздный кейс AMG",
        "stars": 39,
        "emoji": "🧰",
        "badge": "Азарт 📦",
        "short_desc": "35 монет 🪙 + 1000 XP + шанс на спорткар S-класса",
        "desc": "Премиальный ларец: 35 монет, 1 000 XP, $30 000 на прокачку и шанс 25% выбить спорткар AMG GT S!",
        "bonus_coins": 35,
        "bonus_money": 30000,
        "bonus_xp": 1000,
        "case_drop": True,
    },
    "coins_450": {
        "id": "coins_450",
        "title": "🪙 Стек стритрейсера (450 🪙)",
        "stars": 69,
        "emoji": "💰",
        "badge": "Выгодно +25%",
        "short_desc": "+450 монет 🪙 + Нитро на 24 часа",
        "desc": "Солидный куш: 450 монет 🪙 на любые цели, $50 000 на Stage-прокачку и суточное Нитро-ускорение (+15% скорости)!",
        "bonus_coins": 450,
        "bonus_money": 50000,
        "bonus_xp": 1200,
        "nitro_hours": 24,
    },
    "vip_7": {
        "id": "vip_7",
        "title": "👑 VIP-Гонщик на 7 дней",
        "stars": 79,
        "emoji": "👑",
        "badge": "Хит продаж 🔥",
        "short_desc": "Корона в нике, бак энергии 13, 60 монет 🪙",
        "desc": "Золотой VIP-статус на 7 дней:\n• Корона 👑 возле ника в рейтингах и чатах\n• Постоянный бак 13 энергии вместо 10\n• 60 монет 🪙 и $60 000 на тюнинг\n• Эксклюзивная переливающаяся покраска\n• Бесплатный ежедневный спин колеса фортуны!",
        "bonus_coins": 60,
        "bonus_money": 60000,
        "bonus_xp": 2000,
        "vip_days": 7,
        "energy_bonus": 3,
    },
    "coins_1200": {
        "id": "coins_1200",
        "title": "🪙 Сейф авторитета (1 200 🪙)",
        "stars": 149,
        "emoji": "💎",
        "badge": "Супер-выгода +40%",
        "short_desc": "+1 200 монет 🪙 + Золотой винил ✨",
        "desc": "Крупный запас капитала: 1 200 монет 🪙 (хватит сразу на Mercedes-AMG C63 S!), золотой винил ✨ на любое авто и $150 000 на запчасти!",
        "bonus_coins": 1200,
        "bonus_money": 150000,
        "bonus_xp": 3500,
        "gold_wrap": True,
    },
    "car_gts_star": {
        "id": "car_gts_star",
        "title": "🌟 AMG GT S «Star Edition»",
        "stars": 179,
        "emoji": "🌟",
        "badge": "Эксклюзив 🏎",
        "short_desc": "Эксклюзивный спорткар S-класса + 150 монет + 3 страховки",
        "desc": "Лимитированный спорткар Mercedes-AMG GT S «Star Edition» (540 л.с., класс S) в звёздном матовом обвесе, 150 монет 🪙, 3 страховки от аварий и $120 000 на тюнинг!",
        "bonus_coins": 150,
        "bonus_money": 120000,
        "bonus_xp": 4000,
        "give_car": "amg_gts_star",
        "insurance": 3,
    },
    "coins_3000": {
        "id": "coins_3000",
        "title": "🏦 Банк AMG (3 000 🪙)",
        "stars": 299,
        "emoji": "🏦",
        "badge": "Максимум монет 🚀",
        "short_desc": "+3 000 монет 🪙 + VIP на 14 дней!",
        "desc": "Огромный банк: 3 000 монет 🪙 (хватит на суперкар E63 S!), 14 дней VIP-статуса (корона 👑 + бак 14) и $300 000 на максимальный Stage!",
        "bonus_coins": 3000,
        "bonus_money": 300000,
        "bonus_xp": 7500,
        "vip_days": 14,
        "energy_bonus": 4,
    },
    "elite_30": {
        "id": "elite_30",
        "title": "👑 Спонсор AMG Elite (30 дней)",
        "stars": 499,
        "emoji": "👑",
        "badge": "Королевский VIP 💎",
        "short_desc": "VIP 30 дней + Hypercar Black Series + 1 000 монет",
        "desc": "Максимальный статус спонсора на 30 дней:\n• VIP-корона 👑 и бак энергии 15 на целый месяц\n• Легендарный гиперкар Mercedes-AMG GT Black Series «Star Edition» (740 л.с., класс SS)\n• 1 000 монет 🪙 и $500 000 на тюнинг\n• Постоянная страховка от поломок на 30 дней!",
        "bonus_coins": 1000,
        "bonus_money": 500000,
        "bonus_xp": 10000,
        "vip_days": 30,
        "energy_bonus": 5,
        "give_car": "gt_bs_star",
        "insurance": 10,
    },
}



CASES = {
    "case_basic": {
        "name": "📦 Базовый сундук",
        "price": 100,
        "emoji": "📦",
        "desc": "Монеты, опыт и шанс выбить машины классов D–B (A35, CLA 45 S, C63 S).",
    },
    "case_elite": {
        "name": "🎁 Элитный кейс AMG",
        "price": 350,
        "emoji": "🎁",
        "desc": "Солидный куш монет, много XP и суперкары E63 S, AMG GT, GT R, Black Series.",
    },
    "case_legendary": {
        "name": "👑 Легендарный ларец ONE",
        "price": 750,
        "emoji": "👑",
        "desc": "До 2500 монет, 3000 XP и шанс забрать гиперкары SS и сам Mercedes-AMG ONE!",
    },
}

# AMG GIFs (проверенные прямые GIF с автомобилями Mercedes-AMG)
AMG_GIFS = {
    "welcome": "https://media.tenor.com/0C8klDvuopYAAAAM/mercedes-benz-mercedes.gif",
    "win": "https://media.tenor.com/3rpwuiDLFK0AAAAM/forza-horizon-5-mercedes-amg-gt-r.gif",
    "crash": "https://media.tenor.com/FusLX8DRHjUAAAAM/mercedes-clr-mercedes-benz-clr.gif",
    "boss": "https://media.tenor.com/SMfTQh_L4ykAAAAM/forza-horizon4-mercedes-benz-g65amg.gif",
    "chest": "https://media.tenor.com/V3DWk6ZLvzgAAAAM/mercedes-amg-amg.gif",
    "boss_rage": "https://media.tenor.com/Iqr0XGqDUGcAAAAM/forza-horizon5-mercedes-benz-g60amg.gif",
    "race": "https://media.tenor.com/dsQKgHxp1koAAAAM/forza-horizon-5-mercedes-amg-gt3.gif",
    "burnout": "https://media.tenor.com/zK14d9A9JcgAAAAM/mercedes-c63-drifting.gif",
    "drift": "https://media.tenor.com/cOd5d2YhhggAAAAM/opris-handsome-mercedes-drift.gif",
    "garage": "https://media.tenor.com/iibDzEi-aREAAAAM/mercedes-amg-gt-63-cars.gif",
    "heist": "https://media.tenor.com/bE1p6fxp93QAAAAM/cls63-cls.gif",
    "wheel": "https://media.tenor.com/UJGeQmzsja0AAAAM/forza-horizon-5-mercedes-amg-gt-black-series.gif",
    "drag": "https://media.tenor.com/A4a-ejXthrwAAAAM/forza-horizon-4-mercedes-amg-c-63-s-coupe.gif",
    "police": "https://media.tenor.com/lOcnIOQKtVUAAAAM/makhachkalaracing-02reg.gif",
    "autobahn": "https://media.tenor.com/F0XjiYxCuPAAAAAM/forza-horizon5-mercedes-amg-project-one.gif",
}

# Расширенный ростер Рейдовых Боссов чата
BOSS_ROSTER = [
    {
        "id": "brabus_g63",
        "name": "Барон на броне-Гелике Brabus 900",
        "car_key": "g63",
        "hp": 4500,
        "ability": "🛡 Бронебойный таран и дымовая завеса",
        "phrase": "«Мой V8 перемелет ваши легковушки в щебень!»",
        "coins_pool": 300,
        "loot": "📦 Элитный кейс запчастей"
    },
    {
        "id": "amg_one_ghost",
        "name": "Призрак Нордшляйфе на AMG ONE",
        "car_key": "amg_one",
        "hp": 6500,
        "ability": "⚡ Аэродинамический срыв F1 и уворот от тарана",
        "phrase": "«1063 лошадиные силы не оставляют вам и шанса!»",
        "coins_pool": 600,
        "loot": "👑 Королевский трофей AMG ONE"
    },
    {
        "id": "devil_gt_bs",
        "name": "Ночной Дьявол на GT Black Series",
        "car_key": "gt_bs",
        "hp": 5500,
        "ability": "🔥 Выброс пламени из выхлопа и ярость V8",
        "phrase": "«Посмотрим, чей битурбо сгорит первым в этой ночи!»",
        "coins_pool": 450,
        "loot": "🎁 Кейс тюнинга и нитро"
    },
    {
        "id": "syndicate_gt63s",
        "name": "Глава синдиката на GT 63 S E-Performance",
        "car_key": "gt63se",
        "hp": 5000,
        "ability": "🔋 Электро-импульс 843 л.с. и регенерация бампера",
        "phrase": "«Гибридная мощь сотрёт вас с автобана!»",
        "coins_pool": 400,
        "loot": "⚡ Запас супер-энергии"
    }
]

# Колесо Фортуны AMG (призы и вероятности)
WHEEL_PRIZES = [
    {"type": "coins", "val": 10, "text": "🪙 10 монет AMG", "weight": 25},
    {"type": "coins", "val": 25, "text": "🪙 Куш: 25 монет!", "weight": 14},
    {"type": "coins", "val": 15, "text": "🪙 15 золотых монет AMG", "weight": 20},
    {"type": "coins", "val": 50, "text": "🪙 ДЖЕКПОТ: 50 монет!", "weight": 4},
    {"type": "energy", "val": 4, "text": "⚡ +4 единиц энергии", "weight": 18},
    {"type": "xp", "val": 300, "text": "📈 +300 очков опыта гонщика", "weight": 14},
    {"type": "fine", "val": 8, "text": "👮 Штраф ДПС за тонировку (-8 🪙) 😅", "weight": 5},
]

# Сценарии приключений и похождений по автобану
ADVENTURE_SCENARIOS = [
    {
        "title": "Нелегальная сходка на подземном паркинге",
        "desc": "Вы въезжаете на закрытую подземную парковку в деловом квартале. Густой дым от резины, вокруг ревут V8 Biturbo, толпа стритрейсеров окружила заряженный C63.",
        "choices": [
            {
                "id": "dyno",
                "text": "📊 Заехать на диностенд и показать мощь",
                "req_stat": "power",
                "success_text": "Диностенд выдал запредельные показатели! Толпа в восторге, вам скинулись на призовой фонд!",
                "win_coins": 10, "win_xp": 150
            },
            {
                "id": "drag402",
                "text": "🚦 Принять вызов на быстрый спринт по рампе",
                "req_stat": "acceleration",
                "success_text": "Чистый старт на лаунч-контроле! Вы улетели вперёд, оставив соперника глотать пыль!",
                "win_coins": 14, "win_xp": 200
            },
            {
                "id": "mechanic",
                "text": "🔧 Подойти к подпольному механику AMG",
                "req_stat": "any",
                "success_text": "Механик уважительно оценил ваше авто и бесплатно подкрутил прошивку ECU!",
                "win_coins": 8, "win_xp": 250
            }
        ]
    },
    {
        "title": "Ночной автобан A2 без ограничений",
        "desc": "Стрелка спидометра перевалила за 250 км/ч. В зеркале заднего вида внезапно вспыхивают матричные фары — вас догоняет колонна черных суперкаров!",
        "choices": [
            {
                "id": "flatout",
                "text": "💨 Педаль в пол: проверить максималку",
                "req_stat": "speed",
                "success_text": "Ваш AMG показал свой максимум! Колонна осталась далеко позади, вы король трассы!",
                "win_coins": 15, "win_xp": 220
            },
            {
                "id": "corners",
                "text": "↩️ Свернуть на извилистую развязку",
                "req_stat": "handling",
                "success_text": "Филигранное прохождение шпилек! Шасси отработало идеально, вам начислили очки стиля!",
                "win_coins": 12, "win_xp": 180
            }
        ]
    },
    {
        "title": "Полицейская засада и облава",
        "desc": "На съезде с моста включились сирены! Перехватчики дорожной полиции на броневиках блокируют полосы!",
        "choices": [
            {
                "id": "escape_tunnel",
                "text": "🚇 Срезать через ремонтный тоннель",
                "req_stat": "handling",
                "success_text": "Вы пролетели в сантиметрах от отбойников и оторвались в темноте тоннеля!",
                "win_coins": 16, "win_xp": 300
            },
            {
                "id": "nitro_blast",
                "text": "🔥 Врубить полный баллон нитро!",
                "req_stat": "power",
                "success_text": "Взрыв ускорения вжал вас в сиденье! Радары копов просто зашкалили!",
                "win_coins": 18, "win_xp": 280
            }
        ]
    }
]

CASE_DROPS = {
    "case_basic": [  # (вес, тип, значение)
        (45, "coins", 15), (25, "coins", 35), (20, "xp", 300),
        (7, "car", "a35"), (2.5, "car", "cla45"), (0.5, "coins", 100),
    ],
    "case_elite": [
        (40, "coins", 60), (20, "coins", 120), (15, "xp", 1000),
        (12, "car", "e63s"), (8, "car", "amg_gt"), (4, "car", "gt63s"),
        (1, "car", "amg_gtr"),
    ],
    "case_legendary": [
        (35, "coins", 150), (20, "coins", 300), (15, "xp", 2000),
        (14, "car", "gt63se"), (9, "car", "amg_gtr"), (5, "car", "gt_bs"),
        (2, "car", "amg_one"),
    ],
}

MAX_ENERGY_CAP = 25
ENERGY_REGEN_MINUTES = 10


def get_cars_by_class(cls: str) -> list:
    return sorted([(k, v) for k, v in CAR_CATALOG.items() if v["cls"] == cls], key=lambda x: x[1]["price"])


def is_weakest_in_tier(car_key: str) -> bool:
    """Самая слабая (начальная по цене) машина в каждом тире не может разбиться."""
    car = CAR_CATALOG.get(car_key)
    if not car:
        return False
    cls_cars = get_cars_by_class(car["cls"])
    if not cls_cars:
        return False
    return cls_cars[0][0] == car_key


def get_upgrade_cost(car_price: int, upgrade_type: str, current_level: int) -> int:
    base = car_price if car_price > 0 else 200
    mult = UPGRADE_DEFS[upgrade_type]["mult"]
    return max(10, int(base * 0.05 * (current_level + 1) * mult))


def upgrade_investment(car_data: dict, player_car: dict) -> int:
    total = 0
    for key in UPGRADE_DEFS:
        for lvl in range(player_car.get(f"{key}_level", 0)):
            total += get_upgrade_cost(car_data["price"], key, lvl)
    return total


def get_sell_price(car_data: dict, player_car: dict) -> int:
    return int(car_data["price"] * 0.6 + upgrade_investment(car_data, player_car) * 0.4)


def xp_for_level(level: int) -> int:
    """
    Прогрессивная RPG кривая:
    Уровень 1 -> 2: 50 XP (всего 1-2 гонки)
    Уровень 2 -> 3: 100 XP
    Уровень 5: ~350 XP
    Уровень 10: ~1200 XP
    Уровень 20+: настоящий хардкор
    """
    if level <= 1:
        return 50
    elif level == 2:
        return 100
    elif level <= 5:
        return int(80 * (level ** 1.35))
    elif level <= 15:
        return int(110 * (level ** 1.65))
    else:
        return int(140 * (level ** 1.85))



def fmt(n) -> str:
    return f"{int(n):,}".replace(",", " ")

