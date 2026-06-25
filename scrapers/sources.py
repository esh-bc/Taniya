import asyncio
import aiohttp
import re
from config import SCRAPE_SOURCES, GITHUB_SEARCH_QUERIES


RAW_PROXY_RE = re.compile(
    r"\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d{2,5})\b"
)

GITHUB_API = "https://api.github.com/search/code"
GITHUB_HEADERS = {
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "ProxyNeko-Bot/1.0",
}

GEONODE_API = "https://proxylist.geonode.com/api/proxy-list"


async def fetch_text(session: aiohttp.ClientSession, url: str, timeout: int = 15) -> str:
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
            if resp.status == 200:
                return await resp.text(errors="replace")
    except Exception:
        pass
    return ""


async def parse_plain_text_proxies(text: str, proxy_type: str = "http") -> list[dict]:
    matches = RAW_PROXY_RE.findall(text)
    proxies = []
    for ip, port_str in matches:
        try:
            port = int(port_str)
            if 1 <= port <= 65535:
                proxies.append({"ip": ip, "port": port, "type": proxy_type, "source": "text"})
        except ValueError:
            pass
    return proxies


async def scrape_free_proxy_list(session: aiohttp.ClientSession) -> list[dict]:
    text = await fetch_text(session, "https://free-proxy-list.net")
    proxies = []
    for match in re.finditer(
        r"<td>(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})</td><td>(\d+)</td><td>([A-Z]{2})</td>.*?<td>(.*?)</td>.*?<td>(yes|no)</td>",
        text,
        re.IGNORECASE,
    ):
        ip, port, country, anonymity_raw, https = match.groups()
        anon_map = {"elite proxy": "elite", "anonymous": "anonymous", "transparent": "transparent"}
        anonymity = anon_map.get(anonymity_raw.lower().strip(), "transparent")
        proxy_type = "https" if https.lower() == "yes" else "http"
        try:
            proxies.append({
                "ip": ip,
                "port": int(port),
                "type": proxy_type,
                "country": country,
                "anonymity": anonymity,
                "source": "free-proxy-list.net",
            })
        except ValueError:
            pass
    return proxies


async def scrape_geonode(session: aiohttp.ClientSession, page: int = 1) -> list[dict]:
    url = f"{GEONODE_API}?limit=500&page={page}&sort_by=lastChecked&sort_type=desc"
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as resp:
            if resp.status == 200:
                data = await resp.json()
                proxies = []
                for item in data.get("data", []):
                    for pt in item.get("protocols", ["http"]):
                        proxies.append({
                            "ip": item.get("ip", ""),
                            "port": int(item.get("port", 0)),
                            "type": pt.lower(),
                            "country": item.get("country", "XX"),
                            "anonymity": item.get("anonymityLevel", "transparent").lower(),
                            "speed": item.get("speed", 9999),
                            "uptime": item.get("upTime", 0),
                            "source": "geonode",
                        })
                return proxies
    except Exception:
        pass
    return []


async def scrape_proxyscrape(session: aiohttp.ClientSession) -> list[dict]:
    urls = [
        "https://api.proxyscrape.com/v3/free-proxy-list/get?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
        "https://api.proxyscrape.com/v3/free-proxy-list/get?request=displayproxies&protocol=socks5&timeout=10000&country=all",
        "https://api.proxyscrape.com/v3/free-proxy-list/get?request=displayproxies&protocol=socks4&timeout=10000&country=all",
    ]
    results = []
    for url in urls:
        proxy_type = "http"
        if "socks5" in url:
            proxy_type = "socks5"
        elif "socks4" in url:
            proxy_type = "socks4"
        text = await fetch_text(session, url)
        results.extend(await parse_plain_text_proxies(text, proxy_type))
    return results


async def scrape_openproxylist(session: aiohttp.ClientSession) -> list[dict]:
    endpoints = [
        ("https://openproxylist.xyz/http.txt", "http"),
        ("https://openproxylist.xyz/https.txt", "https"),
        ("https://openproxylist.xyz/socks4.txt", "socks4"),
        ("https://openproxylist.xyz/socks5.txt", "socks5"),
    ]
    results = []
    for url, ptype in endpoints:
        text = await fetch_text(session, url)
        results.extend(await parse_plain_text_proxies(text, ptype))
    return results


async def search_github_proxy_repos(session: aiohttp.ClientSession) -> list[dict]:
    results = []
    for query in GITHUB_SEARCH_QUERIES[:3]:
        try:
            params = {"q": query, "per_page": 10}
            async with session.get(
                GITHUB_API,
                params=params,
                headers=GITHUB_HEADERS,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for item in data.get("items", [])[:5]:
                        raw_url = item.get("html_url", "").replace(
                            "github.com", "raw.githubusercontent.com"
                        ).replace("/blob/", "/")
                        text = await fetch_text(session, raw_url)
                        if text:
                            found = await parse_plain_text_proxies(text)
                            results.extend(found)
                await asyncio.sleep(1)
        except Exception:
            pass
    return results


async def duckduckgo_dork(session: aiohttp.ClientSession, query: str) -> list[str]:
    url_re = re.compile(r'href="(https?://[^"]+)"')
    search_url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"
    text = await fetch_text(session, search_url)
    urls = url_re.findall(text)
    filtered = [u for u in urls if "duckduckgo" not in u and "ad.doubleclick" not in u]
    return filtered[:5]


async def scrape_from_url(session: aiohttp.ClientSession, url: str) -> list[dict]:
    text = await fetch_text(session, url)
    if not text:
        return []
    return await parse_plain_text_proxies(text)


async def collect_all_sources(session: aiohttp.ClientSession) -> list[dict]:
    tasks = [
        scrape_free_proxy_list(session),
        scrape_geonode(session, 1),
        scrape_geonode(session, 2),
        scrape_proxyscrape(session),
        scrape_openproxylist(session),
        search_github_proxy_repos(session),
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    all_proxies = []
    for r in results:
        if isinstance(r, list):
            all_proxies.extend(r)
    seen = set()
    unique = []
    for p in all_proxies:
        key = (p.get("ip"), p.get("port"))
        if key not in seen and p.get("ip") and p.get("port"):
            seen.add(key)
            unique.append(p)
    return unique
