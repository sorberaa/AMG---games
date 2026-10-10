"""Inline-клавиатуры."""
from aiogram.types import InlineKeyboardButton as Btn, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from data import (CAR_CATALOG, CAR_CLASSES, CAR_CLASS_EMOJIS, CAR_CLASS_NAMES, COIN_SHOP,
                  DIFFICULTY_EMOJI, STREET_OPPONENTS, UPGRADE_DEFS, fmt, get_upgrade_cost)


def back_kb(cb: str = "menu", text: str = "◀️ Назад") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[Btn(text=text, callback_data=cb)]])


def main_menu_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for text, cb in [("🚗 Гараж", "garage:0"), ("🏪 Автосалон", "shop"),
                     ("🏁 Гонка", "race"), ("🔧 Тюнинг", "tuning"),
                     ("👤 Профиль", "profile"), ("🏆 Топ", "top:wins"),
                     ("🎁 Бонус дня", "daily"), ("🪙 Магазин монет", "cshop"),
                     ("❓ Помощь", "help")]:
        b.button(text=text, callback_data=cb)
    b.adjust(2)
    return b.as_markup()


def garage_kb(cars: list, selected_id: int, page: int = 0) -> InlineKeyboardMarkup:
    per = 6
    b = InlineKeyboardBuilder()
    for c in cars[page * per:(page + 1) * per]:
        car = CAR_CATALOG.get(c["car_key"])
        if not car:
            continue
        mark = " ✅" if c["id"] == selected_id else ""
        b.row(Btn(text=f"{car['emoji']} {car['name']}{mark}", callback_data=f"car:{c['id']}"))
    nav = []
    if page > 0:
        nav.append(Btn(text="◀️", callback_data=f"garage:{page - 1}"))
    if (page + 1) * per < len(cars):
        nav.append(Btn(text="▶️", callback_data=f"garage:{page + 1}"))
    if nav:
        b.row(*nav)
    b.row(Btn(text="🏠 Меню", callback_data="menu"))
    return b.as_markup()


def car_actions_kb(car_id: int, is_selected: bool) -> InlineKeyboardMarkup:
    rows = []
    if not is_selected:
        rows.append([Btn(text="✅ Сделать основной", callback_data=f"car_select:{car_id}")])
    rows.append([Btn(text="🔧 Тюнинг", callback_data=f"tuning:{car_id}"),
                 Btn(text="💰 Продать", callback_data=f"car_sell:{car_id}")])
    rows.append([Btn(text="◀️ В гараж", callback_data="garage:0")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def sell_confirm_kb(car_id: int, price: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [Btn(text=f"✅ Продать за ${fmt(price)}", callback_data=f"car_sell_yes:{car_id}")],
        [Btn(text="❌ Отмена", callback_data=f"car:{car_id}")],
    ])


def shop_classes_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for cls in CAR_CLASSES:
        b.button(text=f"{CAR_CLASS_EMOJIS[cls]} Класс {cls} — {CAR_CLASS_NAMES[cls]}", callback_data=f"shop_class:{cls}")
    b.button(text="🏠 Меню", callback_data="menu")
    b.adjust(1)
    return b.as_markup()


def shop_list_kb(cars: list, level: int, owned: set) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for key, car in cars:
        mark = " ✅" if key in owned else (" 🔒" if level < car["level_req"] else "")
        b.button(text=f"{car['emoji']} {car['name']} — ${fmt(car['price'])}{mark}", callback_data=f"shop_car:{key}")
    b.button(text="◀️ К классам", callback_data="shop")
    b.adjust(1)
    return b.as_markup()


def buy_confirm_kb(car_key: str, cls: str, can_buy: bool) -> InlineKeyboardMarkup:
    rows = []
    if can_buy:
        rows.append([Btn(text="✅ Купить", callback_data=f"buy_yes:{car_key}")])
    rows.append([Btn(text="◀️ Назад", callback_data=f"shop_class:{cls}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def race_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [Btn(text="🏎 Уличная гонка", callback_data="race_street")],
        [Btn(text="⚔️ Создать вызов", callback_data="race_pvp")],
        [Btn(text="📋 Открытые вызовы", callback_data="race_pvp_list")],
        [Btn(text="🏠 Меню", callback_data="menu")],
    ])


def street_opponents_kb(unlocked_idx: int = 0) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for i, o in enumerate(STREET_OPPONENTS):
        car = CAR_CATALOG[o["car_key"]]
        if i <= unlocked_idx:
            b.button(text=f"{DIFFICULTY_EMOJI[o['difficulty']]} {o['name']} — {car['name']}", callback_data=f"race_street:{i}")
        else:
            b.button(text=f"🔒 {o['name']} (победи предыдущего)", callback_data=f"race_street_locked:{i}")
    b.button(text="◀️ Назад", callback_data="race")
    b.adjust(1)
    return b.as_markup()



def pvp_bet_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for amount in (0, 1000, 5000, 10000, 50000, 100000):
        b.button(text="🤝 Без ставки" if amount == 0 else f"💵 ${fmt(amount)}", callback_data=f"race_pvp_bet:{amount}")
    # Ставки на монеты 🪙 (с лимитом 1 час)
    for c_amount in (10, 25, 50, 100):
        b.button(text=f"🪙 {c_amount} монет", callback_data=f"race_coin_bet:{c_amount}")
    b.button(text="◀️ Назад", callback_data="race")
    b.adjust(2)
    return b.as_markup()


def boss_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [Btn(text="💥 ТАРАНИТЬ (-1 ⚡)", callback_data="boss:hit"),
         Btn(text="🔥 НИТРО-УДАР x2.5 (-2 ⚡)", callback_data="boss:nitro")],
        [Btn(text="📊 Статистика урона", callback_data="boss:stats"),
         Btn(text="🔄 Обновить HP", callback_data="boss:refresh")],
    ])


def wheel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [Btn(text="🎰 КРУТИТЬ РУЛЕТКУ (1 раз в сутки)", callback_data="wheel:spin")],
        [Btn(text="🏠 Главное меню", callback_data="menu")],
    ])


def adventure_choice_kb(scenario_idx: int, choices: list) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for ch_idx, ch in enumerate(choices):
        b.button(text=ch["text"], callback_data=f"adv:choice:{scenario_idx}:{ch_idx}")
    b.adjust(1)
    return b.as_markup()


def drag_ready_kb(drag_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [Btn(text="🚦 ВСТАТЬ НА СТАРТ 402м", callback_data=f"drag:join:{drag_id}")],
    ])


def drag_launch_kb(drag_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [Btn(text="🟢 ГАЗ В ПОЛ! СТАРТ! 🟢", callback_data=f"drag:launch:{drag_id}")],
    ])



def pvp_challenge_kb(race_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [Btn(text="⚔️ Принять вызов", callback_data=f"race_accept:{race_id}")],
        [Btn(text="❌ Отменить (автор)", callback_data=f"race_cancel:{race_id}")],
    ])


def pvp_list_kb(races: list) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for r in races:
        bet = f"${fmt(r['bet'])}" if r["bet"] else "без ставки"
        b.button(text=f"⚔️ {r['challenger_name']} | {bet}", callback_data=f"race_accept:{r['id']}")
    b.button(text="◀️ Назад", callback_data="race")
    b.adjust(1)
    return b.as_markup()


def race_result_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [Btn(text="🔄 Ещё гонка", callback_data="race_street"), Btn(text="🏠 Меню", callback_data="menu")],
    ])


def tuning_kb(player_car: dict, money: int) -> InlineKeyboardMarkup:
    car = CAR_CATALOG[player_car["car_key"]]
    b = InlineKeyboardBuilder()
    for key, u in UPGRADE_DEFS.items():
        lvl = player_car[f"{key}_level"]
        if lvl >= u["max_level"]:
            b.button(text=f"{u['emoji']} {u['name']} [MAX] ✅", callback_data="noop")
        else:
            cost = get_upgrade_cost(car["price"], key, lvl)
            warn = "" if money >= cost else " ❌"
            b.button(text=f"{u['emoji']} {u['name']} [{lvl}/{u['max_level']}] — ${fmt(cost)}{warn}",
                     callback_data=f"upgrade:{player_car['id']}:{key}")
    b.button(text="◀️ К машине", callback_data=f"car:{player_car['id']}")
    b.adjust(1)
    return b.as_markup()


def upgrade_confirm_kb(car_id: int, key: str, cost: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [Btn(text=f"✅ Улучшить за ${fmt(cost)}", callback_data=f"upgrade_yes:{car_id}:{key}")],
        [Btn(text="❌ Отмена", callback_data=f"tuning:{car_id}")],
    ])


def profile_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [Btn(text="🏅 Достижения", callback_data="profile_ach")],
        [Btn(text="🏠 Меню", callback_data="menu")],
    ])


def top_kb(current: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for key, text in [("wins", "🏆 Победы"), ("money", "💰 Деньги"), ("level", "📈 Уровень"),
                      ("reputation", "⭐ Репутация"), ("coins", "🪙 Монеты")]:
        b.button(text=("✅ " if key == current else "") + text, callback_data=f"top:{key}")
    b.button(text="🏠 Меню", callback_data="menu")
    b.adjust(2)
    return b.as_markup()


def daily_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [Btn(text="🎁 Забрать награду", callback_data="daily_claim")],
        [Btn(text="🏠 Меню", callback_data="menu")],
    ])


def coin_shop_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for key, item in COIN_SHOP.items():
        b.button(text=f"{item['name']} — {item['price']} 🪙", callback_data=f"cbuy:{key}")
    b.button(text="🏠 Меню", callback_data="menu")
    b.adjust(1)
    return b.as_markup()

