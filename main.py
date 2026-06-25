import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN, REDIS_HOST, REDIS_PORT, REDIS_DB
from db.models import connect_db, close_db
from scheduler.jobs import start_scheduler, stop_scheduler

from handlers import start, proxy, stats, premium, admin

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


async def main():
    logger.info("◈ ProxyNeko starting ne~ ✦")

    await connect_db()
    logger.info("◇ MongoDB connected ◎")

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher()

    dp.include_router(admin.router)
    dp.include_router(start.router)
    dp.include_router(proxy.router)
    dp.include_router(stats.router)
    dp.include_router(premium.router)

    start_scheduler()
    logger.info("◈ Scheduler running ✦")

    logger.info("◎ Taiya-chan is ready senpai~ ◇")

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        stop_scheduler()
        await close_db()
        await bot.session.close()
        logger.info("◇ Taiya-chan is going to sleep ne~ ◎")


if __name__ == "__main__":
    asyncio.run(main())
