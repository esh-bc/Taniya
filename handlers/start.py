from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery

from db.queries import get_or_create_user, get_pool_stats, get_last_scrape_time
from keyboards.builder import main_menu_kb, back_main_kb
from utils.helpers import time_since, format_number

router = Router()


async def send_main_menu(target: Message | CallbackQuery, user: dict):
    pool = await get_pool_stats()
    last_scrape = await get_last_scrape_time()
    updated = time_since(last_scrape) if last_scrape else "never"

    text = (
        f"Ara ara~ you finally showed up senpai ◇\n"
        f"Taiya-chan has fresh proxies waiting~\n\n"
        f"◈ Pool Status\n"
        f"◇ S-Tier  → {format_number(pool['S'])} live\n"
        f"◈ A-Tier  → {format_number(pool['A'])} live\n"
        f"✦ B-Tier  → {format_number(pool['B'])} live\n"
        f"━━━━━━━━━━━━━━\n"
        f"Updated {updated} ◎"
    )
    kb = main_menu_kb(is_premium=user.get("is_premium", False))

    if isinstance(target, Message):
        await target.answer(text, reply_markup=kb)
    else:
        await target.message.edit_text(text, reply_markup=kb)


@router.message(CommandStart())
async def cmd_start(message: Message):
    user = await get_or_create_user(message.from_user.id, message.from_user.username or "")
    await send_main_menu(message, user)


@router.callback_query(lambda c: c.data == "back_main")
async def cb_back_main(callback: CallbackQuery):
    user = await get_or_create_user(callback.from_user.id, callback.from_user.username or "")
    await send_main_menu(callback, user)
    await callback.answer()


@router.callback_query(lambda c: c.data == "help")
async def cb_help(callback: CallbackQuery):
    text = (
        "◈ Taiya-chan's Guide ne~\n\n"
        "◇ Get Proxies  → Choose tier, type, country and count\n"
        "◈ My Stats     → See your daily usage and plan\n"
        "✦ By Country   → Filter proxies by country first\n"
        "◎ Premium~     → Upgrade for more proxies senpai\n\n"
        "━━━━━━━━━━━━━━\n"
        "◇ Tiers explained ne~\n"
        "⬡ S-Tier → Ultra fast elite proxies (Premium only)\n"
        "◈ A-Tier → Fast anonymous proxies\n"
        "◇ B-Tier → Standard live proxies\n\n"
        "Mou~ don't waste Taiya-chan's time senpai ◇"
    )
    from keyboards.builder import back_main_kb
    await callback.message.edit_text(text, reply_markup=back_main_kb())
    await callback.answer()
