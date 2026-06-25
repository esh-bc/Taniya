import asyncio
import io
from aiogram import Router
from aiogram.types import CallbackQuery, BufferedInputFile

from db.queries import (
    get_or_create_user,
    get_user_remaining,
    fetch_proxies,
    increment_user_usage,
    user_can_access_tier,
    reset_daily_if_needed,
)
from keyboards.builder import (
    tier_select_kb,
    type_select_kb,
    country_select_kb,
    count_select_kb,
    after_delivery_kb,
    limit_hit_kb,
)
from utils.helpers import time_until_midnight_utc, format_number, tier_label

router = Router()

_sessions: dict[int, dict] = {}


def get_session(user_id: int) -> dict:
    if user_id not in _sessions:
        _sessions[user_id] = {}
    return _sessions[user_id]


def clear_session(user_id: int):
    _sessions.pop(user_id, None)


@router.callback_query(lambda c: c.data == "get_proxies")
async def cb_get_proxies(callback: CallbackQuery):
    user = await get_or_create_user(callback.from_user.id, callback.from_user.username or "")
    await reset_daily_if_needed(callback.from_user.id)

    remaining = await get_user_remaining(user)
    if remaining <= 0:
        limit = user.get("daily_limit", 100)
        used = user.get("used_today", 0)
        reset_in = time_until_midnight_utc()
        text = (
            f"Mou~ you used all your proxies today senpai ◇\n"
            f"◈ Used      → {format_number(used)}/{format_number(limit)}\n"
            f"◇ Resets in → {reset_in}\n"
            f"Taiya-chan cannot help you until then~"
        )
        await callback.message.edit_text(text, reply_markup=limit_hit_kb())
        await callback.answer()
        return

    is_free = user.get("premium_tier", "free") == "free"
    clear_session(callback.from_user.id)

    text = "Which tier senpai~ ◇\nDon't be greedy ne~"
    await callback.message.edit_text(text, reply_markup=tier_select_kb(is_free=is_free))
    await callback.answer()


@router.callback_query(lambda c: c.data == "by_country")
async def cb_by_country(callback: CallbackQuery):
    user = await get_or_create_user(callback.from_user.id, callback.from_user.username or "")
    clear_session(callback.from_user.id)
    sess = get_session(callback.from_user.id)
    sess["from_country"] = True
    text = "Country filter~ or are you lazy senpai ◇"
    await callback.message.edit_text(text, reply_markup=country_select_kb())
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("tier_"))
async def cb_tier(callback: CallbackQuery):
    tier = callback.data.split("_")[1]
    user = await get_or_create_user(callback.from_user.id, callback.from_user.username or "")

    if not await user_can_access_tier(user, tier):
        await callback.answer(
            "Ara ara~ S-Tier is for premium senpai ◇ Upgrade ne~",
            show_alert=True,
        )
        return

    sess = get_session(callback.from_user.id)
    sess["tier"] = tier
    text = "What type ne~ ◇"
    await callback.message.edit_text(text, reply_markup=type_select_kb())
    await callback.answer()


@router.callback_query(lambda c: c.data == "back_tier")
async def cb_back_tier(callback: CallbackQuery):
    user = await get_or_create_user(callback.from_user.id, callback.from_user.username or "")
    is_free = user.get("premium_tier", "free") == "free"
    sess = get_session(callback.from_user.id)
    sess.pop("tier", None)
    await callback.message.edit_text(
        "Which tier senpai~ ◇\nDon't be greedy ne~",
        reply_markup=tier_select_kb(is_free=is_free),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("type_"))
async def cb_type(callback: CallbackQuery):
    proxy_type = callback.data.split("_")[1]
    sess = get_session(callback.from_user.id)
    sess["type"] = proxy_type
    if sess.get("from_country"):
        tier_text = "Which tier senpai~ ◇\nDon't be greedy ne~"
        user = await get_or_create_user(callback.from_user.id, callback.from_user.username or "")
        is_free = user.get("premium_tier", "free") == "free"
        await callback.message.edit_text(tier_text, reply_markup=tier_select_kb(is_free=is_free))
    else:
        await callback.message.edit_text(
            "Country filter~ or are you lazy senpai ◇",
            reply_markup=country_select_kb(),
        )
    await callback.answer()


@router.callback_query(lambda c: c.data == "back_type")
async def cb_back_type(callback: CallbackQuery):
    sess = get_session(callback.from_user.id)
    sess.pop("type", None)
    await callback.message.edit_text("What type ne~ ◇", reply_markup=type_select_kb())
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("country_"))
async def cb_country(callback: CallbackQuery):
    country = callback.data.split("_", 1)[1]
    sess = get_session(callback.from_user.id)
    sess["country"] = country

    if sess.get("from_country") and "tier" not in sess:
        user = await get_or_create_user(callback.from_user.id, callback.from_user.username or "")
        is_free = user.get("premium_tier", "free") == "free"
        await callback.message.edit_text(
            "Which tier senpai~ ◇\nDon't be greedy ne~",
            reply_markup=tier_select_kb(is_free=is_free),
        )
    elif "type" not in sess:
        await callback.message.edit_text("What type ne~ ◇", reply_markup=type_select_kb())
    else:
        await callback.message.edit_text(
            "How many ne~ don't get greedy ◇",
            reply_markup=count_select_kb(),
        )
    await callback.answer()


@router.callback_query(lambda c: c.data == "back_country")
async def cb_back_country(callback: CallbackQuery):
    sess = get_session(callback.from_user.id)
    sess.pop("country", None)
    await callback.message.edit_text(
        "Country filter~ or are you lazy senpai ◇",
        reply_markup=country_select_kb(),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("count_"))
async def cb_count(callback: CallbackQuery):
    count = int(callback.data.split("_")[1])
    uid = callback.from_user.id
    sess = get_session(uid)

    user = await get_or_create_user(uid, callback.from_user.username or "")
    await reset_daily_if_needed(uid)
    remaining = await get_user_remaining(user)

    if remaining <= 0:
        limit = user.get("daily_limit", 100)
        used = user.get("used_today", 0)
        reset_in = time_until_midnight_utc()
        text = (
            f"Mou~ you used all your proxies today senpai ◇\n"
            f"◈ Used      → {format_number(used)}/{format_number(limit)}\n"
            f"◇ Resets in → {reset_in}\n"
            f"Taiya-chan cannot help you until then~"
        )
        await callback.message.edit_text(text, reply_markup=limit_hit_kb())
        await callback.answer()
        return

    actual_count = min(count, remaining)
    tier = sess.get("tier", "B")
    proxy_type = sess.get("type", "all")
    country = sess.get("country", "all")

    steps = ["◇ Querying...", "◈ Filtering...", "✦ Packing...", "◎ Done ◇"]
    base_text = "◈ Fetching ne~\n"

    for step in steps[:-1]:
        await callback.message.edit_text(base_text + step)
        await asyncio.sleep(0.8)

    proxies = await fetch_proxies(tier, proxy_type, country, actual_count)

    await callback.message.edit_text(base_text + steps[-1])
    await asyncio.sleep(0.4)

    if not proxies:
        await callback.message.edit_text(
            "Mou~ no proxies found for those filters senpai ◇\n"
            "Taiya-chan tried her best ne~",
            reply_markup=after_delivery_kb(),
        )
        await callback.answer()
        clear_session(uid)
        return

    lines = [f"{p['ip']}:{p['port']}" for p in proxies]
    content = "\n".join(lines).encode()
    file = BufferedInputFile(content, filename=f"proxies_{tier}_{proxy_type}.txt")

    country_label = country if country not in ("all", "any") else "All"
    caption = (
        f"Mou~ finally done senpai ◇\n"
        f"◈ Count    → {format_number(len(proxies))}\n"
        f"◇ Tier     → {tier}\n"
        f"✦ Type     → {proxy_type.upper()}\n"
        f"◎ Country  → {country_label}"
    )

    await increment_user_usage(uid, len(proxies))
    await callback.message.delete()
    await callback.message.answer_document(file, caption=caption, reply_markup=after_delivery_kb())
    await callback.answer()
    clear_session(uid)
