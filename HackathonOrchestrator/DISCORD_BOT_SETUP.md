# 🤖 Discord Bot Setup Guide

This guide will help you set up the Discord bot integration for your hackathon platform.

## 📋 Prerequisites

1. **Discord Developer Account**: You need a Discord account and access to the Discord Developer Portal
2. **PostgreSQL Database**: The bot requires a PostgreSQL database with pgvector extension
3. **OpenAI API Key**: For AI-powered features (optional but recommended)
4. **Platform Access**: Administrative access to your hackathon platform

## 🔧 Step 1: Create Discord Application

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name (e.g., "Hackathon Assistant Bot")
3. Navigate to the "Bot" section
4. Click "Add Bot" to create a bot user
5. Copy the **Bot Token** - you'll need this for `DISCORD_BOT_TOKEN`
6. Under "Privileged Gateway Intents", enable:
   - Message Content Intent
   - Server Members Intent (optional)

## 🔑 Step 2: Configure OAuth2

1. In the Discord Developer Portal, go to "OAuth2" → "General"
2. Copy the **Client ID** - you'll need this for `DISCORD_CLIENT_ID`
3. Copy the **Client Secret** - you'll need this for `DISCORD_CLIENT_SECRET`
4. Add redirect URIs for your platform:
   - `https://yourplatform.com/discord/callback`
   - `http://localhost:8001/discord/callback` (for development)

## 🎯 Step 3: Set Bot Permissions

In the OAuth2 → URL Generator section:

### Scopes:
- `bot`
- `applications.commands`

### Bot Permissions:
- Send Messages
- Manage Messages
- Manage Threads
- Read Message History
- Mention Everyone (optional)
- Pin Messages
- Use Slash Commands

Copy the generated URL - this is what organizers will use to add the bot to their servers.

## 🛢️ Step 4: Database Setup

### Install PostgreSQL with pgvector

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo -u postgres psql -c "CREATE EXTENSION vector;"
```

**macOS with Homebrew:**
```bash
brew install postgresql pgvector
brew services start postgresql
psql postgres -c "CREATE EXTENSION vector;"
```

**Docker:**
```bash
docker run -d \
  --name hackathon-postgres \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=hackathon_orchestrator \
  -p 5432:5432 \
  pgvector/pgvector:pg15
```

### Create Database

```sql
CREATE DATABASE hackathon_orchestrator;
CREATE USER hackathon_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE hackathon_orchestrator TO hackathon_user;
\c hackathon_orchestrator
CREATE EXTENSION IF NOT EXISTS vector;
```

## ⚙️ Step 5: Environment Configuration

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Update the environment variables:
   ```env
   # Discord Configuration
   DISCORD_BOT_TOKEN=your_bot_token_from_step_1
   DISCORD_CLIENT_ID=your_client_id_from_step_2
   DISCORD_CLIENT_SECRET=your_client_secret_from_step_2
   
   # Database
   DATABASE_URL=postgresql://hackathon_user:secure_password@localhost:5432/hackathon_orchestrator
   
   # Security
   JWT_SECRET_KEY=generate-a-very-secure-random-key-here
   DEFAULT_WEBHOOK_SECRET=generate-another-secure-secret-for-webhooks
   
   # OpenAI (optional but recommended)
   OPENAI_API_KEY=your_openai_api_key_for_ai_features
   
   # Development
   DEBUG=1
   DUMMY_RUN=0
   ```

## 🚀 Step 6: Install Dependencies and Start Services

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Initialize the database:**
   ```bash
   python -c "from discord_bot.database import init_database; init_database()"
   ```

3. **Start the platform server:**
   ```bash
   python start.py backend
   # or
   uvicorn core.server:app --reload --port 8001
   ```

4. **Start the Discord bot service:**
   ```bash
   python -m discord_bot.bot_service
   ```

## 🎛️ Step 7: Configure Bot via Web Interface

1. Open the platform web interface: `http://localhost:8080/web/index.html?api=8001`
2. Scroll to the "Discord Bot Configuration" section
3. Fill in the required fields:
   - **Hackathon ID**: Unique identifier for your hackathon
   - **Discord Server ID**: The ID of the Discord server where the bot will operate
   - **Installation ID**: Generate a unique installation identifier
   - **Escalation Channel ID**: Discord channel for alerts and escalations

4. Configure features and settings as needed
5. Click "Configure Bot" to save the configuration

## 🧪 Step 8: Test the Integration

### Test Bot Configuration
1. Click "Test Configuration" in the web interface
2. Verify the configuration is valid

### Test FAQ Sync
1. Click "Sync FAQs" to sync your platform's FAQs with the bot
2. Verify FAQs are loaded correctly

### Test Bot Health
1. Click "Check Bot Health" to verify all services are running
2. Check that the database connection is healthy

### Test in Discord
1. Invite the bot to your Discord server using the OAuth2 URL from Step 3
2. Try asking a question that matches your FAQs
3. Verify the bot responds correctly

## 📊 Monitoring and Logs

### View Bot Logs
```bash
tail -f discord_bot.log
```

### Monitor Database
```sql
-- Check bot configurations
SELECT hackathon_id, status, created_at FROM bot_configs;

-- Check recent events
SELECT event_type, created_at, delivered FROM bot_events ORDER BY created_at DESC LIMIT 10;

-- Check FAQ embeddings
SELECT hackathon_id, COUNT(*) as faq_count FROM faq_embeddings GROUP BY hackathon_id;
```

### Web Interface Monitoring
- Real-time Discord events appear in the "Discord Bot Events" panel
- Configuration results are shown in the results panel
- All actions are logged in the main execution log

## 🔧 Troubleshooting

### Common Issues

**Bot not responding to messages:**
- Check that Message Content Intent is enabled
- Verify the bot has required permissions in the Discord server
- Check bot logs for errors

**Configuration fails:**
- Verify all required environment variables are set
- Check database connection
- Ensure JWT tokens are valid

**FAQ sync fails:**
- Verify platform API is accessible
- Check OpenAI API key for embedding generation
- Ensure database has pgvector extension

**Database connection issues:**
- Verify PostgreSQL is running
- Check DATABASE_URL format
- Ensure database user has proper permissions

### Debug Mode

Enable debug mode for verbose logging:
```env
DEBUG=1
LOG_LEVEL=DEBUG
```

### Health Checks

**Platform API:**
```bash
curl http://localhost:8001/health
```

**Discord Bot Health:**
```bash
curl http://localhost:8001/discord/health
```

**Database Health:**
```bash
curl http://localhost:8001/api/v1/bot/stats
```

## 📚 API Reference

### Configuration API

**Configure Bot:**
```bash
curl -X POST http://localhost:8001/api/v1/bot/configure \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_jwt_token" \
  -d @bot_config.json
```

**Get Configuration:**
```bash
curl http://localhost:8001/api/v1/bot/configure?hackathon_id=your_hackathon_id \
  -H "Authorization: Bearer your_jwt_token"
```

### FAQ Sync API

**Sync FAQs:**
```bash
curl -X POST http://localhost:8001/discord/faq/sync \
  -H "Content-Type: application/json" \
  -d '{
    "hackathon_id": "your_hackathon_id",
    "faqs": [
      {
        "question": "What is the WiFi password?",
        "answer": "The WiFi password is hack2024"
      }
    ]
  }'
```

## 🚨 Security Considerations

1. **Keep tokens secure**: Never commit Discord tokens or API keys to version control
2. **Use HTTPS**: Always use HTTPS for webhook URLs in production
3. **Validate permissions**: Ensure the bot only has necessary Discord permissions
4. **Monitor usage**: Keep track of API usage and rate limits
5. **Regular updates**: Keep dependencies updated for security patches

## 🎯 Production Deployment

### Environment Setup
- Use a production PostgreSQL instance
- Set strong, unique passwords for all services
- Use environment-specific JWT secrets
- Enable SSL/TLS for all connections

### Scaling Considerations
- Consider Redis for caching and rate limiting
- Use a load balancer for multiple bot instances
- Monitor database performance with connection pooling
- Implement proper logging and alerting

### Backup Strategy
- Regular database backups
- Configuration backups
- Monitor disk space and performance

## 📞 Support

If you encounter issues:

1. Check the logs first (`discord_bot.log`)
2. Verify your configuration using the health check endpoints
3. Test individual components (database, Discord API, OpenAI API)
4. Review the troubleshooting section above

For additional support, check the project documentation or reach out to the development team.
