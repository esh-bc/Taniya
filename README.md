# ProxyNeko ◇ — Taiya-chan's Proxy Bot

A professional Telegram proxy distribution bot with a Japanese girl personality.

## Setup

### 1. Set your bot token

Open `config.py` and replace `YOUR_BOT_TOKEN_HERE` with your real token from [@BotFather](https://t.me/BotFather).

```python
BOT_TOKEN = "1234567890:ABCDEFGHabcdefgh..."
```

### 2. Run with Docker

```bash
cd taniya
docker-compose up -d --build
```

### 3. Check logs

```bash
docker logs -f proxyneko_bot
```

## Admin Commands

| Command | Description |
|---------|-------------|
| `/run` | Start a full scrape immediately |
| `/run 50 s` | Scrape until 50 S-tier proxies found |
| `/run 200 a` | Scrape until 200 A-tier proxies found |
| `/cancel` | Cancel running scrape |
| `/stats` | Full database + system stats |

## User Flow

`/start` → Choose tier → Choose type → Choose country → Choose count → Receive `.txt` file

## Tiers

- **S-Tier** — speed < 100ms, elite anonymity, reliability > 90 (Premium only)
- **A-Tier** — speed < 300ms, elite/anonymous, reliability > 70
- **B-Tier** — speed < 1000ms, live, reliability > 50

## Daily Limits

| Plan | Limit | Tiers |
|------|-------|-------|
| Free | 100/day | A, B |
| Basic | 500/day | All |
| Pro | 2000/day | All |
| Elite | Unlimited | All |

## Scheduled Jobs

- **03:00 UTC daily** — Full scrape of all sources
- **Every 30 min** — Validate stored proxies, remove dead ones (3+ fails)
- **00:00 UTC daily** — Reset all user daily limits
