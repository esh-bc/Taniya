import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from config import (
    SCRAPE_HOUR_UTC,
    SCRAPE_MINUTE_UTC,
    VALIDATION_INTERVAL_MINUTES,
)
from db.queries import (
    create_scrape_job,
    complete_scrape_job,
    get_running_scrape_job,
)
from scrapers.scraper import run_full_scrape
from scrapers.validator import run_validation_cycle

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="UTC")


async def daily_scrape_job():
    logger.info("◈ Daily scrape started ne~")
    running = await get_running_scrape_job()
    if running:
        logger.info("◇ Scrape already running, skipping ne~")
        return

    job_id = await create_scrape_job(
        job_type="scheduled",
        triggered_by=None,
        target_tier=None,
        target_count=None,
    )

    try:
        result = await run_full_scrape(job_id=job_id)
        await complete_scrape_job(
            job_id,
            proxies_found=result["proxies_found"],
            sources_checked=result["sources_checked"],
        )
        logger.info(
            f"◈ Daily scrape done ✦ found={result['proxies_found']} sources={result['sources_checked']}"
        )
    except Exception as e:
        logger.error(f"◎ Daily scrape error: {e}")


async def validation_job():
    logger.info("◇ Validation cycle started ne~")
    try:
        result = await run_validation_cycle()
        logger.info(
            f"✦ Validation done: live={result['live']} dead={result['dead']} removed={result['removed']}"
        )
    except Exception as e:
        logger.error(f"◎ Validation error: {e}")


async def daily_limit_reset_job():
    from datetime import date
    from db.models import db
    from config import DAILY_LIMITS
    today = date.today().isoformat()
    try:
        cursor = db.users.find({})
        async for user in cursor:
            tier = user.get("premium_tier", "free")
            limit = DAILY_LIMITS.get(tier, 100)
            await db.users.update_one(
                {"user_id": user["user_id"]},
                {"$set": {"used_today": 0, "last_reset": today, "daily_limit": limit}},
            )
        logger.info("◈ Daily limits reset for all users ne~")
    except Exception as e:
        logger.error(f"◎ Daily reset error: {e}")


def start_scheduler():
    scheduler.add_job(
        daily_scrape_job,
        CronTrigger(hour=SCRAPE_HOUR_UTC, minute=SCRAPE_MINUTE_UTC, timezone="UTC"),
        id="daily_scrape",
        replace_existing=True,
    )

    scheduler.add_job(
        validation_job,
        IntervalTrigger(minutes=VALIDATION_INTERVAL_MINUTES),
        id="validation",
        replace_existing=True,
    )

    scheduler.add_job(
        daily_limit_reset_job,
        CronTrigger(hour=0, minute=0, timezone="UTC"),
        id="daily_reset",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("◈ Scheduler started ne~ ✦")


def stop_scheduler():
    scheduler.shutdown(wait=False)
    logger.info("◇ Scheduler stopped ne~")
