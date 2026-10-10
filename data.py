"""Игровые данные AMG Racing."""

CAR_CLASSES = ["D", "C", "B", "A", "S", "SS"]
CAR_CLASS_NAMES = {"D": "Начальный", "C": "Любитель", "B": "Продвинутый",
                   "A": "Эксперт", "S": "Мастер", "SS": "Легенда"}
CAR_CLASS_EMOJIS = {"D": "🟢", "C": "🔵", "B": "🟡", "A": "🟠", "S": "⭐", "SS": "💎"}

# Палитра фирменных цветов Mercedes-AMG
CAR_COLORS = {
    "red":    {"name": "Красный (Designo Cardinal)", "emoji": "🔴", "price": 15000},
    "yellow": {"name": "Жёлтый (Solarbeam Yellow)",   "emoji": "🟡", "price": 20000},
    "green":  {"name": "Зелёный (Green Hell Magno)",  "emoji": "🟢", "price": 30000},
    "blue":   {"name": "Синий (Brilliant Blue)",      "emoji": "🔵", "price": 20000},
    "purple": {"name": "Фиолетовый (Mystic Purple)",  "emoji": "🟣", "price": 25000},
    "orange": {"name": "Оранжевый (Copper Orange)",   "emoji": "🟠", "price": 25000},
    "black":  {"name": "Чёрный (Obsidian Black)",     "emoji": "⚫", "price": 15000},
    "white":  {"name": "Белый (Polar White)",         "emoji": "⚪", "price": 10000},
    "brown":  {"name": "Бронзовый (Citrine Brown)",   "emoji": "🟤", "price": 18000},
    "grey":   {"name": "Матовый серый (Selenite Magno)", "emoji": "🔘", "price": 22000},
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
    "a35":     _car("Mercedes-AMG A35", "D", "🏎", 30000, 1, 306, 250, 4.7, 60, 1555, "Заряженный хэтч с полным приводом."),
    "c43":     _car("Mercedes-AMG C43", "C", "🏎", 55000, 2, 390, 250, 4.7, 65, 1660, "Спокойный снаружи, злой внутри."),
    "cla45":   _car("Mercedes-AMG CLA 45 S", "C", "🏎", 65000, 3, 421, 270, 4.0, 68, 1630, "Самый мощный серийный 2.0 турбо в мире."),
    "e53":     _car("Mercedes-AMG E53", "B", "🏎", 120000, 4, 435, 270, 4.4, 70, 1880, "Гибридный бизнес-снаряд."),
    "c63":     _car("Mercedes-AMG C63 S", "B", "🏎", 150000, 5, 510, 290, 3.9, 72, 1740, "Битурбо V8 и легендарный рёв."),
    "g63":     _car("Mercedes-AMG G63", "B", "🚙", 180000, 5, 585, 220, 4.5, 45, 2560, "Гелик. Объяснения не нужны."),
    "cls53":   _car("Mercedes-AMG CLS 53", "A", "🏎", 280000, 7, 435, 270, 4.3, 73, 1870, "Четырёхдверное купе с характером."),
    "e63s":    _car("Mercedes-AMG E63 S", "A", "🏎", 300000, 8, 612, 300, 3.4, 75, 1960, "Седан, который рвёт суперкары."),
    "gt53":    _car("Mercedes-AMG GT 53", "A", "🏎", 320000, 8, 435, 285, 4.1, 76, 1910, "Комфорт GT и скорость AMG."),
    "gle63s":  _car("Mercedes-AMG GLE 63 S", "A", "🚙", 350000, 9, 612, 280, 3.8, 55, 2370, "Кроссовер-ракета."),
    "s63":     _car("Mercedes-AMG S63", "A", "🏎", 400000, 10, 612, 290, 3.5, 68, 2150, "Роскошь на скорости 290."),
    "amg_gt":  _car("Mercedes-AMG GT", "S", "🏎", 500000, 12, 585, 312, 3.6, 82, 1615, "Длинный капот, короткая корма, чистый драйв."),
    "sl63":    _car("Mercedes-AMG SL 63", "S", "🏎", 550000, 12, 585, 315, 3.6, 80, 1790, "Родстер для тех, кто любит ветер."),
    "amg_gts": _car("Mercedes-AMG GT S", "S", "🏎", 600000, 13, 522, 310, 3.7, 84, 1645, "Острая версия GT."),
    "gt63s":   _car("Mercedes-AMG GT 63 S", "S", "🏎", 700000, 15, 639, 315, 3.2, 78, 2100, "Четыре двери, 639 сил."),
    "gt63se":  _car("Mercedes-AMG GT 63 S E Performance", "S", "⚡", 850000, 16, 843, 316, 2.9, 80, 2280, "Гибридный монстр на 843 силы."),
    "amg_gtr": _car("Mercedes-AMG GT R", "SS", "🏎", 1000000, 18, 585, 318, 3.6, 90, 1555, "Зелёный ад. Зверь с Нюрбургринга."),
    "gtr_pro": _car("Mercedes-AMG GT R PRO", "SS", "🏎", 1200000, 20, 585, 318, 3.6, 95, 1500, "Трековая версия GT R."),
    "gt_bs":   _car("Mercedes-AMG GT Black Series", "SS", "🏎", 1500000, 22, 730, 325, 3.2, 92, 1435, "Рекордсмен Нордшляйфе."),
    "amg_one": _car("Mercedes-AMG ONE", "SS", "👑", 3000000, 25, 1063, 352, 2.9, 95, 1695, "Болид Формулы-1 с номерами."),
}

UPGRADE_DEFS = {
    "engine":     {"name": "Двигатель", "emoji": "🔧", "max_level": 5, "mult": 1.0},
    "turbo":      {"name": "Турбина", "emoji": "🌀", "max_level": 5, "mult": 1.2},
    "suspension": {"name": "Подвеска", "emoji": "🔩", "max_level": 5, "mult": 0.8},
    "tires":      {"name": "Шины", "emoji": "🛞", "max_level": 5, "mult": 0.6},
    "nitro":      {"name": "Закись азота", "emoji": "💨", "max_level": 5, "mult": 1.1},
    "ecu":        {"name": "Чип-тюнинг", "emoji": "💻", "max_level": 5, "mult": 0.9},
    "body_kit":   {"name": "Обвес", "emoji": "🎨", "max_level": 5, "mult": 0.7},
}


def _b(p=0, s=0, a=0, h=0, w=0):
    return {"power_pct": p, "speed_pct": s, "accel_pct": a, "handling_pct": h, "weight_pct": w}


UPGRADE_BONUSES = {
    "engine":     [_b(5, 1), _b(10, 2), _b(16, 3), _b(22, 4), _b(30, 5)],
    "turbo":      [_b(4, 2), _b(8, 4), _b(13, 6), _b(18, 8), _b(25, 10)],
    "suspension": [_b(h=5, a=1), _b(h=10, a=2), _b(h=16, a=3), _b(h=22, a=4), _b(h=30, a=5)],
    "tires":      [_b(h=3, a=3), _b(h=6, a=5), _b(h=10, a=8), _b(h=14, a=11), _b(h=18, a=15)],
    "nitro":      [_b(a=5), _b(a=10), _b(a=16), _b(a=22), _b(a=30)],
    "ecu":        [_b(3, 2, 1), _b(6, 4, 2), _b(10, 6, 3), _b(14, 8, 4), _b(18, 11, 5)],
    "body_kit":   [_b(s=1, w=-2), _b(s=2, w=-4), _b(s=3, w=-6), _b(s=4, w=-9), _b(s=6, w=-12)],
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
    "millionaire":   {"name": "Миллионер", "emoji": "💰", "description": "Накопи $1,000,000"},
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
    {"money": 1000, "xp": 50, "coins": 20, "energy": 0, "bonus": None},
    {"money": 1500, "xp": 75, "coins": 25, "energy": 0, "bonus": None},
    {"money": 2500, "xp": 100, "coins": 30, "energy": 2, "bonus": "⚡ +2 энергии"},
    {"money": 3500, "xp": 150, "coins": 35, "energy": 0, "bonus": None},
    {"money": 5000, "xp": 200, "coins": 40, "energy": 5, "bonus": "⚡ +5 энергии"},
    {"money": 7500, "xp": 300, "coins": 50, "energy": 0, "bonus": None},
    {"money": 15000, "xp": 500, "coins": 80, "energy": 0, "bonus": "🎁 Бесплатный кейс"},
]

# Магазин за монеты 🪙
COIN_SHOP = {
    "energy_refill": {"name": "⚡ Полная энергия", "price": 60, "desc": "Восстанавливает энергию до максимума"},
    "energy_plus":   {"name": "🔋 +1 к макс. энергии", "price": 400, "desc": "Навсегда +1 к максимуму (до 20)"},
    "case_basic":    {"name": "📦 Обычный кейс", "price": 100, "desc": "Деньги, XP или машина класса D–B"},
    "case_elite":    {"name": "🎁 Элитный кейс", "price": 350, "desc": "Крупные призы и шанс на класс A–SS"},
    "xp_boost":      {"name": "📈 +500 XP", "price": 120, "desc": "Мгновенно +500 опыта"},
    "insurance":     {"name": "🛡 Страховка AMG", "price": 150, "desc": "Защищает машину от аварии (спасет 1 раз)"},
    "chat_nitro":    {"name": "⚡ Нитро для чата", "price": 80, "desc": "+10% скорости во всех командных гонках чата на 24ч"},
    "gold_wrap":     {"name": "✨ Золотой винил", "price": 250, "desc": "+15% к авторитету и наградам в чате"},
}

# AMG GIFs (проверенные прямые ссылки Giphy)
AMG_GIFS = {
    "welcome": "https://media.giphy.com/media/xUOrwihVn9p8HhU3iU/giphy.gif",
    "win": "https://media.giphy.com/media/3o7TKMt1VVNkHV2PaE/giphy.gif",
    "crash": "https://media.giphy.com/media/26n6WywStCAfdHUM8/giphy.gif",
    "boss": "https://media.giphy.com/media/l41JGlWa1xOjJSsV2/giphy.gif",
    "boss_rage": "https://media.giphy.com/media/l4pTfSeH65zpQW7yo/giphy.gif",
    "race": "https://media.giphy.com/media/MDJ9IbxxvDUQM/giphy.gif",
    "burnout": "https://media.giphy.com/media/3o7TKsWZBdg99GS956/giphy.gif",
    "drift": "https://media.giphy.com/media/l0HlHJGHe3yAMhdQY/giphy.gif",
    "garage": "https://media.giphy.com/media/xT9IgzoKnwFNmISR8I/giphy.gif",
    "heist": "https://media.giphy.com/media/3ohhwkIX215Zg8k59u/giphy.gif",
    "wheel": "https://media.giphy.com/media/26AHONQ79FdWZhAI0/giphy.gif",
    "drag": "https://media.giphy.com/media/3o7TKUM3IgJBX2as9O/giphy.gif",
    "police": "https://media.giphy.com/media/ryMHjDHZtfKoggE436/giphy.gif",
    "autobahn": "https://media.giphy.com/media/d8isjk1UBP755nnld4/giphy.gif",
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
        "coins_pool": 250,
        "money_pool": 100000,
        "loot": "📦 Элитный кейс запчастей"
    },
    {
        "id": "amg_one_ghost",
        "name": "Призрак Нордшляйфе на AMG ONE",
        "car_key": "amg_one",
        "hp": 6500,
        "ability": "⚡ Аэродинамический срыв F1 и уворот от тарана",
        "phrase": "«1063 лошадиные силы не оставляют вам и шанса!»",
        "coins_pool": 400,
        "money_pool": 250000,
        "loot": "👑 Королевский трофей AMG ONE"
    },
    {
        "id": "devil_gt_bs",
        "name": "Ночной Дьявол на GT Black Series",
        "car_key": "gt_bs",
        "hp": 5500,
        "ability": "🔥 Выброс пламени из выхлопа и ярость V8",
        "phrase": "«Посмотрим, чей битурбо сгорит первым в этой ночи!»",
        "coins_pool": 320,
        "money_pool": 180000,
        "loot": "🎁 Кейс тюнинга и нитро"
    },
    {
        "id": "syndicate_gt63s",
        "name": "Глава синдиката на GT 63 S E-Performance",
        "car_key": "gt63se",
        "hp": 5000,
        "ability": "🔋 Электро-импульс 843 л.с. и регенерация бампера",
        "phrase": "«Гибридная мощь сотрёт вас с автобана!»",
        "coins_pool": 280,
        "money_pool": 140000,
        "loot": "⚡ Запас супер-энергии"
    }
]

# Колесо Фортуны AMG (призы и вероятности)
WHEEL_PRIZES = [
    {"type": "money", "val": 15000, "text": "💵 $15,000 наличных", "weight": 25},
    {"type": "money", "val": 50000, "text": "💵 Крупный куш: $50,000!", "weight": 12},
    {"type": "coins", "val": 30, "text": "🪙 30 золотых монет AMG", "weight": 20},
    {"type": "coins", "val": 100, "text": "🪙 ДЖЕКПОТ: 100 золотых монет!", "weight": 5},
    {"type": "energy", "val": 5, "text": "⚡ +5 единиц энергии", "weight": 18},
    {"type": "xp", "val": 400, "text": "📈 +400 очков опыта гонщика", "weight": 15},
    {"type": "fine", "val": 3000, "text": "👮 Штраф ДПС за тонировку (-$3,000) 😅", "weight": 5},
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
                "win_money": 25000, "win_coins": 20, "win_xp": 150
            },
            {
                "id": "drag402",
                "text": "🚦 Принять вызов на быстрый спринт по рампе",
                "req_stat": "acceleration",
                "success_text": "Чистый старт на лаунч-контроле! Вы улетели вперёд, оставив соперника глотать пыль!",
                "win_money": 35000, "win_coins": 25, "win_xp": 200
            },
            {
                "id": "mechanic",
                "text": "🔧 Подойти к подпольному механику AMG",
                "req_stat": "any",
                "success_text": "Механик уважительно оценил ваше авто и бесплатно подкрутил прошивку ECU!",
                "win_money": 10000, "win_coins": 15, "win_xp": 250
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
                "win_money": 40000, "win_coins": 30, "win_xp": 220
            },
            {
                "id": "corners",
                "text": "↩️ Свернуть на извилистую развязку",
                "req_stat": "handling",
                "success_text": "Филигранное прохождение шпилек! Шасси отработало идеально, вам начислили очки стиля!",
                "win_money": 30000, "win_coins": 20, "win_xp": 180
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
                "win_money": 45000, "win_coins": 35, "win_xp": 300
            },
            {
                "id": "nitro_blast",
                "text": "🔥 Врубить полный баллон нитро!",
                "req_stat": "power",
                "success_text": "Взрыв ускорения вжал вас в сиденье! Радары копов просто зашкалили!",
                "win_money": 50000, "win_coins": 40, "win_xp": 280
            }
        ]
    }
]

CASE_DROPS = {
    "case_basic": [  # (вес, тип, значение)
        (40, "money", 5000), (25, "money", 15000), (20, "xp", 300),
        (8, "car", "a35"), (4, "car", "cla45"), (2, "car", "c63"), (1, "money", 100000),
    ],
    "case_elite": [
        (35, "money", 50000), (20, "money", 120000), (15, "xp", 1500),
        (12, "car", "e63s"), (8, "car", "amg_gt"), (5, "car", "gt63s"),
        (3, "car", "amg_gtr"), (1.5, "car", "gt_bs"), (0.5, "car", "amg_one"),
    ],
}

MAX_ENERGY_CAP = 20
ENERGY_REGEN_MINUTES = 20


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
    base = car_price if car_price > 0 else 20000
    mult = UPGRADE_DEFS[upgrade_type]["mult"]
    return max(1000, int(base * 0.05 * (current_level + 1) * mult))


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

