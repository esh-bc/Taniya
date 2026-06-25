import asyncio
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from config import ADMIN_ID
from db.queries import (
    get_full_stats,
    create_scrape_job,
    complete_scrape_job,
    cancel_scrape_job,
    get_running_scrape_job,
    get_user,
    set_user_plan,
)
from scrapers.scraper import run_full_scrape, cancel_active_job, get_active_job
from keyboards.builder import admin_run_kb
from utils.helpers import format_number, time_since, time_until, elapsed_str

router = Router()

REJECT_MSG = "Ara ara~ those commands are not for you senpai ◇"


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


@router.message(Command("stats"))
async def cmd_admin_stats(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer(REJECT_MSG)
        return

    data = await get_full_stats()
    pool = data["pool"]
    last = time_since(data["last_scrape"]) if data["last_scrape"] else "never"
    nxt = time_until(data["next_scrape"]) if data["next_scrape"] else "unknown"

    running_job = await get_running_scrape_job()
    validator_status = "running ◇" if running_job else "idle ◎"

    text = (
        f"◈ Database Status ne~\n"
        f"◇ S-Tier live   → {format_number(pool['S'])}\n"
        f"◈ A-Tier live   → {format_number(pool['A'])}\n"
        f"✦ B-Tier live   → {format_number(pool['B'])}\n"
        f"◎ Total stored  → {format_number(pool['total'])}\n"
        f"━━━━━━━━━━━━━━\n"
        f"◇ Last scrape   → {last}\n"
        f"◈ Next scrape   → {nxt}\n"
        f"✦ Validator     → {validator_status}\n"
        f"━━━━━━━━━━━━━━\n"
        f"◇ Total users   → {format_number(data['total_users'])}\n"
        f"◈ Premium users → {format_number(data['premium_users'])}\n"
        f"✦ Requests today→ {format_number(data['requests_today'])}"
    )
    await message.answer(text)


@router.message(Command("run"))
async def cmd_run(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer(REJECT_MSG)
        return

    running = await get_running_scrape_job()
    if running:
        await message.answer(
            "Mou~ already running senpai ◇\n"
            "Use /cancel first ne~"
        )
        return

    args = message.text.split()[1:]
    target_count: int | None = None
    target_tier: str | None = None

    if len(args) >= 2:
        try:
            target_count = int(args[0])
            raw_tier = args[1].upper()
            if raw_tier in ("S", "A", "B"):
                target_tier = raw_tier
            else:
                await message.answer(
                    "Mou~ invalid tier senpai ◇\n"
                    "Use: /run <count> <s|a|b>"
                )
                return
        except ValueError:
            await message.answer(
                "Mou~ invalid format senpai ◇\n"
                "Use: /run or /run 50 s"
            )
            return

    job_id = await create_scrape_job(
        job_type="targeted" if target_count else "manual",
        triggered_by=message.from_user.id,
        target_tier=target_tier,
        target_count=target_count,
    )

    if target_count and target_tier:
        initial = (
            f"◈ Hunting {target_tier}-tier ne~ ◇\n"
            f"◇ Target     → {format_number(target_count)}\n"
            f"✦ Found so far → 0\n"
            f"◎ Sources checked → 0\n"
            f"━━━━━━━━━━━━━━"
        )
    else:
        initial = (
            f"Mou~ fine, Taiya-chan will scrape now ◇\n"
            f"◈ Sources queued  → starting\n"
            f"◇ Proxies found   → 0\n"
            f"✦ Validated       → 0\n"
            f"━━━━━━━━━━━━━━\n"
            f"◎ Status → Running..."
        )

    status_msg = await message.answer(initial, reply_markup=admin_run_kb(job_id))

    async def send_progress(state: dict):
        if target_count and target_tier:
            text = (
                f"◈ Hunting {target_tier}-tier ne~ ◇\n"
                f"◇ Target     → {format_number(target_count)}\n"
                f"✦ Found so far → {format_number(state['proxies_found'])}\n"
                f"◎ Sources checked → {format_number(state['sources_checked'])}\n"
                f"━━━━━━━━━━━━━━"
            )
        else:
            elapsed = elapsed_str(
                __import__("datetime").datetime.fromtimestamp(
                    state["started_at"],
                    tz=__import__("datetime").timezone.utc
                )
            )
            text = (
                f"Mou~ fine, Taiya-chan will scrape now ◇\n"
                f"◈ Sources queued  → {format_number(state['sources_checked'])}\n"
                f"◇ Proxies found   → {format_number(state['proxies_found'])}\n"
                f"✦ Time elapsed    → {elapsed}\n"
                f"━━━━━━━━━━━━━━\n"
                f"◎ Status → Running..."
            )
        try:
            await status_msg.edit_text(text, reply_markup=admin_run_kb(job_id))
        except Exception:
            pass

    result = await run_full_scrape(
        job_id=job_id,
        target_tier=target_tier,
        target_count=target_count,
        progress_callback=send_progress,
    )

    if not result.get("cancelled"):
        await complete_scrape_job(
            job_id,
            proxies_found=result["proxies_found"],
            sources_checked=result["sources_checked"],
        )

        if target_count and target_tier:
            from datetime import datetime, timezone
            import time
            elapsed = elapsed_str(
                datetime.fromtimestamp(result["started_at"], tz=timezone.utc)
            )
            done_text = (
                f"Ara ara~ Taiya-chan found your {format_number(target_count)} {target_tier}-tier proxies ✦\n"
                f"◈ Target      → {format_number(target_count)}\n"
                f"◇ Found       → {format_number(result['proxies_found'])}\n"
                f"◎ Time taken  → {elapsed}\n"
                f"✦ Scrape stopped automatically ne~"
            )
        else:
            done_text = (
                f"◈ Done ne~ Taiya-chan finished scraping ✦\n"
                f"◇ Proxies found   → {format_number(result['proxies_found'])}\n"
                f"◎ Sources checked → {format_number(result['sources_checked'])}\n"
                f"✦ All saved to database ne~"
            )
        await status_msg.edit_text(done_text)


@router.message(Command("cancel"))
async def cmd_cancel(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer(REJECT_MSG)
        return

    job = get_active_job()
    if not job:
        await message.answer(
            "There is nothing running senpai ◇\n"
            "Taiya-chan is just sitting here..."
        )
        return

    cancelled = cancel_active_job()
    if cancelled:
        proxies_found = job.get("proxies_found", 0)
        job_id = job.get("job_id")
        if job_id:
            await cancel_scrape_job(job_id, proxies_found)
        await message.answer(
            f"Mou~ fine, Taiya-chan is stopping ◇\n"
            f"◈ Proxies found before cancel → {format_number(proxies_found)}\n"
            f"✦ They are saved to database ne~"
        )
    else:
        await message.answer(
            "There is nothing running senpai ◇\n"
            "Taiya-chan is just sitting here..."
        )


VALID_PLANS = ("free", "basic", "pro", "elite")
PLAN_LIMITS = {"free": "100/day", "basic": "500/day", "pro": "2,000/day", "elite": "Unlimited"}
PLAN_TIERS  = {"free": "A, B only", "basic": "All", "pro": "All", "elite": "All + Priority"}


@router.message(Command("promote"))
async def cmd_promote(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer(REJECT_MSG)
        return

    args = message.text.split()[1:]
    if len(args) < 2:
        await message.answer(
            "Mou~ usage senpai ◇\n"
            "/promote <user_id> <plan>\n\n"
            "◇ Plans → basic · pro · elite"
        )
        return

    try:
        target_id = int(args[0])
    except ValueError:
        await message.answer("Ara ara~ that user_id looks wrong senpai ◇")
        return

    plan = args[1].lower()
    if plan not in ("basic", "pro", "elite"):
        await message.answer(
            "Mou~ invalid plan senpai ◇\n"
            "◇ Choose → basic · pro · elite"
        )
        return

    existing = await get_user(target_id)
    old_plan = existing.get("premium_tier", "free") if existing else "not registered"

    updated = await set_user_plan(target_id, plan)
    if not updated:
        await message.answer(
            f"◎ User {target_id} not found in database senpai ◇\n"
            f"They need to /start the bot first ne~"
        )
        return

    await message.answer(
        f"◈ Plan updated ne~ ✦\n"
        f"━━━━━━━━━━━━━━\n"
        f"◇ User ID   → {target_id}\n"
        f"◈ Old plan  → {old_plan.capitalize()}\n"
        f"✦ New plan  → {plan.capitalize()}\n"
        f"◎ Limit     → {PLAN_LIMITS[plan]}\n"
        f"◇ Tiers     → {PLAN_TIERS[plan]}\n"
        f"━━━━━━━━━━━━━━\n"
        f"Taiya-chan applied it immediately ne~ ◇"
    )


@router.message(Command("demote"))
async def cmd_demote(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer(REJECT_MSG)
        return

    args = message.text.split()[1:]
    if len(args) < 1:
        await message.answer(
            "Mou~ usage senpai ◇\n"
            "/demote <user_id> [plan]\n\n"
            "◇ Plan is optional → default is free\n"
            "◇ Valid → free · basic · pro"
        )
        return

    try:
        target_id = int(args[0])
    except ValueError:
        await message.answer("Ara ara~ that user_id looks wrong senpai ◇")
        return

    plan = args[1].lower() if len(args) >= 2 else "free"
    if plan not in ("free", "basic", "pro"):
        await message.answer(
            "Mou~ invalid plan senpai ◇\n"
            "◇ Demote targets → free · basic · pro"
        )
        return

    existing = await get_user(target_id)
    if not existing:
        await message.answer(
            f"◎ User {target_id} not found senpai ◇\n"
            f"They need to /start the bot first ne~"
        )
        return

    old_plan = existing.get("premium_tier", "free")
    if old_plan == plan:
        await message.answer(
            f"◎ User {target_id} is already on {plan.capitalize()} senpai ◇\n"
            f"Nothing to do ne~"
        )
        return

    updated = await set_user_plan(target_id, plan)
    if not updated:
        await message.answer("Mou~ something went wrong ◈ Try again senpai~")
        return

    await message.answer(
        f"◇ Plan downgraded ne~ ◎\n"
        f"━━━━━━━━━━━━━━\n"
        f"◇ User ID   → {target_id}\n"
        f"◈ Old plan  → {old_plan.capitalize()}\n"
        f"✦ New plan  → {plan.capitalize()}\n"
        f"◎ Limit     → {PLAN_LIMITS[plan]}\n"
        f"◇ Tiers     → {PLAN_TIERS[plan]}\n"
        f"━━━━━━━━━━━━━━\n"
        f"Taiya-chan applied it immediately ne~ ◇"
    )


@router.message(Command("userinfo"))
async def cmd_userinfo(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer(REJECT_MSG)
        return

    args = message.text.split()[1:]
    if not args:
        await message.answer(
            "Mou~ usage senpai ◇\n"
            "/userinfo <user_id>"
        )
        return

    try:
        target_id = int(args[0])
    except ValueError:
        await message.answer("Ara ara~ that user_id looks wrong senpai ◇")
        return

    user = await get_user(target_id)
    if not user:
        await message.answer(
            f"◎ User {target_id} not found senpai ◇\n"
            f"They haven't started the bot ne~"
        )
        return

    from utils.helpers import time_since as _ts
    plan = user.get("premium_tier", "free")
    used = user.get("used_today", 0)
    limit = user.get("daily_limit", 100)
    limit_str = "∞" if plan == "elite" else format_number(limit)
    total_dl = user.get("total_downloaded", 0)
    joined = _ts(user.get("joined_at"))
    username = user.get("username") or "—"

    await message.answer(
        f"◈ User Info ne~\n"
        f"━━━━━━━━━━━━━━\n"
        f"◇ User ID   → {target_id}\n"
        f"◈ Username  → @{username}\n"
        f"✦ Plan      → {plan.capitalize()}\n"
        f"◎ Limit     → {PLAN_LIMITS[plan]}\n"
        f"◇ Tiers     → {PLAN_TIERS[plan]}\n"
        f"━━━━━━━━━━━━━━\n"
        f"◈ Used today→ {format_number(used)}/{limit_str}\n"
        f"◇ Total DL  → {format_number(total_dl)} proxies\n"
        f"✦ Joined    → {joined}\n"
        f"━━━━━━━━━━━━━━\n"
        f"◇ Promote → /promote {target_id} <plan>\n"
        f"◈ Demote  → /demote {target_id} [plan]"
    )


@router.callback_query(lambda c: c.data and c.data.startswith("admin_cancel_"))
async def cb_admin_cancel(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer(REJECT_MSG, show_alert=True)
        return

    job = get_active_job()
    if not job:
        await callback.answer("Nothing running senpai ◇", show_alert=True)
        return

    cancelled = cancel_active_job()
    if cancelled:
        proxies_found = job.get("proxies_found", 0)
        job_id = job.get("job_id")
        if job_id:
            await cancel_scrape_job(job_id, proxies_found)
        await callback.message.edit_text(
            f"Mou~ fine, Taiya-chan is stopping ◇\n"
            f"◈ Proxies found before cancel → {format_number(proxies_found)}\n"
            f"✦ They are saved to database ne~"
        )
    await callback.answer()
