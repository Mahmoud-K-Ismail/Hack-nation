#!/usr/bin/env python3
"""
Test script to verify all paths and imports are working correctly
after the repository restructuring.
"""

import sys
import os
from pathlib import Path

def test_imports():
    """Test that all critical imports work"""
    print("🧪 Testing imports...")
    
    try:
        # Test core imports
        from core.server import app
        print("✅ core.server imported successfully")
        
        from core.main import run_orchestrator
        print("✅ core.main imported successfully")
        
        from services.speaker_finder_service import speaker_finder_service
        print("✅ services.speaker_finder_service imported successfully")
        
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def test_file_paths():
    """Test that all critical files exist"""
    print("\n📁 Testing file paths...")
    
    critical_files = [
        "core/server.py",
        "core/main.py", 
        "core/tasks.py",
        "services/speaker_finder_service.py",
        "web/index.html",
        "requirements.txt",
        "start.py"
    ]
    
    all_exist = True
    for file_path in critical_files:
        if Path(file_path).exists():
            print(f"✅ {file_path} exists")
        else:
            print(f"❌ {file_path} missing")
            all_exist = False
    
    return all_exist

def test_directory_structure():
    """Test that all directories exist"""
    print("\n📂 Testing directory structure...")
    
    critical_dirs = [
        "core",
        "services", 
        "web",
        "docs",
        "scripts",
        "static",
        "templates"
    ]
    
    all_exist = True
    for dir_name in critical_dirs:
        if Path(dir_name).exists() and Path(dir_name).is_dir():
            print(f"✅ {dir_name}/ directory exists")
        else:
            print(f"❌ {dir_name}/ directory missing")
            all_exist = False
    
    return all_exist

def main():
    """Run all tests"""
    print("🚀 Hackathon Orchestrator - Path & Import Test")
    print("=" * 50)
    
    # Add current directory to Python path
    current_dir = Path(__file__).parent
    if str(current_dir) not in sys.path:
        sys.path.insert(0, str(current_dir))
    
    print(f"📍 Working directory: {os.getcwd()}")
    print(f"📍 Python path includes: {current_dir}")
    
    # Run tests
    imports_ok = test_imports()
    files_ok = test_file_paths()
    dirs_ok = test_directory_structure()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print(f"   Imports: {'✅ PASS' if imports_ok else '❌ FAIL'}")
    print(f"   Files:   {'✅ PASS' if files_ok else '❌ FAIL'}")
    print(f"   Dirs:    {'✅ PASS' if dirs_ok else '❌ FAIL'}")
    
    if all([imports_ok, files_ok, dirs_ok]):
        print("\n🎉 All tests passed! The repository restructuring was successful.")
        print("\n💡 Next steps:")
        print("   1. Start backend: python start.py backend")
        print("   2. Start frontend: python start.py frontend")
        print("   3. Open: http://127.0.0.1:8080/web/index.html?api=8001")
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
        print("\n💡 Troubleshooting:")
        print("   - Ensure you're in the HackathonOrchestrator directory")
        print("   - Check that all files were moved correctly")
        print("   - Verify virtual environment is activated")

if __name__ == "__main__":
    main()
