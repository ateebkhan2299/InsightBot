import os
import sys
import uuid
import requests

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database.mongodb import db_connection

BASE_URL = "http://127.0.0.1:5000"


def run_smoke_test():
    print("Starting End-to-End Smoke Test...")
    print("-" * 50)

    if not db_connection.connect():
        print("FAIL: Could not connect to MongoDB.")
        return

    test_username = f"smoke_user_{uuid.uuid4().hex[:6]}"
    test_password = "password123"
    session = requests.Session()

    try:
        print(f"[1/5] Registering account ({test_username})...", end=" ")
        reg_resp = session.post(f"{BASE_URL}/register", data={"username": test_username, "password": test_password})
        if reg_resp.status_code == 200:
            print("PASS")
        else:
            print(f"FAIL ({reg_resp.status_code})")
            return
    except Exception as exc:
        print(f"FAIL ({exc})")
        return

    try:
        print("[2/5] Approving account...", end=" ")
        users_coll = db_connection.get_collection('users')
        res = users_coll.update_one({"username": test_username}, {"$set": {"approved": True}})
        if res.modified_count == 1:
            print("PASS")
        else:
            print("FAIL")
            return
    except Exception as exc:
        print(f"FAIL ({exc})")
        return

    try:
        print("[3/5] Logging in...", end=" ")
        login_resp = session.post(f"{BASE_URL}/login", data={"username": test_username, "password": test_password})
        if login_resp.status_code == 200:
            print("PASS")
        else:
            print(f"FAIL ({login_resp.status_code})")
            return
    except Exception as exc:
        print(f"FAIL ({exc})")
        return

    try:
        print("[4/5] Testing news explorer search...", end=" ")
        resp = session.get(f"{BASE_URL}/articles?lang=English&q=news")
        if resp.status_code == 200:
            print("PASS")
        else:
            print(f"FAIL ({resp.status_code})")
            return
    except Exception as exc:
        print(f"FAIL ({exc})")
        return

    try:
        print("[5/5] Cleaning up test account...", end=" ")
        users_coll.delete_one({"username": test_username})
        print("PASS")
    except Exception as exc:
        print(f"FAIL ({exc})")
        return

    print("-" * 50)
    print("ALL SMOKE TESTS PASSED!")


if __name__ == "__main__":
    run_smoke_test()
