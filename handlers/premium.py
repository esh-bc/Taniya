from aiogram import Router
from aiogram.types import CallbackQuery

from db.queries import get_or_create_user
from keyboards.builder import premium_kb, back_main_kb

router = Router()


@router.callback_query(lambda c: c.data == "premium")
async def cb_premium(callback: CallbackQuery):
    text = (
        "◈ Premium Plans ne~\n"
        "Taiya-chan worked hard for these ◇\n"
        "Stop being cheap senpai~\n\n"
        "◇ Basic  · $5/mo  · 500/day  · All tiers\n"
        "◈ Pro    · $10/mo · 2000/day · All tiers\n"
        "✦ Elite  · $20/mo · Unlimited · All tiers · Priority"
    )
    await callback.message.edit_text(text, reply_markup=premium_kb())
    await callback.answer()


@router.callback_query(lambda c: c.data in ("buy_basic", "buy_pro", "buy_elite"))
async def cb_buy(callback: CallbackQuery):
    plan_map = {
        "buy_basic": ("Basic", "$5/mo"),
        "buy_pro": ("Pro", "$10/mo"),
        "buy_elite": ("Elite", "$20/mo"),
    }
    plan_name, price = plan_map[callback.data]
    text = (
        f"◈ {plan_name} Plan — {price}\n\n"
        f"Ara ara~ you're serious senpai ◇\n"
        f"Taiya-chan is impressed ne~\n\n"
        f"◇ Contact admin to complete your purchase ◎\n"
        f"✦ @admin_username\n\n"
        f"━━━━━━━━━━━━━━\n"
        f"Mou~ don't keep Taiya-chan waiting~"
    )
    await callback.message.edit_text(text, reply_markup=back_main_kb())
    await callback.answer()
