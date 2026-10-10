"""Общие хелперы и мидлвари."""
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message, TelegramObject, User

import db
from config import ADMIN_IDS
from data import ACHIEVEMENTS_DEF
from engine import check_achievements

# (chat_id, message_id) -> user_id владельца меню (для групповых чатов)
MENU_OWNERS: dict = {}
_admin_cache: set = set()

# Кнопки, которые может нажимать любой участник чата в группе
PUBLIC_CALLBACKS = (
    "race_accept:", "race_cancel:", "race_street:", "race_street",
    "tourn:", "boss:", "chase:", "drop:", "royale:", "drag:",
    "quiz:", "adv:", "wheel:", "race_pvp", "race_coin_bet:", "race_pvp_bet:"
)


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS or user_id in _admin_cache


async def reload_admins():
    _admin_cache.clear()
    _admin_cache.update(await db.get_admin_ids())


def set_admin_cache(user_id: int, value: bool):
    (_admin_cache.add if value else _admin_cache.discard)(user_id)


async def ensure_player(user: User) -> dict:
    p = await db.get_player(user.id)
    if p is None:
        p = await db.create_player(user.id, user.username, user.first_name or "Гонщик")
        car_id = await db.add_car(user.id, "c180")
        await db.select_car(user.id, car_id)
        p = await db.get_player(user.id)
    elif p["username"] != user.username or p["first_name"] != (user.first_name or "Гонщик"):
        await db.update_player(user.id, username=user.username, first_name=user.first_name or "Гонщик")
    return p


async def send_menu(message: Message, owner_id: int, text: str, kb=None):
    sent = await message.answer(text, reply_markup=kb)
    if message.chat.type != "private":
        MENU_OWNERS[(sent.chat.id, sent.message_id)] = owner_id
        if len(MENU_OWNERS) > 5000:
            for k in list(MENU_OWNERS)[:1000]:
                MENU_OWNERS.pop(k, None)
    return sent


async def safe_edit(cb: CallbackQuery, text: str, kb=None):
    try:
        await cb.message.edit_text(text, reply_markup=kb)
    except TelegramBadRequest as e:
        if "not modified" not in str(e):
            try:
                await cb.message.answer(text, reply_markup=kb)
            except TelegramBadRequest:
                pass


async def award_achievements(user_id: int, extra: set = None) -> str:
    """Проверяет и выдаёт достижения, возвращает текст-уведомление."""
    player = await db.get_player(user_id)
    cars = await db.get_player_cars(user_id)
    current = await db.get_achievements(user_id)
    new = check_achievements(player, cars, current, extra)
    lines = []
    for key in new:
        if await db.add_achievement(user_id, key):
            a = ACHIEVEMENTS_DEF[key]
            coins = await db.grant_coins(user_id, 25)
            reward = f" (+{coins} 🪙)" if coins else ""
            lines.append(f"🏅 <b>Достижение:</b> {a['emoji']} {a['name']}{reward}")
    return ("\n\n" + "\n".join(lines)) if lines else ""


class AccessMiddleware(BaseMiddleware):
    """Создаёт игрока, блокирует забаненных и чужие меню в группах."""

    async def __call__(self, handler: Callable[[TelegramObject, dict], Awaitable[Any]],
                       event: TelegramObject, data: dict) -> Any:
        user = getattr(event, "from_user", None)
        if user is None or user.is_bot:
            return await handler(event, data)

        player = await ensure_player(user)
        if player.get("is_banned") and not is_admin(user.id):
            if isinstance(event, CallbackQuery):
                await event.answer("🚫 Доступ к игре ограничен.", show_alert=True)
            elif isinstance(event, Message) and event.chat.type == "private":
                await event.answer("🚫 Доступ к игре ограничен.")
            return None

        if isinstance(event, CallbackQuery) and event.message:
            cbd = event.data or ""
            owner = MENU_OWNERS.get((event.message.chat.id, event.message.message_id))
            if owner and owner != user.id and not cbd.startswith(PUBLIC_CALLBACKS):
                await event.answer("Это не твоё меню! Напиши /menu 🙂", show_alert=True)
                return None

        data["player"] = player
        return await handler(event, data)

