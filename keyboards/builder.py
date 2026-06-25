from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def _btn(text: str, callback: str, style: str | None = None) -> InlineKeyboardButton:
    kwargs = {"text": text, "callback_data": callback}
    if style:
        kwargs["style"] = style
    return InlineKeyboardButton(**kwargs)


def main_menu_kb(is_premium: bool = False) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            _btn("◇ Get Proxies", "get_proxies", "success"),
            _btn("◈ My Stats", "my_stats", "primary"),
        ],
        [
            _btn("✦ By Country", "by_country", "primary"),
            _btn("◎ Premium~", "premium", "primary"),
        ],
        [
            _btn("◉ Help", "help"),
        ],
    ])


def tier_select_kb(is_free: bool = False) -> InlineKeyboardMarkup:
    rows = []
    if not is_free:
        rows.append([_btn("⬡ S-Tier", "tier_S", "success")])
    rows.append([
        _btn("◈ A-Tier", "tier_A", "primary"),
        _btn("◇ B-Tier", "tier_B"),
    ])
    rows.append([_btn("◇ Back", "back_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def type_select_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            _btn("◎ HTTP", "type_http"),
            _btn("◈ HTTPS", "type_https"),
        ],
        [
            _btn("◇ SOCKS4", "type_socks4"),
            _btn("✦ SOCKS5", "type_socks5", "success"),
        ],
        [
            _btn("◉ All Types", "type_all", "primary"),
        ],
        [_btn("◇ Back", "back_tier")],
    ])


def country_select_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            _btn("◈ All", "country_all", "primary"),
            _btn("◇ US", "country_US"),
            _btn("◎ JP", "country_JP"),
        ],
        [
            _btn("✦ UK", "country_UK"),
            _btn("◉ DE", "country_DE"),
            _btn("⬡ Other", "country_other"),
        ],
        [_btn("◇ Back", "back_type")],
    ])


def count_select_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            _btn("◇ 10", "count_10"),
            _btn("◈ 25", "count_25"),
            _btn("✦ 50", "count_50"),
            _btn("◎ 100", "count_100"),
        ],
        [_btn("◇ Back", "back_country")],
    ])


def after_delivery_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            _btn("◈ Get More~", "get_proxies", "success"),
            _btn("◇ Back", "back_main"),
        ],
    ])


def limit_hit_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            _btn("◎ Upgrade~", "premium", "danger"),
            _btn("◇ Back", "back_main"),
        ],
    ])


def stats_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            _btn("◈ Upgrade~", "premium", "danger"),
            _btn("◇ Back", "back_main"),
        ],
    ])


def premium_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            _btn("◇ Basic", "buy_basic", "primary"),
            _btn("◈ Pro", "buy_pro", "success"),
            _btn("✦ Elite", "buy_elite", "success"),
        ],
        [_btn("◎ Maybe later~", "back_main")],
    ])


def admin_run_kb(job_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [_btn("◎ Cancel", f"admin_cancel_{job_id}", "danger")],
    ])


def back_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [_btn("◇ Back", "back_main")],
    ])
