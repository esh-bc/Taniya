BOT_TOKEN = "8840522351:AAGcFDB8gZbbWoDVr_TX841AcGN7sDCXqBk"

ADMIN_ID = 8264404281

MONGODB_URL = "mongodb+srv://singhyashraj:leechbotxesh@cluster0.i1ruod.mongodb.net/?appName=Cluster0"
MONGODB_DB_NAME = "proxyneko"

REDIS_HOST = "redis"
REDIS_PORT = 6379
REDIS_DB = 0

DAILY_LIMITS = {
    "free":  100,
    "basic": 500,
    "pro":   2000,
    "elite": -1,
}

TIER_ACCESS = {
    "free":  ["A", "B"],
    "basic": ["S", "A", "B"],
    "pro":   ["S", "A", "B"],
    "elite": ["S", "A", "B"],
}

SCRAPE_SOURCES = [
    "https://free-proxy-list.net",
    "https://www.proxyscrape.com/free-proxy-list",
    "https://proxylist.geonode.com/api/proxy-list?limit=500&page=1&sort_by=lastChecked&sort_type=desc",
    "https://openproxylist.xyz/http.txt",
    "https://openproxylist.xyz/socks5.txt",
]

DORK_QUERIES = [
    '"proxy list" filetype:txt 2026',
    '"socks5 proxy" inurl:list',
    '"elite proxy list" site:github.com',
    '"free proxy" filetype:txt site:github.com',
    '"http proxy list" 2026',
]

GITHUB_SEARCH_QUERIES = [
    "proxy list txt",
    "socks5 proxy list",
    "elite proxy list 2026",
    "free proxy list updated",
]

VALIDATOR_CONCURRENT = 500
VALIDATION_INTERVAL_MINUTES = 30
SCRAPE_INTERVAL_HOURS = 24
SCRAPE_HOUR_UTC = 3
SCRAPE_MINUTE_UTC = 0

PROGRESS_UPDATE_SECONDS = 30

PROXY_FAIL_THRESHOLD = 3

COUNTRIES = ["US", "JP", "UK", "DE", "FR", "CA", "AU", "NL", "SG", "BR"]
