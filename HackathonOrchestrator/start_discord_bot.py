#!/usr/bin/env python3
"""
Discord Bot Service Launcher
Provides easy start/stop commands for the Discord bot service.
"""

import os
import sys
import asyncio
import signal
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_dependencies():
    """Check if all required dependencies are available"""
    try:
        import discord
        import sqlalchemy
        import openai
        import psycopg2
        print("✅ All dependencies are available")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Please run: pip install -r requirements.txt")
        return False

def check_environment():
    """Check if all required environment variables are set"""
    required_vars = [
        'DISCORD_BOT_TOKEN',
        'DATABASE_URL',
        'JWT_SECRET_KEY'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please check your .env file or set these environment variables")
        return False
    
    print("✅ Environment variables are configured")
    return True

def check_database():
    """Check database connection and setup"""
    try:
        from discord_bot.database import DatabaseManager
        
        if not DatabaseManager.health_check():
            print("❌ Database connection failed")
            print("Please ensure PostgreSQL is running and DATABASE_URL is correct")
            return False
        
        print("✅ Database connection is healthy")
        return True
    except Exception as e:
        print(f"❌ Database check failed: {e}")
        return False

def init_database():
    """Initialize database tables"""
    try:
        from discord_bot.database import init_database
        init_database()
        print("✅ Database initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False

async def start_bot_service():
    """Start the Discord bot service"""
    try:
        from discord_bot.bot_service import bot_service
        
        print("🚀 Starting Discord bot service...")
        await bot_service.start()
        
    except KeyboardInterrupt:
        print("\n⏹️ Stopping Discord bot service...")
    except Exception as e:
        print(f"❌ Bot service error: {e}")
        return False
    finally:
        try:
            await bot_service.stop()
        except:
            pass
    
    return True

def run_health_checks():
    """Run all health checks"""
    print("🔍 Running health checks...")
    
    checks = [
        ("Dependencies", check_dependencies),
        ("Environment", check_environment),
        ("Database", check_database)
    ]
    
    all_passed = True
    for name, check_func in checks:
        print(f"\n📋 Checking {name}...")
        if not check_func():
            all_passed = False
    
    return all_passed

def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("""
🤖 Discord Bot Service Launcher

Usage:
    python start_discord_bot.py <command>

Commands:
    check       - Run health checks
    init        - Initialize database
    start       - Start the Discord bot service
    dev         - Start in development mode with auto-reload
    status      - Check service status

Examples:
    python start_discord_bot.py check
    python start_discord_bot.py init
    python start_discord_bot.py start
        """)
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "check":
        print("🔍 Running Discord Bot Health Checks\n")
        if run_health_checks():
            print("\n✅ All checks passed! Ready to start the bot service.")
            sys.exit(0)
        else:
            print("\n❌ Some checks failed. Please fix the issues before starting the bot.")
            sys.exit(1)
    
    elif command == "init":
        print("🛠️ Initializing Discord Bot Database\n")
        if check_dependencies() and check_environment():
            if init_database():
                print("\n✅ Database initialization complete!")
                sys.exit(0)
            else:
                print("\n❌ Database initialization failed!")
                sys.exit(1)
        else:
            sys.exit(1)
    
    elif command == "start":
        print("🚀 Starting Discord Bot Service\n")
        
        # Run health checks first
        if not run_health_checks():
            print("\n❌ Health checks failed. Please fix issues before starting.")
            sys.exit(1)
        
        print("\n🤖 Starting Discord bot...")
        try:
            asyncio.run(start_bot_service())
        except KeyboardInterrupt:
            print("\n👋 Bot service stopped by user")
            sys.exit(0)
        except Exception as e:
            print(f"\n❌ Failed to start bot service: {e}")
            sys.exit(1)
    
    elif command == "dev":
        print("🔧 Starting Discord Bot in Development Mode\n")
        
        # Set development environment
        os.environ["DEBUG"] = "1"
        os.environ["LOG_LEVEL"] = "DEBUG"
        
        # Run health checks
        if not run_health_checks():
            print("\n❌ Health checks failed. Please fix issues before starting.")
            sys.exit(1)
        
        print("\n🔧 Starting bot in development mode...")
        print("📝 Debug logging enabled")
        print("🔄 Auto-reload on code changes")
        
        try:
            asyncio.run(start_bot_service())
        except KeyboardInterrupt:
            print("\n👋 Development bot stopped")
            sys.exit(0)
    
    elif command == "status":
        print("📊 Checking Discord Bot Status\n")
        
        try:
            from discord_bot.database import DatabaseManager
            
            # Check database
            db_healthy = DatabaseManager.health_check()
            print(f"Database: {'✅ Healthy' if db_healthy else '❌ Unhealthy'}")
            
            # Get stats
            stats = DatabaseManager.get_stats()
            if stats:
                print(f"Active configurations: {stats.get('active_configs', 0)}")
                print(f"Total events: {stats.get('total_events', 0)}")
                print(f"FAQ embeddings: {stats.get('faq_embeddings', 0)}")
                print(f"Recent messages: {stats.get('recent_messages', 0)}")
            
            # Check if bot process is running (simplified check)
            try:
                import psutil
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    if 'discord_bot' in ' '.join(proc.info.get('cmdline', [])):
                        print(f"Bot process: ✅ Running (PID: {proc.info['pid']})")
                        break
                else:
                    print("Bot process: ❌ Not running")
            except ImportError:
                print("Bot process: ❓ Cannot check (psutil not installed)")
            
        except Exception as e:
            print(f"❌ Status check failed: {e}")
    
    else:
        print(f"❌ Unknown command: {command}")
        print("Run 'python start_discord_bot.py' for usage information")
        sys.exit(1)

if __name__ == "__main__":
    main()
