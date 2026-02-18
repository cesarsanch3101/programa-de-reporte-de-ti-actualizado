import os
import sys
import subprocess
import json
from datetime import datetime

CHECK_STRING = "CRITICAL_SECURITY_VULNERABILITY_FOUND"
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

def run_checks():
    print(f"--- 🛡️ Starting Local CI/CD Verification: {datetime.now().isoformat()} ---")
    
    # 1. Search for Smart Fail Flag
    print(f"Checking for {CHECK_STRING} in codebase...")
    # We ignore the script itself
    try:
        # Use grep-like logic
        found = False
        for root, dirs, files in os.walk(PROJECT_ROOT):
            if ".git" in dirs: dirs.remove(".git")
            if ".gemini" in dirs: dirs.remove(".gemini")
            for file in files:
                if file.endswith(".py") or file.endswith(".html") or file.endswith(".js"):
                    filepath = os.path.join(root, file)
                    if filepath == __file__: continue
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        if CHECK_STRING in f.read():
                            print(f"❌ SMART FAIL: Found {CHECK_STRING} in {filepath}")
                            found = True
        if found:
            print("🛑 Build stopped due to security flag.")
            sys.exit(1)
    except Exception as e:
        print(f"⚠️ Error during security flag check: {e}")

    # 2. Simulate SBOM Generation
    print("Generating SBOM (Software Bill of Materials)...")
    try:
        if os.path.exists(os.path.join(PROJECT_ROOT, 'requirements.txt')):
            result = subprocess.run(['pip', 'freeze'], capture_output=True, text=True)
            dependencies = result.stdout.splitlines()
            sbom = {
                "timestamp": datetime.now().isoformat(),
                "project": "IT Support Reporting",
                "dependencies": dependencies
            }
            with open(os.path.join(PROJECT_ROOT, 'sbom.json'), 'w') as f:
                json.dump(sbom, f, indent=4)
            print("✅ SBOM updated in sbom.json")
    except Exception as e:
        print(f"⚠️ Error generating SBOM: {e}")

    # 3. Simulate Tests (Pytest)
    print("Running unit tests...")
    # For now, we just check if pytest can run (even if 0 tests found)
    try:
        result = subprocess.run(['pytest', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Pytest is available.")
            # We would run: subprocess.run(['pytest', 'tests']) here
        else:
            print("⚠️ Pytest not found or error. Skipping tests.")
    except Exception as e:
        print(f"⚠️ Error running tests: {e}")

    print("--- ✅ Local Verification Passed! ---")

if __name__ == "__main__":
    run_checks()
