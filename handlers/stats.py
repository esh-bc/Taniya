from aiogram import Router
from aiogram.types import CallbackQuery

from db.queries import get_or_create_user, get_user_remaining, reset_daily_if_needed
from keyboards.builder import stats_kb
from utils.helpers import time_until_midnight_utc, format_number

router = Router()


@router.callback_query(lambda c: c.data == "my_stats")
async def cb_my_stats(callback: CallbackQuery):
    user = await get_or_create_user(callback.from_user.id, callback.from_user.username or "")
    await reset_daily_if_needed(callback.from_user.id)
    user = await get_or_create_user(callback.from_user.id, callback.from_user.username or "")

    from datetime import datetime, timezone
    joined_at = user.get("joined_at")
    if joined_at:
        if joined_at.tzinfo is None:
            joined_at = joined_at.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - joined_at
        days_ago = delta.days
        joined_str = f"{days_ago} days ago" if days_ago > 0 else "today"
    else:
        joined_str = "unknown"

    tier = user.get("premium_tier", "free").capitalize()
    total_dl = user.get("total_downloaded", 0)
    used_today = user.get("used_today", 0)
    daily_limit = user.get("daily_limit", 100)
    limit_str = "∞" if tier.lower() == "elite" else format_number(daily_limit)
    reset_in = time_until_midnight_utc()

    text = (
        f"◈ Your stats senpai~\n"
        f"Mou~ don't get too proud ne ◇\n\n"
        f"◇ Plan        → {tier}\n"
        f"◈ Joined      → {joined_str}\n"
        f"✦ Total DL    → {format_number(total_dl)} proxies\n"
        f"◎ Today       → {format_number(used_today)}/{limit_str} used\n"
        f"━━━━━━━━━━━━━━\n"
        f"◇ Resets in   → {reset_in}"
    )

    await callback.message.edit_text(text, reply_markup=stats_kb())
    await callback.answer()
