"""
Configuration file for Hackathon Orchestrator
Centralized settings for easy maintenance
"""

import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent
CORE_DIR = BASE_DIR / "core"
SERVICES_DIR = BASE_DIR / "services"
WEB_DIR = BASE_DIR / "web"
DOCS_DIR = BASE_DIR / "docs"

# Server configuration
BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 8001
FRONTEND_PORT = 8080

# API configuration
API_BASE_URL = f"http://{BACKEND_HOST}:{BACKEND_PORT}"
FRONTEND_URL = f"http://{BACKEND_HOST}:{FRONTEND_PORT}"

# Google API configuration
GOOGLE_CREDENTIALS_FILE = BASE_DIR / "credentials.json"
GOOGLE_TOKEN_FILE = BASE_DIR / "token.json"

# Demo data configuration
DEMO_TOPICS = [
    "AI in FinTech",
    "Cybersecurity", 
    "Blockchain",
    "Data Science"
]

# Speaker finder configuration
DEFAULT_MAX_RESULTS = 20
MAX_RESULTS_LIMIT = 50

# File paths
CONTACTS_CSV = CORE_DIR / "contacts.csv"
WEB_INDEX = WEB_DIR / "index.html"

# Environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DUMMY_RUN = os.getenv("DUMMY_RUN", "1")

# Discord Bot configuration
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "")

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/hackathon_orchestrator")

# JWT configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-this")
PLATFORM_API_TOKEN = os.getenv("PLATFORM_API_TOKEN", "")

# Webhook configuration
DEFAULT_WEBHOOK_SECRET = os.getenv("DEFAULT_WEBHOOK_SECRET", "")

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Development settings
DEBUG = os.getenv("DEBUG", "1").lower() in ("1", "true", "yes")
RELOAD = DEBUG

def get_web_url(api_port=None):
    """Get the web interface URL with optional API port override"""
    api_port = api_port or BACKEND_PORT
    return f"{FRONTEND_URL}/web/index.html?api={api_port}"

def get_api_url(endpoint=""):
    """Get the API URL for a given endpoint"""
    return f"{API_BASE_URL}/{endpoint.lstrip('/')}"

def ensure_directories():
    """Ensure all required directories exist"""
    for directory in [CORE_DIR, SERVICES_DIR, WEB_DIR, DOCS_DIR]:
        directory.mkdir(exist_ok=True)
