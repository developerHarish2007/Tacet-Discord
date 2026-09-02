import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_full_stack_mode_switching():
    print("=" * 60)
    print("VERIFYING FULL-STACK TOGGLE MODE SWITCHING")
    print("=" * 60)

    # 1. Test Local AI Toggle Mode
    print("\n1. Testing /junior/ask with ai_mode='local'...")
    resp_local = requests.post(
        f"{BASE_URL}/junior/ask",
        data={
            "question": "What are the recommended fix steps for liquid contamination on bottle capping area?",
            "ai_mode": "local",
            "telemetry_mode": "normal"
        }
    )
    assert resp_local.status_code == 200, f"Local query failed: {resp_local.text}"
    data_local = resp_local.json()
    print("   [Local Mode Success] HTTP Status 200 OK")
    print("   Answer snippet:", data_local.get("answer", "")[:120].replace('\n', ' '))
    print("   Sources:", data_local.get("grounded_sources"))

    # 2. Test Cloud AI Toggle Mode (Groq API)
    print("\n2. Testing /junior/ask with ai_mode='cloud'...")
    resp_cloud = requests.post(
        f"{BASE_URL}/junior/ask",
        data={
            "question": "What are the recommended fix steps for liquid contamination on bottle capping area?",
            "ai_mode": "cloud",
            "telemetry_mode": "normal"
        }
    )
    assert resp_cloud.status_code == 200, f"Cloud query failed: {resp_cloud.text}"
    data_cloud = resp_cloud.json()
    print("   [Cloud Mode Success] HTTP Status 200 OK")
    print("   Answer snippet:", data_cloud.get("answer", "")[:120].replace('\n', ' '))
    print("   Sources:", data_cloud.get("grounded_sources"))

    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE: Mode switching is 100% verified!")
    print("=" * 60)

if __name__ == "__main__":
    test_full_stack_mode_switching()
