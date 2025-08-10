#!/usr/bin/env python3
"""
Startup script for Hackathon Orchestrator
This script handles the import path issues after restructuring
"""

import sys
import os
from pathlib import Path

# Add the current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def start_backend():
    """Start the backend server"""
    try:
        import uvicorn
        from core.server import app
        
        print("🚀 Starting Hackathon Orchestrator Backend...")
        print("📍 Backend will be available at: http://127.0.0.1:8001")
        print("🌐 Frontend should be served at: http://127.0.0.1:8080")
        print("📖 Access the app at: http://127.0.0.1:8080/web/index.html?api=8001")
        print("\n" + "="*60)
        
        uvicorn.run("core.server:app", host="127.0.0.1", port=8001, reload=True)
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure you have activated the virtual environment:")
        print("   source .venv/bin/activate")
        print("   pip install -r requirements.txt")
    except Exception as e:
        print(f"❌ Error starting server: {e}")

def start_frontend():
    """Start the frontend server"""
    try:
        import http.server
        import socketserver
        
        print("🌐 Starting Frontend Server...")
        print("📍 Frontend will be available at: http://127.0.0.1:8080")
        print("📖 Access the app at: http://127.0.0.1:8080/web/index.html?api=8001")
        print("\n" + "="*60)
        
        # Change to web directory and start server
        os.chdir("web")
        with socketserver.TCPServer(("", 8080), http.server.SimpleHTTPRequestHandler) as httpd:
            print("✅ Frontend server started successfully!")
            print("🔄 Press Ctrl+C to stop")
            httpd.serve_forever()
            
    except Exception as e:
        print(f"❌ Error starting frontend: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "frontend":
            start_frontend()
        elif sys.argv[1] == "backend":
            start_backend()
        else:
            print("Usage:")
            print("  python start.py backend   # Start backend server")
            print("  python start.py frontend  # Start frontend server")
            print("  python start.py           # Show this help")
    else:
        print("🚀 Hackathon Orchestrator Startup Script")
        print("="*40)
        print("\nTo start the application:")
        print("\n1. Start Backend (Terminal 1):")
        print("   python start.py backend")
        print("\n2. Start Frontend (Terminal 2):")
        print("   python start.py frontend")
        print("\n3. Open your browser to:")
        print("   http://127.0.0.1:8080/web/index.html?api=8001")
        print("\nOr use the traditional method:")
        print("   Backend: uvicorn core.server:app --reload --port 8001")
        print("   Frontend: cd web && python -m http.server 8080")
