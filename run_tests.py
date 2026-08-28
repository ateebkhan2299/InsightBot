import subprocess
import sys
import os


def run_step(description: str, command: str) -> bool:
    print("=" * 65)
    print(f"Running: {description}")
    print("=" * 65)
    try:
        subprocess.run(command, shell=True, text=True, check=True)
        print("\nResult: SUCCESS\n")
        return True
    except subprocess.CalledProcessError as exc:
        print(f"\nResult: FAILED (Exit Code: {exc.returncode})\n")
        return False


def main():
    print("=" * 65)
    print("      InsightBot — Test & Verification Suite")
    print("=" * 65)

    python_exec = sys.executable
    steps = [
        ("Backend & Interface Unit Tests (pytest)", f'"{python_exec}" -m pytest tests/'),
        ("DOM Pattern Extraction Accuracy Evaluation", f'"{python_exec}" tests/evaluate_accuracy.py')
    ]

    success_count = 0
    for desc, cmd in steps:
        if run_step(desc, cmd):
            success_count += 1

    print("=" * 65)
    print(f"Verification Summary: {success_count}/{len(steps)} steps passed.")
    print("=" * 65)

    if success_count == len(steps):
        print("ALL TESTS PASSED: InsightBot is verified production ready.")
        sys.exit(0)
    else:
        print("TEST FAILURES ENCOUNTERED.")
        sys.exit(1)


if __name__ == "__main__":
    main()
