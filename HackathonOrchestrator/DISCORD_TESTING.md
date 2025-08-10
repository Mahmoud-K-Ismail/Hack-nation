# 🧪 Discord Features Testing (Quick Guide)

This guide shows how to test the Discord bot features locally without a live Discord bot. It uses the built-in synthetic data and endpoints.

## Prerequisites
- Backend running on port 8001
- Frontend running on port 8080
- Virtualenv activated and dependencies installed

Start services:
```bash
# Backend
python start.py backend

# Frontend (in another terminal)
python start.py frontend
```

## Web UI Tests
- Main Dashboard: `http://localhost:8080/index.html?api=8001`
- Discord Bot Page: `http://localhost:8080/bot.html?api=8001`

On the bot page:
- Enter Hackathon ID (e.g., `ai-revolution-2024`)
- Use “❤️ Check Bot Health” (expects OK in mock mode)
- Use “🔄 Sync FAQs” (loads synthetic FAQs into the bot service when available)

## API Smoke Tests
Health checks:
```bash
curl -s http://localhost:8001/health
curl -s http://localhost:8001/discord/health
```

Synthetic data endpoints:
```bash
# 15 synthetic FAQs
curl -s -X POST "http://localhost:8001/hackathon/ai-revolution-2024/faq" | jq '.count,.source'

# 13 schedule events
curl -s -X POST "http://localhost:8001/hackathon/ai-revolution-2024/schedule" | jq '.count,.source'
```

Bot configuration API (enabled when Discord modules are available):
```bash
curl -s -X POST "http://localhost:8001/api/v1/bot/configure" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer demo-token" \
  -d '{
    "hackathon_id": "ai-revolution-2024",
    "discord": {"guild_id": "123", "installation_id": "install_1"},
    "escalation": {"enabled": true, "channel_id": "456"}
  }'
```

## Synthetic Test Suite (CLI)
Run the comprehensive local tests:
```bash
python test_bot_with_data.py
```
- Exercises: FAQ matching, flood detection, sentiment analysis, schedule inspection

View a summary of the synthetic data:
```bash
python view_test_data.py
```

## Common Issues
- “Discord bot modules not available”: install deps `pip install discord.py sqlalchemy psycopg2-binary pgvector`
- Port busy: `lsof -ti :8001 | xargs kill -9`
- Use the correct URL (no `/web/` prefix):
  - `http://localhost:8080/index.html?api=8001`
  - `http://localhost:8080/bot.html?api=8001`

## Optional: Real Discord Bot
If you want to test with a real bot, follow `DISCORD_BOT_SETUP.md`, then:
```bash
python start_discord_bot.py init
python start_discord_bot.py start
```
Invite the bot to a test server and ask FAQ-style questions.
