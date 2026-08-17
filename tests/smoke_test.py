import requests
import uuid
import sys
import os

# Add parent directory to path to access database
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database.mongodb import db_connection

BASE_URL = "http://127.0.0.1:5000"

def run_smoke_test():
    print("Starting End-to-End Sanity Smoke Test...")
    print("-" * 50)
    
    if not db_connection.connect():
        print("FAIL: Could not connect to MongoDB.")
        return
        
    # Generate unique test user
    test_username = f"smoke_test_user_{uuid.uuid4().hex[:6]}"
    test_password = "password123"
    
    session = requests.Session()
    
    # 1. Test Registration
    try:
        print(f"[STEP 1] Registering throwaway account ({test_username})...", end=" ")
        reg_resp = session.post(f"{BASE_URL}/register", data={
            "username": test_username,
            "password": test_password
        })
        if reg_resp.status_code == 200:
            print("PASS")
        else:
            print(f"FAIL (Status: {reg_resp.status_code})")
            return
    except Exception as e:
        print(f"FAIL (Exception: {e})")
        return
        
    # 2. Simulate Manual Approval via MongoDB (Test Helper)
    try:
        print("[STEP 2] Simulating manual admin approval via MongoDB...", end=" ")
        users_coll = db_connection.get_collection('users')
        result = users_coll.update_one({"username": test_username}, {"$set": {"is_approved": True}})
        if result.modified_count == 1:
            print("PASS")
        else:
            print("FAIL (Could not update user in DB)")
            return
    except Exception as e:
        print(f"FAIL (Exception: {e})")
        return
        
    # 3. Test Login
    try:
        print("[STEP 3] Logging in with approved account...", end=" ")
        login_resp = session.post(f"{BASE_URL}/login", data={
            "username": test_username,
            "password": test_password
        })
        if login_resp.status_code == 200:
            print("PASS")
        else:
            print(f"FAIL (Status: {login_resp.status_code})")
            return
    except Exception as e:
        print(f"FAIL (Exception: {e})")
        return
        
    # 4. Hit /articles with filters
    try:
        print("[STEP 4] Hitting /articles with language filter and search query...", end=" ")
        articles_resp = session.get(f"{BASE_URL}/articles?lang=English&q=news")
        if articles_resp.status_code == 200:
            print("PASS")
        else:
            print(f"FAIL (Status: {articles_resp.status_code})")
            return
    except Exception as e:
        print(f"FAIL (Exception: {e})")
        return
        
    # 5. Cleanup Test User
    try:
        print("[STEP 5] Cleaning up throwaway account...", end=" ")
        users_coll.delete_one({"username": test_username})
        print("PASS")
    except Exception as e:
        print(f"FAIL (Exception: {e})")
        return
        
    print("-" * 50)
    print("ALL SMOKE TESTS PASSED SUCCESSFULLY! ✅")

if __name__ == "__main__":
    run_smoke_test()
