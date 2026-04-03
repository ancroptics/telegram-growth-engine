# Telegram Growth Engine

Multi-tenant Telegram bot for channel growth management.

## Features
- Auto-approve join requests (instant / drip)
- Welcome DMs with multi-language support
- Force-subscribe to other channels
- Broadcast messaging
- Cross-promotion listings
- Analytics & stats dashboard
- Clone bot support
- Premium tiers

## Setup
1. Copy `.env.example` to `.env` and fill values
2. Run migrations against your Supabase DB
3. `pip install -r requirements.txt`
4. `python bot.py`

## Deploy to Render
- Push to GitHub, connect repo in Render
- Set env vars in Render dashboard (never in render.yaml)
- Uses Docker runtime
