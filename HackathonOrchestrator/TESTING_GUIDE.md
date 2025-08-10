# 🧪 Discord Bot Testing Guide

This guide will help you test the Discord bot implementation step by step.

## 🚀 Quick Test Checklist

### ✅ Phase 1: Basic Setup Verification

1. **Check Dependencies**
```bash
python start_discord_bot.py check
```
Expected output: All checks should pass ✅

2. **Test Platform API**
```bash
curl http://localhost:8001/health
```
Expected: `{"ok": true}`

3. **Test Discord Bot Health (without Discord token)**
```bash
curl http://localhost:8001/discord/health
```
Expected: Service status information

---

### ✅ Phase 2: Database Testing

1. **Initialize Database**
```bash
python start_discord_bot.py init
```
Expected: "Database initialization complete!"

2. **Check Database Connection**
```bash
python start_discord_bot.py status
```
Expected: Database should show as "Healthy" ✅

---

### ✅ Phase 3: API Testing (No Discord Required)

1. **Test Bot Configuration API**
```bash
curl -X POST "http://localhost:8001/api/v1/bot/configure" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer demo-token" \
  -d '{
    "hackathon_id": "test-hackathon-2024",
    "discord": {
      "guild_id": "123456789012345678",
      "installation_id": "test-installation"
    },
    "features": {
      "faq_autoreply": true,
      "flood_detection": true,
      "escalation": true,
      "scheduled_announcements": true,
      "thread_autocreate": true,
      "sentiment_detection": true,
      "pin_auto_answers": true
    },
    "escalation": {
      "enabled": true,
      "channel_id": "987654321012345678",
      "escalation_threshold": 0.7,
      "notify_roles": []
    },
    "faq": {
      "source": "platform",
      "auto_sync": true,
      "sync_interval_minutes": 15
    },
    "schedule": {
      "source": "platform",
      "timezone": "UTC",
      "reminder_lead_minutes": [10, 60, 1440]
    },
    "embeddings": {
      "vector_store": "pgvector",
      "similarity_threshold": 0.78
    },
    "personality": {
      "tone": "casual",
      "welcome_message": "Welcome to our test hackathon! 🎉"
    },
    "logging": {
      "send_to_platform_webhook": true,
      "platform_webhook_url": "https://httpbin.org/post"
    }
  }'
```

Expected Response:
```json
{
  "status": "ok",
  "hackathon_id": "test-hackathon-2024",
  "config_id": "some-uuid",
  "message": "Configuration created.",
  "applied_at": "2024-XX-XXTXX:XX:XX"
}
```

2. **Test Configuration Retrieval**
```bash
curl "http://localhost:8001/api/v1/bot/configure?hackathon_id=test-hackathon-2024" \
  -H "Authorization: Bearer demo-token"
```

Expected: Returns the configuration you just created

3. **Test FAQ Endpoints**
```bash
# Get mock FAQs
curl -X POST "http://localhost:8001/hackathon/test-hackathon-2024/faq"

# Test FAQ sync
curl -X POST "http://localhost:8001/discord/faq/sync" \
  -H "Content-Type: application/json" \
  -d '{
    "hackathon_id": "test-hackathon-2024",
    "faqs": [
      {
        "id": "1",
        "question": "What is the WiFi password?",
        "answer": "The WiFi password is TestHack2024"
      },
      {
        "id": "2", 
        "question": "When does the hackathon start?",
        "answer": "The hackathon starts at 6 PM on Friday"
      }
    ]
  }'
```

---

### ✅ Phase 4: Web Interface Testing

1. **Start the Platform**
```bash
# Terminal 1: Start backend
python start.py backend

# Terminal 2: Start frontend  
python start.py frontend
```

2. **Open Web Interface**
```
http://localhost:8080/web/index.html?api=8001
```

3. **Test Discord Bot Configuration**
- Scroll to "Discord Bot Configuration" section
- Fill in the form with test data:
  - Hackathon ID: `test-hackathon-2024`
  - Discord Server ID: `123456789012345678`
  - Installation ID: `test-installation`
  - Escalation Channel ID: `987654321012345678`
- Click "⚙️ Configure Bot"
- Expected: Green success message with configuration details

4. **Test Other Web Features**
- Click "🧪 Test Configuration" - should show config test results
- Click "🔄 Sync FAQs" - should sync the test FAQs
- Click "❤️ Check Bot Health" - should show service health

---

### ✅ Phase 5: Mock Discord Bot Testing (Advanced)

If you want to test the bot logic without setting up a real Discord bot:

1. **Create Test Script**
```python
# test_bot_logic.py
import asyncio
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from discord_bot.ai_processor import AIProcessor
from discord_bot.database import SessionLocal
from discord_bot.models import FAQEmbedding

async def test_ai_processor():
    """Test AI processing without Discord"""
    processor = AIProcessor()
    
    # Test message analysis
    print("Testing message analysis...")
    analysis = await processor.analyze_message("I'm having trouble with WiFi, it's not working!")
    print(f"Analysis: {analysis}")
    
    # Test FAQ matching (mock mode)
    print("\nTesting FAQ matching...")
    match = await processor.find_faq_match("What's the WiFi password?", "test-hackathon-2024")
    print(f"FAQ Match: {match}")
    
    # Test flood summarization
    print("\nTesting flood summarization...")
    messages = [
        "WiFi not working",
        "Can't connect to internet", 
        "WiFi password doesn't work",
        "Internet is down"
    ]
    summary = await processor.summarize_flood(messages)
    print(f"Flood Summary: {summary}")

if __name__ == "__main__":
    asyncio.run(test_ai_processor())
```

2. **Run the Test**
```bash
python test_bot_logic.py
```

Expected Output:
```
Testing message analysis...
Analysis: {'sentiment_score': -0.6, 'urgency_score': 0.8, 'category': 'complaint'}

Testing FAQ matching...
FAQ Match: {'question': "What's the WiFi password?", 'answer': 'The WiFi network is...', 'similarity': 0.85}

Testing flood summarization...
Flood Summary: Multiple participants are experiencing WiFi connectivity issues...
```

---

### ✅ Phase 6: Full Discord Integration (Optional)

If you want to test with a real Discord bot:

1. **Set Up Discord Bot** (Follow DISCORD_BOT_SETUP.md)

2. **Update Environment**
```env
DISCORD_BOT_TOKEN=your_real_bot_token
DISCORD_CLIENT_ID=your_client_id
DISCORD_CLIENT_SECRET=your_client_secret
```

3. **Start Bot Service**
```bash
python start_discord_bot.py start
```

4. **Test in Discord**
- Invite bot to test server
- Ask a question: "What's the WiFi password?"
- Bot should respond with FAQ answer
- Try asking multiple similar questions to test flood detection
- Post a complaint message to test escalation

---

## 🔍 Troubleshooting

### Common Issues & Solutions

**❌ "Database connection failed"**
```bash
# Check if PostgreSQL is running
brew services start postgresql  # macOS
sudo systemctl start postgresql  # Linux

# Or use Docker
docker run -d --name test-postgres -e POSTGRES_PASSWORD=password -p 5432:5432 postgres:15
```

**❌ "Discord bot modules not available"**
```bash
pip install discord.py sqlalchemy psycopg2-binary pgvector
```

**❌ "JWT verification failed"**
- The demo uses `Bearer demo-token` for testing
- In production, you'd generate real JWT tokens

**❌ "OpenAI API errors"**
- The system works in mock mode without OpenAI
- Set `OPENAI_API_KEY` for full AI features

**❌ "Port already in use"**
```bash
# Find and kill process using port 8001
lsof -ti:8001 | xargs kill -9
```

### Debugging Commands

```bash
# Check all services
python start_discord_bot.py status

# View logs
tail -f discord_bot.log

# Test database directly
python -c "from discord_bot.database import DatabaseManager; print(DatabaseManager.get_stats())"

# Test webhook delivery
curl -X POST "http://localhost:8001/discord/events/webhook" \
  -H "Content-Type: application/json" \
  -d '{"event": "test", "hackathon_id": "test"}'
```

---

## ✅ Expected Test Results

After running all tests, you should see:

1. **✅ All health checks pass**
2. **✅ Database initialized and connected**
3. **✅ Configuration API working**
4. **✅ FAQ sync functional**
5. **✅ Web interface responsive**
6. **✅ Mock AI processing working**
7. **✅ Webhook delivery successful**

## 🎯 Success Criteria

- [ ] Platform starts without errors
- [ ] Database health check passes
- [ ] Bot configuration API accepts and stores configs
- [ ] FAQ sync processes test data
- [ ] Web interface shows Discord bot section
- [ ] All API endpoints return expected responses
- [ ] Mock AI processing returns realistic results
- [ ] Webhook events are logged and delivered

If all tests pass, your Discord bot implementation is working correctly! 🎉
