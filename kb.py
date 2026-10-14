"""Inline-клавиатуры."""
from aiogram.types import InlineKeyboardButton as Btn, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from data import (CAR_CATALOG, CAR_CLASSES, CAR_CLASS_EMOJIS, CAR_CLASS_NAMES, CAR_COLORS, CASES, COIN_SHOP,
                  DIFFICULTY_EMOJI, STARS_PACKS, STREET_OPPONENTS, UPGRADE_DEFS, fmt, get_upgrade_cost)


def back_kb(cb: str = "menu", text: str = "◀️ Назад") -> InlineKeyboardMarkup:
    if cb == "menu":
        return InlineKeyboardMarkup(inline_keyboard=[[Btn(text="🏠 Главное меню", callback_data="menu")]])
    return InlineKeyboardMarkup(inline_keyboard=[
        [Btn(text=text, callback_data=cb), Btn(text="🏠 Главное меню", callback_data="menu")]
    ])


def main_menu_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    # Верхняя кнопка особой акции
    b.row(Btn(text="⚡ БАХНУТЬ СОЛИ (10 🪙)", callback_data="salt_boost"))
    # Звёздный магазин Telegram Stars
    b.row(Btn(text="⭐ ЗВЁЗДНЫЙ МАГАЗИН (STARS)", callback_data="stars_shop"))
    # Главная кнопка заездов и гонок
    b.row(Btn(text="🏁 ГОНКИ И ЗАЕЗДЫ", callback_data="race"))
    for text, cb in [
        ("🚗 Гараж", "garage:0"),
        ("🔧 Тюнинг", "tuning"),
        ("🏪 Автосалон", "shop"),
        ("🧰 Сундуки AMG", "cases"),
        ("🪙 Магазин монет", "cshop"),
        ("🎁 Бонус дня", "daily"),
        ("👤 Профиль", "profile"),
        ("🏆 Топ игроков", "top:wins"),
        ("👥 Командный режим", "group_info"),
        ("❓ Помощь", "help")
    ]:
        b.button(text=text, callback_data=cb)
    b.adjust(1, 1, 1, 2, 2, 2, 2, 2)
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
    b.row(Btn(text="🏠 Главное меню", callback_data="menu"))
    return b.as_markup()


def car_actions_kb(car_id: int, is_selected: bool) -> InlineKeyboardMarkup:
    rows = []
    if not is_selected:
        rows.append([Btn(text="✅ Сделать основной", callback_data=f"car_select:{car_id}")])
    rows.append([Btn(text="🔧 Тюнинг", callback_data=f"tuning:{car_id}"),
                 Btn(text="🎨 Покраска", callback_data=f"car_paint:{car_id}")])
    rows.append([Btn(text="🏷 Блатной номер", callback_data=f"car_plate:{car_id}"),
                 Btn(text="💰 Продать", callback_data=f"car_sell:{car_id}")])
    rows.append([Btn(text="🚗 В гараж", callback_data="garage:0"),
                 Btn(text="🏠 Главное меню", callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def car_plate_kb(car_id: int, has_plates: bool, current_plate: str | None = None) -> InlineKeyboardMarkup:
    presets = [
        "А 777 АА 77", "Х 001 АМ 99",
        "В 007 ОР 77", "С 666 СС 77",
        "АМГ 063", "B O S S",
    ]
    b = InlineKeyboardBuilder()
    for p in presets:
        is_cur = (current_plate == p)
        txt = f"🏷 {p} ✅" if is_cur else f"🏷 {p}"
        b.button(text=txt, callback_data=f"plate_set:{car_id}:{p}")
    b.adjust(2)

    extra_rows = []
    if not has_plates:
        extra_rows.append([Btn(text="⭐️ Купить установку номера (29 ⭐️)", callback_data="stars:buy:plate_custom")])
    if current_plate:
        extra_rows.append([Btn(text="🗑 Снять номер", callback_data=f"plate_remove:{car_id}")])
    extra_rows.append([Btn(text="◀️ К машине", callback_data=f"car:{car_id}"),
                       Btn(text="🚗 В гараж", callback_data="garage:0")])

    kb = b.as_markup()
    for row in extra_rows:
        kb.inline_keyboard.append(row)
    return kb


def paint_shop_kb(car_id: int, current_color_key: str = None) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for key, c_info in CAR_COLORS.items():
        is_cur = (current_color_key == key)
        status = " (Установлен) ✅" if is_cur else f" — {fmt(c_info['price'])} 🪙"
        b.button(text=f"{c_info['emoji']} {c_info['name']}{status}", callback_data=f"car_paint_buy:{car_id}:{key}")
    b.adjust(1)
    b.row(Btn(text="◀️ К машине", callback_data=f"car:{car_id}"),
          Btn(text="🚗 В гараж", callback_data="garage:0"))
    b.row(Btn(text="🏠 Главное меню", callback_data="menu"))
    return b.as_markup()


def sell_confirm_kb(car_id: int, price: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [Btn(text=f"✅ Продать за {fmt(price)} 🪙", callback_data=f"car_sell_yes:{car_id}")],
        [Btn(text="❌ Отмена (к машине)", callback_data=f"car:{car_id}")],
        [Btn(text="🚗 В гараж", callback_data="garage:0"), Btn(text="🏠 Главное меню", callback_data="menu")],
    ])


def shop_classes_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for cls in CAR_CLASSES:
        b.button(text=f"{CAR_CLASS_EMOJIS[cls]} Класс {cls} — {CAR_CLASS_NAMES[cls]}", callback_data=f"shop_class:{cls}")
    b.adjust(1)
    b.row(Btn(text="🏠 Главное меню", callback_data="menu"))
    return b.as_markup()


def shop_list_kb(cars: list, level: int, owned: set) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for key, car in cars:
        mark = " ✅" if key in owned else (" 🔒" if level < car["level_req"] else "")
        b.button(text=f"{car['emoji']} {car['name']} — {fmt(car['price'])} 🪙{mark}", callback_data=f"shop_car:{key}")
    b.adjust(1)
    b.row(Btn(text="◀️ К классам", callback_data="shop"), Btn(text="🏠 Главное меню", callback_data="menu"))
    return b.as_markup()


def buy_confirm_kb(car_key: str, cls: str, can_buy: bool, need_coins: bool = False) -> InlineKeyboardMarkup:
    rows = []
    if can_buy:
        rows.append([Btn(text="✅ Купить", callback_data=f"buy_yes:{car_key}")])
    elif need_coins:
        rows.append([Btn(text="⭐️ Пополнить монеты (Stars)", callback_data="stars_shop")])
    rows.append([Btn(text="◀️ Назад к классу", callback_data=f"shop_class:{cls}"),
                 Btn(text="🏪 К классам", callback_data="shop")])
    rows.append([Btn(text="🏠 Главное меню", callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def no_energy_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [Btn(text="⚡ Полный бак + Нитро (15 ⭐️)", callback_data="stars:view:energy_nitro")],
        [Btn(text="🪙 Заправить за 60 🪙", callback_data="cbuy:energy_refill")],
        [Btn(text="◀️ Назад к гонкам", callback_data="race"), Btn(text="🏠 Главное меню", callback_data="menu")],
    ])


def not_enough_coins_kb(back_target: str = "shop") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [Btn(text="⭐️ Пополнить монеты (Stars)", callback_data="stars_shop")],
        [Btn(text="◀️ Назад", callback_data=back_target), Btn(text="🏠 Главное меню", callback_data="menu")],
    ])


def race_menu_kb(energy: int = 10) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        Btn(text="⚔️ Дуэль 1х1", callback_data="race_pvp"),
        Btn(text="🏆 Гран-при турнир", callback_data="rmode:tourn")
    )
    b.row(
        Btn(text="🚓 Погоня от полиции", callback_data="rmode:chase"),
        Btn(text="👾 Рейд на босса", callback_data="rmode:boss")
    )
    b.row(
        Btn(text="🚦 Драг-рейсинг 402м", callback_data="rmode:drag"),
        Btn(text="👑 Выбывание Royale", callback_data="rmode:royale")
    )
    b.row(
        Btn(text="📦 Аирдроп контейнер", callback_data="rmode:airdrop"),
        Btn(text="🎰 Колесо Фортуны", callback_data="rmode:wheel")
    )
    b.row(
        Btn(text="🧠 Викторина AMG", callback_data="rmode:quiz")
    )
    b.row(
        Btn(text="⚡ Заправить бак (15 ⭐️)", callback_data="stars:view:energy_nitro"),
        Btn(text="⭐️ Звёздный магазин", callback_data="stars_shop")
    )
    b.row(
        Btn(text="📋 Открытые дуэли", callback_data="race_pvp_list"),
        Btn(text="🏠 Главное меню", callback_data="menu")
    )
    return b.as_markup()


def solo_race_kb(energy: int = 10) -> InlineKeyboardMarkup:
    rows = [
        [Btn(text="🟢 СТАРТ ЗАЕЗДА (-1 ⚡)", callback_data="race_solo_start")],
    ]
    if energy <= 2:
        rows.append([Btn(text="⚡ Полный бак + Нитро (15 ⭐️)", callback_data="stars:view:energy_nitro")])
    rows.append([Btn(text="◀️ Назад к гонкам", callback_data="race"),
                 Btn(text="🏠 Главное меню", callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def solo_race_result_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [Btn(text="🔄 Ещё заезд (-1 ⚡)", callback_data="race_solo_start")],
        [Btn(text="🏁 Все гонки", callback_data="race"),
         Btn(text="🏠 Главное меню", callback_data="menu")],
    ])


def street_opponents_kb(unlocked_idx: int = 0) -> InlineKeyboardMarkup:
    return solo_race_kb()


def pvp_bet_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for amount in (0, 10, 25, 50, 100):
        b.button(text="🤝 Без ставки" if amount == 0 else f"🪙 {amount} монет", callback_data=f"race_pvp_bet:{amount}")
    b.adjust(2)
    b.row(Btn(text="◀️ Назад к гонкам", callback_data="race"), Btn(text="🏠 Главное меню", callback_data="menu"))
    return b.as_markup()


def boss_kb(can_flee: bool = False) -> InlineKeyboardMarkup:
    rows = [
        [Btn(text="💥 ТАРАНИТЬ (-1 ⚡)", callback_data="boss:hit"),
         Btn(text="🔥 НИТРО-УДАР x2.5 (-2 ⚡)", callback_data="boss:nitro")],
        [Btn(text="📊 Статистика урона", callback_data="boss:stats"),
         Btn(text="🔄 Обновить HP", callback_data="boss:refresh")],
    ]
    if can_flee:
        rows.append([Btn(text="🏳️ Сбросить / Сбежать от босса", callback_data="boss:flee")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def wheel_kb(extra_spins: int = 0, is_spinned_today: bool = False, bot_username: str = "") -> InlineKeyboardMarkup:
    rows = []
    if not is_spinned_today:
        rows.append([Btn(text="🎰 КРУТИТЬ РУЛЕТКУ (Бесплатно)", callback_data="wheel:spin")])
    elif extra_spins > 0:
        rows.append([Btn(text=f"🎰 КРУТИТЬ ДОП. СПИН (Осталось: {extra_spins})", callback_data="wheel:spin_extra")])
    else:
        if bot_username:
            url_1 = f"https://t.me/{bot_username}?start=stars_wheel_spin_1"
            url_3 = f"https://t.me/{bot_username}?start=stars_wheel_spin_3"
            rows.append([Btn(text="🎰 1 спин (9 ⭐️)", url=url_1),
                         Btn(text="🎰 3 спина (19 ⭐️) 🔥", url=url_3)])
        else:
            rows.append([Btn(text="🎰 1 спин (9 ⭐️)", callback_data="stars:buy:wheel_spin_1"),
                         Btn(text="🎰 3 спина (19 ⭐️) 🔥", callback_data="stars:buy:wheel_spin_3")])

    rows.append([Btn(text="⭐ Магазин Звёзд", callback_data="stars_shop"),
                 Btn(text="🏠 Главное меню", callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


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
        bet = f"{fmt(r['bet'])} 🪙" if r["bet"] else "без ставки"
        b.button(text=f"⚔️ {r['challenger_name']} | {bet}", callback_data=f"race_accept:{r['id']}")
    b.adjust(1)
    b.row(Btn(text="◀️ Назад к гонкам", callback_data="race"), Btn(text="🏠 Главное меню", callback_data="menu"))
    return b.as_markup()


def race_result_kb(opp_idx: int = None) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [Btn(text="🔄 Ещё заезд (-1 ⚡)", callback_data="race_solo_start")],
        [
            Btn(text="🏁 Все гонки", callback_data="race"),
            Btn(text="🏠 Главное меню", callback_data="menu")
        ]
    ])


def tuning_kb(player_car: dict, coins: int) -> InlineKeyboardMarkup:
    car = CAR_CATALOG[player_car["car_key"]]
    b = InlineKeyboardBuilder()
    for key, u in UPGRADE_DEFS.items():
        lvl = player_car[f"{key}_level"]
        if lvl >= u["max_level"]:
            b.button(text=f"{u['emoji']} {u['name']} [MAX] ✅", callback_data="noop")
        else:
            cost = get_upgrade_cost(car["price"], key, lvl)
            warn = "" if coins >= cost else " ❌"
            b.button(text=f"{u['emoji']} {u['name']} [{lvl}/{u['max_level']}] — {fmt(cost)} 🪙{warn}",
                     callback_data=f"upgrade:{player_car['id']}:{key}")
    b.adjust(1)
    b.row(Btn(text="◀️ К машине", callback_data=f"car:{player_car['id']}"),
          Btn(text="🚗 В гараж", callback_data="garage:0"))
    b.row(Btn(text="🏠 Главное меню", callback_data="menu"))
    return b.as_markup()


def upgrade_confirm_kb(car_id: int, key: str, cost: int, can_afford: bool = True) -> InlineKeyboardMarkup:
    rows = []
    if can_afford:
        rows.append([Btn(text=f"✅ Улучшить за {fmt(cost)} 🪙", callback_data=f"upgrade_yes:{car_id}:{key}")])
    else:
        rows.append([Btn(text="⭐️ Пополнить монеты (Stars)", callback_data="stars_shop")])
    rows.append([Btn(text="❌ Отмена (к тюнингу)", callback_data=f"tuning:{car_id}")])
    rows.append([Btn(text="🚗 В гараж", callback_data="garage:0"), Btn(text="🏠 Главное меню", callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def profile_kb(is_vip: bool = False) -> InlineKeyboardMarkup:
    rows = []
    if not is_vip:
        rows.append([Btn(text="👑 Стать VIP за 79 ⭐️", callback_data="stars:view:vip_7")])
    rows.append([Btn(text="⭐️ Звёздный магазин", callback_data="stars_shop")])
    rows.append([Btn(text="🏅 Достижения", callback_data="profile_ach")])
    rows.append([Btn(text="🏠 Главное меню", callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def top_kb(current: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for key, text in [("wins", "🏆 Победы"), ("coins", "🪙 Монеты"), ("level", "📈 Уровень"),
                      ("reputation", "⭐ Репутация")]:
        b.button(text=("✅ " if key == current else "") + text, callback_data=f"top:{key}")
    b.adjust(2)
    b.row(Btn(text="🏠 Главное меню", callback_data="menu"))
    return b.as_markup()


def daily_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [Btn(text="🎁 Забрать награду", callback_data="daily_claim")],
        [Btn(text="🏠 Главное меню", callback_data="menu")],
    ])


def coin_shop_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="⭐️ Купить монеты за Stars", callback_data="stars_shop")
    b.button(text="🧰 Открыть сундуки AMG", callback_data="cases")
    for key, item in COIN_SHOP.items():
        if key.startswith("case_"):
            continue
        b.button(text=f"{item['name']} — {item['price']} 🪙", callback_data=f"cbuy:{key}")
    b.adjust(1)
    b.row(Btn(text="🏠 Главное меню", callback_data="menu"))
    return b.as_markup()


def cases_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for key, c_info in CASES.items():
        b.button(text=f"{c_info['emoji']} {c_info['name']} — {c_info['price']} 🪙", callback_data=f"case_open:{key}")
    b.adjust(1)
    b.row(Btn(text="⭐️ Пополнить монеты (Stars)", callback_data="stars_shop"))
    b.row(Btn(text="🪙 Магазин монет", callback_data="cshop"), Btn(text="🏠 Главное меню", callback_data="menu"))
    return b.as_markup()


def stars_shop_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for key, p in STARS_PACKS.items():
        badge = f" [{p['badge']}]" if p.get("badge") else ""
        b.button(text=f"{p['emoji']} {p['title']}{badge} — {p['stars']} ⭐️", callback_data=f"stars:view:{key}")
    b.adjust(1)
    b.row(Btn(text="🏠 Главное меню", callback_data="menu"))
    return b.as_markup()


def stars_pack_kb(pack_id: str, stars: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [Btn(text=f"⭐️ Оплатить {stars} ⭐️", callback_data=f"stars:buy:{pack_id}")],
        [Btn(text="◀️ В магазин звёзд", callback_data="stars_shop"), Btn(text="🏠 Главное меню", callback_data="menu")]
    ])


