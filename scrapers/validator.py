import asyncio
import time
import aiohttp
from aiohttp_socks import ProxyConnector, ProxyType
from db.queries import (
    get_proxies_to_validate,
    update_proxy_check,
    remove_dead_proxies,
)
from config import VALIDATOR_CONCURRENT, PROXY_FAIL_THRESHOLD

TEST_URL = "http://httpbin.org/ip"
TIMEOUT_SECONDS = 8

_SOCKS_TYPES = {"socks4": ProxyType.SOCKS4, "socks5": ProxyType.SOCKS5}


async def check_proxy(
    ip: str,
    port: int,
    proxy_type: str,
    semaphore: asyncio.Semaphore,
) -> tuple[bool, int]:
    async with semaphore:
        start = time.monotonic()
        try:
            ptype = proxy_type.lower()
            if ptype in _SOCKS_TYPES:
                connector = ProxyConnector(
                    proxy_type=_SOCKS_TYPES[ptype],
                    host=ip,
                    port=port,
                    ssl=False,
                )
                async with aiohttp.ClientSession(connector=connector) as session:
                    async with session.get(
                        TEST_URL,
                        timeout=aiohttp.ClientTimeout(total=TIMEOUT_SECONDS),
                        ssl=False,
                    ) as resp:
                        if resp.status == 200:
                            elapsed = int((time.monotonic() - start) * 1000)
                            return True, elapsed
            else:
                proxy_url = f"{ptype}://{ip}:{port}"
                connector = aiohttp.TCPConnector(ssl=False)
                async with aiohttp.ClientSession(connector=connector) as session:
                    async with session.get(
                        TEST_URL,
                        proxy=proxy_url,
                        timeout=aiohttp.ClientTimeout(total=TIMEOUT_SECONDS),
                        ssl=False,
                    ) as resp:
                        if resp.status == 200:
                            elapsed = int((time.monotonic() - start) * 1000)
                            return True, elapsed
        except Exception:
            pass
    return False, 0


async def validate_batch(proxies: list[dict]) -> dict[str, int]:
    semaphore = asyncio.Semaphore(VALIDATOR_CONCURRENT)
    results = {"live": 0, "dead": 0}

    tasks = [
        check_proxy(p["ip"], p["port"], p.get("type", "http"), semaphore)
        for p in proxies
    ]
    check_results = await asyncio.gather(*tasks, return_exceptions=True)

    updates = []
    for i, p in enumerate(proxies):
        r = check_results[i]
        if isinstance(r, Exception):
            is_live, speed = False, 0
        else:
            is_live, speed = r
        updates.append((p["ip"], p["port"], is_live, speed))
        if is_live:
            results["live"] += 1
        else:
            results["dead"] += 1

    await asyncio.gather(*[
        update_proxy_check(ip, port, is_live, speed)
        for ip, port, is_live, speed in updates
    ])

    removed = await remove_dead_proxies(PROXY_FAIL_THRESHOLD)
    results["removed"] = removed
    return results


async def run_validation_cycle() -> dict:
    proxies = await get_proxies_to_validate(batch_size=5000)
    if not proxies:
        return {"live": 0, "dead": 0, "removed": 0, "total": 0}
    result = await validate_batch(proxies)
    result["total"] = len(proxies)
    return result
