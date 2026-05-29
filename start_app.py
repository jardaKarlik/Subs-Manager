#!/usr/bin/env python3
"""
Subscription Manager - Complete Application Launcher
Starts both the FastAPI backend and serves the frontend
"""

import subprocess
import sys
import os
import time
import webbrowser
from pathlib import Path

def start_backend():
    """Start the FastAPI backend server"""
    print("[*] Starting FastAPI backend server...")
    backend_process = subprocess.Popen([
        sys.executable, "-m", "uvicorn", "api:app",
        "--host", "0.0.0.0",
        "--port", "8000",
        "--reload"
    ], cwd=Path(__file__).parent)
    return backend_process

def start_frontend():
    """Start a simple HTTP server for the frontend"""
    print("[*] Starting frontend server...")
    frontend_dir = Path(__file__).parent / "frontend"
    frontend_process = subprocess.Popen([
        sys.executable, "-m", "http.server", "3000"
    ], cwd=frontend_dir)
    return frontend_process

def main():
    print("=" * 60)
    print("[*] SUBSCRIPTION MANAGER - FULL STACK APPLICATION")
    print("=" * 60)
    print()

    # Start backend
    backend_process = start_backend()

    # Wait a moment for backend to start
    time.sleep(2)

    # Start frontend
    frontend_process = start_frontend()

    # Wait a moment for frontend to start
    time.sleep(2)

    print()
    print("[OK] Application started successfully!")
    print()
    print("[*] Backend API: http://localhost:8000")
    print("    - API Documentation: http://localhost:8000/docs")
    print("    - Subscriptions: http://localhost:8000/api/subscriptions")
    print()
    print("[*] Frontend UI: http://localhost:3000")
    print()
    print("[*] Features Available:")
    print("    - Email parsing from 3 mailboxes (Gmail + Composio)")
    print("    - Manual subscription entry")
    print("    - Beautiful dashboard with statistics")
    print("    - Category-based organization")
    print("    - Cost tracking (monthly/yearly)")
    print()
    print("[*] Usage:")
    print("    1. Open http://localhost:3000 in browser")
    print("    2. Click Sync to parse emails from mailboxes")
    print("    3. View statistics and manage subscriptions")
    print()
    print("[*] Press Ctrl+C to stop both servers...")

    # Open browser
    try:
        webbrowser.open('http://localhost:3000')
    except:
        pass

    try:
        # Keep both processes running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[*] Shutting down servers...")
        backend_process.terminate()
        frontend_process.terminate()

        # Wait for processes to terminate
        backend_process.wait()
        frontend_process.wait()

        print("[OK] Servers stopped successfully!")

if __name__ == "__main__":
    main()