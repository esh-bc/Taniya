from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGODB_URL, MONGODB_DB_NAME

client: AsyncIOMotorClient = None
db = None


async def connect_db():
    global client, db
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[MONGODB_DB_NAME]
    await create_indexes()


async def close_db():
    if client:
        client.close()


async def create_indexes():
    await db.proxies.create_index([("ip", 1), ("port", 1)], unique=True)
    await db.proxies.create_index([("tier", 1), ("is_live", 1)])
    await db.proxies.create_index([("tier", 1), ("type", 1), ("is_live", 1)])
    await db.proxies.create_index([("tier", 1), ("type", 1), ("country", 1), ("is_live", 1)])
    await db.proxies.create_index([("is_live", 1), ("last_checked", 1)])
    await db.proxies.create_index([("fail_count", 1)])
    await db.users.create_index([("user_id", 1)], unique=True)
    await db.scrape_jobs.create_index([("status", 1)])
    await db.scrape_jobs.create_index([("started_at", -1)])
    await db.sources.create_index([("url", 1)], unique=True)


def proxy_document(
    ip: str,
    port: int,
    proxy_type: str,
    country: str,
    anonymity: str,
    speed: int,
    tier: str,
    uptime_percent: float,
    reliability_score: float,
    source_url: str,
) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "ip": ip,
        "port": port,
        "type": proxy_type.lower(),
        "country": country.upper() if country else "XX",
        "anonymity": anonymity.lower(),
        "speed": speed,
        "tier": tier.upper(),
        "uptime_percent": uptime_percent,
        "reliability_score": reliability_score,
        "check_count": 1,
        "fail_count": 0,
        "is_live": True,
        "last_checked": now,
        "source_url": source_url,
        "created_at": now,
    }


def user_document(user_id: int, username: str) -> dict:
    return {
        "user_id": user_id,
        "username": username or "",
        "is_premium": False,
        "premium_tier": "free",
        "daily_limit": 100,
        "used_today": 0,
        "last_reset": datetime.now(timezone.utc).date().isoformat(),
        "total_downloaded": 0,
        "joined_at": datetime.now(timezone.utc),
    }
