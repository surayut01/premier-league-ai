"""ทดสอบการเชื่อมต่อ API และไฟล์สถิติ CSV

วิธีใช้:
    python test_api.py     # อ่านคีย์จาก .streamlit/secrets.toml หรือ env FOOTBALL_API_KEY
"""
import os
import sys
import tomllib  # Python 3.11+
from pathlib import Path

import requests

def load_api_key():
    """อ่านคีย์จาก environment ก่อน ถ้าไม่มีให้อ่านจาก .streamlit/secrets.toml"""
    key = os.environ.get("FOOTBALL_API_KEY")
    if key:
        return key
    secrets_path = Path(__file__).parent / ".streamlit" / "secrets.toml"
    if secrets_path.exists():
        with open(secrets_path, "rb") as f:
            return tomllib.load(f).get("FOOTBALL_API_KEY")
    return None


API_KEY = load_api_key()
if not API_KEY:
    sys.exit("ไม่พบ FOOTBALL_API_KEY ทั้งใน environment variable และ .streamlit/secrets.toml")

url = "https://api.football-data.org/v4/competitions/2021/matches?status=FINISHED"
headers = {"X-Auth-Token": API_KEY}

print("กำลังเชื่อมต่อ API...")
try:
    response = requests.get(url, headers=headers, timeout=10)
    print(f"Status Code: {response.status_code}")
    print("โควต้าคงเหลือต่อนาที:", response.headers.get("X-Requests-Available-Minute", "-"))

    if response.status_code == 200:
        matches = response.json().get("matches", [])
        print(f"ดึงข้อมูลสำเร็จ! พบข้อมูลทั้งหมด {len(matches)} นัด")
    else:
        print(f"เกิดข้อผิดพลาดจากเซิร์ฟเวอร์: {response.text}")
except Exception as e:
    print(f"การเชื่อมต่อล้มเหลว (เช็คอินเทอร์เน็ตหรือ Firewall): {e}")

print("\nกำลังทดสอบการดึงข้อมูลย้อนหลังรายฤดูกาล (Premier League)...")
from datetime import datetime, timezone

_now = datetime.now(timezone.utc)
_start = _now.year if _now.month >= 8 else _now.year - 1

for year in range(_start - 3, _start + 1):
    try:
        r = requests.get(
            "https://api.football-data.org/v4/competitions/2021/matches",
            headers=headers, params={"season": year, "status": "FINISHED"}, timeout=15,
        )
        n = len(r.json().get("matches", [])) if r.status_code == 200 else "-"
        print(f"  ฤดูกาล {year}/{str(year + 1)[2:]}: HTTP {r.status_code}, จำนวนนัด: {n}")
    except Exception as e:
        print(f"  ฤดูกาล {year}: ล้มเหลว {e}")