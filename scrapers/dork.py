import aiohttp
import re
from config import DORK_QUERIES

URL_RE = re.compile(r'href="(https?://[^"&]+)"')
YAHOO_URL = "https://search.yahoo.com/search"
DDG_URL = "https://html.duckduckgo.com/html/"


async def _fetch(session: aiohttp.ClientSession, url: str, params: dict) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    try:
        async with session.get(
            url, params=params, headers=headers,
            timeout=aiohttp.ClientTimeout(total=15)
        ) as resp:
            if resp.status == 200:
                return await resp.text(errors="replace")
    except Exception:
        pass
    return ""


async def duckduckgo_search(session: aiohttp.ClientSession, query: str) -> list[str]:
    text = await _fetch(session, DDG_URL, {"q": query})
    urls = URL_RE.findall(text)
    return [u for u in urls if "duckduckgo" not in u and "doubleclick" not in u][:8]


async def yahoo_japan_search(session: aiohttp.ClientSession, query: str) -> list[str]:
    text = await _fetch(session, "https://search.yahoo.co.jp/search", {"p": query})
    urls = URL_RE.findall(text)
    return [u for u in urls if "yahoo" not in u][:8]


async def run_all_dorks(session: aiohttp.ClientSession) -> list[str]:
    all_urls = []
    for query in DORK_QUERIES:
        try:
            ddg_urls = await duckduckgo_search(session, query)
            all_urls.extend(ddg_urls)
        except Exception:
            pass
    try:
        yahoo_urls = await yahoo_japan_search(session, "proxy list socks5 2026 free")
        all_urls.extend(yahoo_urls)
    except Exception:
        pass

    seen = set()
    unique = []
    for u in all_urls:
        if u not in seen:
            seen.add(u)
            unique.append(u)
    return unique
