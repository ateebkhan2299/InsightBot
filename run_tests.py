import subprocess
import sys
import os

def run_step(description, command):
    print("=" * 65)
    print(f"Running: {description}")
    print("=" * 65)
    try:
        # Run process and stream stdout/stderr
        result = subprocess.run(
            command,
            shell=True,
            text=True,
            check=True
        )
        print("\nResult: SUCCESS\n")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\nResult: FAILED (Exit Code: {e.returncode})\n")
        return False

def main():
    print("=" * 65)
    print("      InsightBot — Unified Testing & Verification Suite")
    print("=" * 65)
    
    python_exec = os.path.join(".venv", "Scripts", "python.exe")
    if not os.path.exists(python_exec):
        python_exec = "python"
        
    steps = [
        ("Backend & Interface Unit Tests (Pytest)", f"{python_exec} -m pytest tests/"),
        ("DOM Pattern-Mining Heuristics Accuracy Test", f"{python_exec} tests/evaluate_accuracy.py"),
        ("Access Control & Route Security Authorization Audit", f"{python_exec} C:/Users/USER/.gemini/antigravity/brain/afdf3e9d-b644-42b9-aed8-83471d47e7b8/scratch/test_authorization.py")
    ]
    
    success_count = 0
    for desc, cmd in steps:
        if run_step(desc, cmd):
            success_count += 1
            
    print("=" * 65)
    print(f"Verification Summary: {success_count}/{len(steps)} steps passed.")
    print("=" * 65)
    
    if success_count == len(steps):
        print("ALL TESTS PASSED: InsightBot is verified production ready!")
        sys.exit(0)
    else:
        print("TEST FAILURES ENCOUNTERED: Please resolve findings before shipping.")
        sys.exit(1)

if __name__ == "__main__":
    main()
