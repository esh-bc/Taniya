from datetime import datetime, timezone, date
import db.models as _models
from db.models import proxy_document, user_document
from config import DAILY_LIMITS, TIER_ACCESS


def _db():
    return _models.db


async def get_user(user_id: int) -> dict | None:
    return await _db().users.find_one({"user_id": user_id})


async def get_or_create_user(user_id: int, username: str) -> dict:
    user = await _db().users.find_one({"user_id": user_id})
    if user:
        await reset_daily_if_needed(user_id)
        return await _db().users.find_one({"user_id": user_id})
    doc = user_document(user_id, username)
    await _db().users.insert_one(doc)
    return doc


async def reset_daily_if_needed(user_id: int):
    user = await _db().users.find_one({"user_id": user_id})
    if not user:
        return
    today = date.today().isoformat()
    if user.get("last_reset") != today:
        tier = user.get("premium_tier", "free")
        limit = DAILY_LIMITS.get(tier, 100)
        await _db().users.update_one(
            {"user_id": user_id},
            {"$set": {"used_today": 0, "last_reset": today, "daily_limit": limit}},
        )


async def get_user_remaining(user: dict) -> int:
    tier = user.get("premium_tier", "free")
    if tier == "elite":
        return 999999
    limit = user.get("daily_limit", 100)
    used = user.get("used_today", 0)
    return max(0, limit - used)


async def increment_user_usage(user_id: int, count: int):
    await _db().users.update_one(
        {"user_id": user_id},
        {"$inc": {"used_today": count, "total_downloaded": count}},
    )


async def user_can_access_tier(user: dict, tier: str) -> bool:
    premium_tier = user.get("premium_tier", "free")
    allowed = TIER_ACCESS.get(premium_tier, ["A", "B"])
    return tier.upper() in allowed


async def fetch_proxies(
    tier: str,
    proxy_type: str,
    country: str,
    count: int,
) -> list[dict]:
    query: dict = {"tier": tier.upper(), "is_live": True}
    if proxy_type.lower() != "all":
        query["type"] = proxy_type.lower()
    if country.lower() not in ("all", "any", ""):
        query["country"] = country.upper()

    cursor = _db().proxies.find(query).sort("reliability_score", -1).limit(count)
    return await cursor.to_list(length=count)


async def get_pool_stats() -> dict:
    pipeline = [
        {"$match": {"is_live": True}},
        {"$group": {"_id": "$tier", "count": {"$sum": 1}}},
    ]
    result = await _db().proxies.aggregate(pipeline).to_list(length=10)
    stats = {"S": 0, "A": 0, "B": 0, "total": 0}
    for row in result:
        tier = row["_id"]
        if tier in stats:
            stats[tier] = row["count"]
    stats["total"] = await _db().proxies.count_documents({})
    return stats


async def get_last_scrape_time() -> datetime | None:
    job = await _db().scrape_jobs.find_one(
        {"status": "completed"},
        sort=[("finished_at", -1)],
    )
    if job:
        return job.get("finished_at")
    return None


async def get_next_scrape_time() -> datetime | None:
    from config import SCRAPE_HOUR_UTC, SCRAPE_MINUTE_UTC
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    next_run = now.replace(
        hour=SCRAPE_HOUR_UTC, minute=SCRAPE_MINUTE_UTC, second=0, microsecond=0
    )
    if next_run <= now:
        next_run += timedelta(days=1)
    return next_run


async def upsert_proxy(
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
) -> bool:
    doc = proxy_document(
        ip, port, proxy_type, country, anonymity, speed,
        tier, uptime_percent, reliability_score, source_url,
    )
    result = await _db().proxies.update_one(
        {"ip": ip, "port": port},
        {"$set": doc},
        upsert=True,
    )
    return result.upserted_id is not None


async def update_proxy_check(
    ip: str, port: int, is_live: bool, speed: int = 0
):
    now = datetime.now(timezone.utc)
    inc = {"check_count": 1}
    if not is_live:
        inc["fail_count"] = 1
    update = {
        "$set": {"is_live": is_live, "last_checked": now},
        "$inc": inc,
    }
    if is_live and speed > 0:
        update["$set"]["speed"] = speed
    await _db().proxies.update_one({"ip": ip, "port": port}, update)


async def remove_dead_proxies(fail_threshold: int = 3):
    result = await _db().proxies.delete_many({"fail_count": {"$gte": fail_threshold}})
    return result.deleted_count


async def get_proxies_to_validate(batch_size: int = 5000) -> list[dict]:
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=25)
    cursor = _db().proxies.find(
        {"last_checked": {"$lt": cutoff}},
        {"ip": 1, "port": 1, "type": 1},
    ).limit(batch_size)
    return await cursor.to_list(length=batch_size)


async def create_scrape_job(
    job_type: str,
    triggered_by: int | None,
    target_tier: str | None,
    target_count: int | None,
) -> str:
    doc = {
        "job_type": job_type,
        "triggered_by": triggered_by,
        "target_tier": target_tier,
        "target_count": target_count,
        "status": "running",
        "proxies_found": 0,
        "sources_checked": 0,
        "started_at": datetime.now(timezone.utc),
        "finished_at": None,
    }
    result = await _db().scrape_jobs.insert_one(doc)
    return str(result.inserted_id)


async def update_scrape_job(job_id: str, **fields):
    from bson import ObjectId
    await _db().scrape_jobs.update_one(
        {"_id": ObjectId(job_id)},
        {"$set": fields},
    )


async def complete_scrape_job(job_id: str, proxies_found: int, sources_checked: int):
    from bson import ObjectId
    await _db().scrape_jobs.update_one(
        {"_id": ObjectId(job_id)},
        {
            "$set": {
                "status": "completed",
                "proxies_found": proxies_found,
                "sources_checked": sources_checked,
                "finished_at": datetime.now(timezone.utc),
            }
        },
    )


async def cancel_scrape_job(job_id: str, proxies_found: int):
    from bson import ObjectId
    await _db().scrape_jobs.update_one(
        {"_id": ObjectId(job_id)},
        {
            "$set": {
                "status": "cancelled",
                "proxies_found": proxies_found,
                "finished_at": datetime.now(timezone.utc),
            }
        },
    )


async def get_running_scrape_job() -> dict | None:
    return await _db().scrape_jobs.find_one({"status": "running"})


async def get_full_stats() -> dict:
    pool = await get_pool_stats()
    total_users = await _db().users.count_documents({})
    premium_users = await _db().users.count_documents({"is_premium": True})

    today = date.today().isoformat()
    pipeline = [
        {"$match": {"last_reset": today}},
        {"$group": {"_id": None, "total": {"$sum": "$used_today"}}},
    ]
    result = await _db().users.aggregate(pipeline).to_list(length=1)
    requests_today = result[0]["total"] if result else 0

    last_scrape = await get_last_scrape_time()
    next_scrape = await get_next_scrape_time()

    return {
        "pool": pool,
        "total_users": total_users,
        "premium_users": premium_users,
        "requests_today": requests_today,
        "last_scrape": last_scrape,
        "next_scrape": next_scrape,
    }


async def set_user_plan(user_id: int, plan: str) -> dict | None:
    plan = plan.lower()
    if plan not in ("free", "basic", "pro", "elite"):
        return None
    limit = DAILY_LIMITS.get(plan, 100)
    is_premium = plan != "free"
    result = await _db().users.find_one_and_update(
        {"user_id": user_id},
        {
            "$set": {
                "premium_tier": plan,
                "is_premium": is_premium,
                "daily_limit": limit,
            }
        },
        return_document=True,
    )
    return result


async def add_source_url(url: str):
    try:
        await _db().sources.update_one(
            {"url": url},
            {"$setOnInsert": {"url": url, "added_at": datetime.now(timezone.utc), "hit_count": 0}},
            upsert=True,
        )
    except Exception:
        pass


async def get_all_sources() -> list[str]:
    cursor = _db().sources.find({}, {"url": 1})
    docs = await cursor.to_list(length=10000)
    return [d["url"] for d in docs]
