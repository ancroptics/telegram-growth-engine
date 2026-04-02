# 🚀 Telegram Growth Engine Bot

A comprehensive Telegram bot for channel growth management — auto-approve join requests, welcome DMs, broadcast, referral system, analytics, bot cloning, cross-promotion, and more.

## Features
- ✅ Auto-Approve Join Requests (instant/drip/manual)
- 💬 Welcome DMs with media & variables
- 📊 Analytics Dashboard
- 📢 Broadcast System with segmentation
- 🔗 Dual-layer Referral System
- 🔒 Force Subscribe
- 🕐 Drip Approve
- 🔄 Cross-Promotion
- 🤖 Auto-Poster
- 📝 Templates
- 🌐 Multi-Language Welcome
- 🧬 Bot Cloning (white-label)
- 💎 Premium Tiers (Free/Premium/Business)
- 👑 Superadmin Panel

## Setup
1. Clone repo
2. Copy `.env.example` to `.env` and fill in values
3. `pip install -r requirements.txt`
4. Run DB migration: `database/migrations/001_initial_schema.sql`
5. `python bot.py`

## Deploy on Render
1. Connect this repo
2. Set env vars (BOT_TOKEN, DATABASE_URL, SUPERADMIN_IDS)
3. Deploy — bot starts with health server automatically
