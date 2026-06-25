from datetime import datetime, timezone, timedelta


def time_until_midnight_utc() -> str:
    now = datetime.now(timezone.utc)
    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    delta = tomorrow - now
    hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes = remainder // 60
    return f"{hours}h {minutes}m"


def time_since(dt: datetime) -> str:
    if dt is None:
        return "never"
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = now - dt
    seconds = int(delta.total_seconds())
    if seconds < 60:
        return f"{seconds}s ago"
    elif seconds < 3600:
        return f"{seconds // 60}m ago"
    elif seconds < 86400:
        return f"{seconds // 3600}h ago"
    else:
        return f"{seconds // 86400}d ago"


def time_until(dt: datetime) -> str:
    if dt is None:
        return "unknown"
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = dt - now
    if delta.total_seconds() <= 0:
        return "now"
    seconds = int(delta.total_seconds())
    if seconds < 3600:
        return f"in {seconds // 60}m"
    elif seconds < 86400:
        return f"in {seconds // 3600}h"
    else:
        return f"in {seconds // 86400}d"


def format_number(n: int) -> str:
    return f"{n:,}"


def elapsed_str(started_at: datetime) -> str:
    if started_at is None:
        return "0s"
    now = datetime.now(timezone.utc)
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)
    delta = now - started_at
    seconds = int(delta.total_seconds())
    minutes, secs = divmod(seconds, 60)
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def tier_label(tier: str) -> str:
    return {"S": "S-Tier", "A": "A-Tier", "B": "B-Tier"}.get(tier.upper(), tier)


def assign_tier(speed: int, anonymity: str, reliability_score: float, is_live: bool) -> str | None:
    anon = anonymity.lower() if anonymity else ""
    if speed < 100 and anon == "elite" and reliability_score > 90:
        return "S"
    if speed < 300 and anon in ("elite", "anonymous") and reliability_score > 70:
        return "A"
    if speed < 1000 and is_live and reliability_score > 50:
        return "B"
    return None
