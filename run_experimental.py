"""
WINDOWS COMMAND RUNNER
Run this with: python run_experimental.py
"""

import os
import subprocess
import sys
from pathlib import Path

# Get the script directory
script_dir = Path(__file__).parent.absolute()

print("=" * 60)
print("EXPERIMENTAL BRANCH SETUP")
print("=" * 60)
print(f"\nCurrent directory: {script_dir}")

# Change to project directory
os.chdir(script_dir)

# Step 1: Check if git repo
print("\n1. Checking git repository...")
result = subprocess.run(["git", "status"], capture_output=True, text=True)
if result.returncode != 0:
    print("❌ Not a git repository. Initializing...")
    subprocess.run(["git", "init"])
    print("✅ Git initialized")
else:
    print("✅ Git repository found")

# Step 2: Create/switch to experimental branch
print("\n2. Creating experimental branch...")
result = subprocess.run(
    ["git", "checkout", "-b", "experimental/local-db-output"],
    capture_output=True,
    text=True
)

if "already exists" in result.stderr or result.returncode != 0:
    print("   Branch exists, switching...")
    subprocess.run(["git", "checkout", "experimental/local-db-output"])
else:
    print("✅ Branch created")

# Step 3: Show branch
result = subprocess.run(["git", "branch"], capture_output=True, text=True)
print(f"\n   Current branch: {result.stdout.strip()}")

# Step 4: Run the experimental test
print("\n" + "=" * 60)
print("RUNNING EXPERIMENTAL TEST")
print("=" * 60)
print("\nConfiguration:")
print("  - Threshold: 0.25 (relaxed)")
print("  - Body: First 5 sentences")
print("  - Database: experimental_subscriptions.db")
print("  - Results: experimental_results/")
print()

response = input("Ready to run test? (y/n): ")
if response.lower() == 'y':
    print("\n🚀 Starting test...")
    subprocess.run([sys.executable, "test_experimental.py"])
else:
    print("\nSkipped. To run manually:")
    print(f"  python test_experimental.py")

print("\n" + "=" * 60)
print("DONE")
print("=" * 60)
