# 🚀 Hackathon Orchestrator

A comprehensive platform for managing hackathon operations including candidate sourcing, speaker/jury finding, and outreach automation.

## 🏗️ **Repository Structure**

```
HackathonOrchestrator/
├── 📁 core/                    # Core application logic
│   ├── main.py                # Main orchestrator
│   ├── server.py              # FastAPI backend server
│   ├── tasks.py               # Task definitions
│   ├── agents.py              # Agent definitions
│   ├── tools/                 # Core tools and utilities
│   ├── contacts.csv           # Demo candidate data
│   └── test_comm.py          # Communication testing
├── 📁 services/               # External service integrations
│   ├── __init__.py
│   └── speaker_finder_service.py  # Speaker/jury sourcing service
├── 📁 web/                    # Frontend web interface
│   └── index.html            # Main web application
├── 📁 docs/                   # Documentation and logs
│   └── ACTIVITY_LOG.md       # Development activity log
├── 📁 scripts/                # Utility scripts
├── 📁 static/                 # Static assets (CSS, JS, images)
├── 📁 templates/              # HTML templates
├── requirements.txt           # Python dependencies
└── README.md                 # This file
```

## 🎯 **Features**

### **Candidate Sourcing & Management**
- CSV-based candidate loading and filtering
- Real-time status tracking (Sourced → Contacted → Accepted)
- Live dashboard with SSE updates
- Outreach simulation and automation

### **🎤 Speaker & Jury Finder**
- Topic-based speaker search (AI in FinTech, Cybersecurity, Blockchain, Data Science)
- Google Sheets integration for professional output
- Web scraping with fallback to comprehensive demo data
- Includes NYU contacts: Omar Shehab & Mahmoud Kassem
- Professional spreadsheet formatting with tracking columns

### **🤖 Discord Bot Integration** *(NEW!)*
- AI-powered FAQ auto-replies with semantic search
- Real-time message monitoring and flood detection
- Automatic issue escalation to organizers
- Scheduled announcements from platform events
- Sentiment analysis and urgency detection
- Thread auto-creation and message pinning
- Customizable bot personality and welcome messages
- Webhook integration for platform communication

### **Web Interface**
- Real-time dashboard with live updates
- CSV upload functionality
- Speaker finder integration
- Responsive design with modern UI

## 🚀 **Quick Start**

### **Prerequisites**
- Python 3.10+
- PostgreSQL with pgvector extension (for Discord bot)
- Google Cloud Project (for speaker finder)
- Discord Developer Account (for Discord bot)
- OpenAI API Key (optional, for AI features)

### **1. Setup Environment**
```bash
# Clone and navigate
cd HackathonOrchestrator

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### **2. Start Backend**
```bash
# Option A: Use the startup script (recommended)
python start.py backend

# Option B: Use uvicorn directly
uvicorn core.server:app --reload --port 8001
```

### **3. Start Frontend**
```bash
# Option A: Use the startup script (recommended)
python start.py frontend

# Option B: Use Python's built-in server
cd web && python3 -m http.server 8080
```

### **4. Access Application**
Open your browser to: `http://127.0.0.1:8080/web/index.html?api=8001`

**Note:** The `?api=8001` parameter ensures the frontend connects to the correct backend port.

## 🔧 **Troubleshooting**

### **Frontend and Backend Not Connected**
1. **Check Ports**: Ensure backend is running on port 8001 and frontend on port 8080
2. **Use Correct URL**: Always access via `http://127.0.0.1:8080/web/index.html?api=8001`
3. **Test Connection**: Use the "🧪 Test Backend" button in the web interface
4. **Check Console**: Open browser dev tools to see any JavaScript errors
5. **Verify Backend**: Test backend directly with `curl http://127.0.0.1:8001/health`

### **Common Issues**
- **Port Already in Use**: Kill existing processes or use different ports
- **Import Errors**: Ensure you're in the `HackathonOrchestrator` directory
- **Virtual Environment**: Make sure `.venv` is activated and dependencies are installed

## 🎭 **Demo Mode (No External Credentials)**

### **Candidate Sourcing Demo**
1. Open the web interface
2. Enter a topic (e.g., "AI in FinTech")
3. Click "🚀 Launch Sourcing Agent"
4. Watch real-time updates and status changes

### **Speaker Finder Demo**
1. Use the "🎤 Speaker & Jury Finder" section
2. Enter a topic (e.g., "Cybersecurity")
3. Set desired number of results
4. Click "🔍 Find Speakers"
5. Get a Google Sheets link with formatted data

## 🔐 **Full Functionality Setup**

### **Google Sheets Integration**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Enable Google Sheets API and Google Drive API
3. Create OAuth 2.0 Client ID for Desktop application
4. Download `credentials.json` and place in project root
5. First run will prompt OAuth consent

### **Environment Variables**
Create `.env` file:
```env
# Core Configuration
OPENAI_API_KEY=your_openai_key_here
DUMMY_RUN=0

# Discord Bot Configuration
DISCORD_BOT_TOKEN=your_discord_bot_token
DISCORD_CLIENT_ID=your_discord_client_id
DISCORD_CLIENT_SECRET=your_discord_client_secret

# Database Configuration
DATABASE_URL=postgresql://postgres:password@localhost:5432/hackathon_orchestrator

# Security
JWT_SECRET_KEY=your-secure-jwt-secret
DEFAULT_WEBHOOK_SECRET=your-webhook-secret
```

## 🧪 **Testing**

### **API Health Check**
```bash
curl -s http://127.0.0.1:8001/health
# Expected: {"ok": true}
```

### **Discord Bot Health Check**
```bash
curl -s http://127.0.0.1:8001/discord/health
# Expected: {"ok": true, "service": "discord_bot", "status": "healthy"}
```

### **Speaker Finder Test**
```bash
curl -X POST "http://127.0.0.1:8001/speakers/find" \
  -H "Content-Type: application/json" \
  -d '{"topic":"cybersecurity","max_results":5}'
```

### **Discord Bot Configuration Test**
```bash
curl -X POST "http://127.0.0.1:8001/api/v1/bot/configure" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer demo-token" \
  -d '{"hackathon_id":"test-hack","discord":{"guild_id":"123","installation_id":"test"},"escalation":{"enabled":true,"channel_id":"456"},"logging":{"send_to_platform_webhook":true,"platform_webhook_url":"https://example.com/webhook"}}'
```

### **End-to-End Test**
1. Start both backend and frontend
2. Open web interface
3. Test candidate sourcing flow
4. Test speaker finder functionality
5. Configure and test Discord bot integration

## 🛠️ **Development**

### **Discord Bot Setup**
For detailed Discord bot setup instructions, see [DISCORD_BOT_SETUP.md](DISCORD_BOT_SETUP.md)

Quick start:
```bash
# Initialize Discord bot database
python start_discord_bot.py init

# Start Discord bot service
python start_discord_bot.py start

# Check Discord bot health
python start_discord_bot.py status
```

### **Adding New Services**
1. Create new service in `services/` directory
2. Add endpoints to `core/server.py`
3. Update frontend in `web/index.html`
4. Document in `docs/ACTIVITY_LOG.md`

### **Code Organization**
- **Core Logic**: `core/` - Main application, server, agents
- **Services**: `services/` - External integrations (Google Sheets, APIs)
- **Discord Bot**: `discord_bot/` - Discord bot service, AI processing, database models
- **Web Interface**: `web/` - Frontend HTML/CSS/JS
- **Documentation**: `docs/` - Logs, guides, setup instructions

## 🐛 **Troubleshooting**

### **Common Issues**
- **Port conflicts**: Use different ports or stop existing processes
- **Import errors**: Ensure virtual environment is activated
- **Google API errors**: Check `credentials.json` and `token.json`
- **Frontend not loading**: Verify backend is running on correct port

### **Getting Help**
1. Check `docs/ACTIVITY_LOG.md` for recent changes
2. Verify all services are running
3. Check browser console for frontend errors
4. Review backend server logs

## 📚 **Documentation**

- **`docs/ACTIVITY_LOG.md`**: Complete development history and setup guide
- **API Endpoints**: See `core/server.py` for all available endpoints
- **Service Details**: Check individual service files in `services/`

## 🤝 **Contributing**

1. Follow the established directory structure
2. Update `docs/ACTIVITY_LOG.md` with changes
3. Test both backend and frontend functionality
4. Ensure proper error handling and user feedback

---

**Happy Hacking! 🎉**
