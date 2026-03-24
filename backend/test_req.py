import requests
import sys

try:
    r = requests.post("http://127.0.0.1:8000/api/v1/verify/start-live", json={"subject_name": "abhi"}, timeout=10)
    print("STATUS:", r.status_code)
    print("TEXT:", r.text)
except Exception as e:
    print("ERROR:", e)
    sys.exit(1)
