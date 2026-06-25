import asyncio
import aiohttp
import time
from typing import Callable, Awaitable

from scrapers.sources import collect_all_sources, scrape_from_url, duckduckgo_dork
from scrapers.validator import check_proxy
from db.queries import upsert_proxy, add_source_url, get_all_sources
from utils.helpers import assign_tier
from config import (
    VALIDATOR_CONCURRENT,
    DORK_QUERIES,
    PROXY_FAIL_THRESHOLD,
)

_active_job: dict | None = None


def get_active_job() -> dict | None:
    return _active_job


def clear_active_job():
    global _active_job
    _active_job = None


async def run_full_scrape(
    job_id: str,
    target_tier: str | None = None,
    target_count: int | None = None,
    progress_callback: Callable[[dict], Awaitable[None]] | None = None,
) -> dict:
    global _active_job

    state = {
        "job_id": job_id,
        "proxies_found": 0,
        "sources_checked": 0,
        "cancelled": False,
        "target_tier": target_tier,
        "target_count": target_count,
        "started_at": time.time(),
    }
    _active_job = state

    semaphore = asyncio.Semaphore(VALIDATOR_CONCURRENT)
    connector = aiohttp.TCPConnector(limit=VALIDATOR_CONCURRENT + 50, ssl=False)

    async with aiohttp.ClientSession(connector=connector) as session:
        raw_proxies = await collect_all_sources(session)

        stored_sources = await get_all_sources()
        for url in stored_sources:
            if state["cancelled"]:
                break
            extra = await scrape_from_url(session, url)
            raw_proxies.extend(extra)
            state["sources_checked"] += 1

        dork_urls = []
        for query in DORK_QUERIES:
            if state["cancelled"]:
                break
            try:
                urls = await duckduckgo_dork(session, query)
                dork_urls.extend(urls)
            except Exception:
                pass

        for url in dork_urls:
            if state["cancelled"]:
                break
            extra = await scrape_from_url(session, url)
            if extra:
                await add_source_url(url)
                raw_proxies.extend(extra)
            state["sources_checked"] += 1

        seen = set()
        unique_proxies = []
        for p in raw_proxies:
            key = (p.get("ip"), p.get("port"))
            if key not in seen and p.get("ip") and p.get("port"):
                seen.add(key)
                unique_proxies.append(p)

        batch_size = 200
        for i in range(0, len(unique_proxies), batch_size):
            if state["cancelled"]:
                break

            if target_count and state["proxies_found"] >= target_count:
                break

            batch = unique_proxies[i:i + batch_size]
            tasks = []
            for p in batch:
                proxy_type = p.get("type", "http")
                if proxy_type not in ("http", "https", "socks4", "socks5"):
                    proxy_type = "http"
                tasks.append(check_proxy(session, p["ip"], p["port"], proxy_type, semaphore))

            check_results = await asyncio.gather(*tasks, return_exceptions=True)

            for j, p in enumerate(batch):
                if state["cancelled"]:
                    break
                r = check_results[j]
                if isinstance(r, Exception):
                    continue
                is_live, speed = r
                if not is_live:
                    continue

                anon = p.get("anonymity", "transparent")
                uptime = p.get("uptime", 50.0)
                reliability = min(100.0, uptime * 1.2)

                tier = assign_tier(speed, anon, reliability, True)
                if tier is None:
                    continue

                if target_tier and tier != target_tier.upper():
                    continue

                proxy_type = p.get("type", "http")
                country = p.get("country", "XX")
                source = p.get("source", "unknown")

                inserted = await upsert_proxy(
                    ip=p["ip"],
                    port=p["port"],
                    proxy_type=proxy_type,
                    country=country,
                    anonymity=anon,
                    speed=speed,
                    tier=tier,
                    uptime_percent=uptime,
                    reliability_score=reliability,
                    source_url=source,
                )

                if inserted:
                    state["proxies_found"] += 1
                    _active_job = state

            if progress_callback:
                try:
                    await progress_callback(dict(state))
                except Exception:
                    pass

    clear_active_job()
    return state


def cancel_active_job():
    global _active_job
    if _active_job:
        _active_job["cancelled"] = True
        return True
    return False
