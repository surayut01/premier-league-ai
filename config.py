"""ค่ากำหนดกลางของทั้งโปรเจกต์ (ไม่ import streamlit/requests จึงทุกไฟล์เรียกใช้ได้โดยไม่ผูกกัน)

โครงสร้างโฟลเดอร์
  data/api/     ผลแข่งจาก football-data.org   {CODE}_{ปี}.csv, {CODE}_{ปี}_live.csv   (เขียนโดย fetch_football_data.py)
  data/fbref/   สถิติทีมรายฤดูกาลจาก FBref   {CODE}_season_{ปี}.csv                  (เขียนโดย fetch_fbref_data.py)
  data/models/  พารามิเตอร์ที่จูนแล้วของแต่ละลีก                                      (เขียนโดย predictor.py)

ลำดับการไหลของข้อมูล
  fetch_*.py -> data/ -> data_prep.py (Master) -> predictor.py / evaluation.py -> app.py
"""
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
API_DIR = DATA_DIR / "api"
FBREF_DIR = DATA_DIR / "fbref"
MODEL_DIR = DATA_DIR / "models"

# api_id = รหัสลีกของ football-data.org • csv_code = prefix ของไฟล์ • fbref_id = ชื่อลีกของ soccerdata
LEAGUES = {
    "Premier League": {"api_id": 2021, "csv_code": "E0", "fbref_id": "ENG-Premier League"},
    "La Liga": {"api_id": 2014, "csv_code": "SP1", "fbref_id": "ESP-La Liga"},
    "Bundesliga": {"api_id": 2002, "csv_code": "D1", "fbref_id": "GER-Bundesliga"},
}

HISTORY_SEASONS_BACK = 4          # ใช้ผลแข่งกี่ฤดูกาลล่าสุด (รวมฤดูกาลปัจจุบัน)

# สถิติ FBref ที่ใช้เป็นฟีเจอร์ (ต้องมีใน fetch_fbref_data.FBREF_SEASON_COLUMNS)
# คัดจาก 15 ตัวด้วย permutation importance: เก็บเฉพาะที่ช่วยลด log-loss ในอย่างน้อย 2 จาก 3 ลีก
# (ดู select_features.py) ตัวที่ตัดออก: SoT90, GperSoT, NPG90, Sh90, Ast90, TklW90, Int90, Fls90, Fld90, Age
# ถ้าอยากทดลองเพิ่มตัวไหนกลับมา แค่เติมชื่อในรายการนี้ (Dist, AerWonPct ว่างทั้งคอลัมน์ในข้อมูลตอนนี้)
FB_STATS = ["Poss", "SoTA90", "SavePct", "CrdY90", "CrdR90"]


def season_start_years(n=HISTORY_SEASONS_BACK):
    """ปีเริ่มต้นของฤดูกาลล่าสุด n ฤดู เช่น [2023, 2024, 2025, 2026] (ฤดูกาลใหม่เริ่มเดือน ส.ค.)"""
    now = datetime.now(timezone.utc)
    start = now.year if now.month >= 8 else now.year - 1
    return list(range(start - n + 1, start + 1))


def current_season_year():
    return season_start_years(1)[0]


def season_of(dates):
    """ปีเริ่มต้นของฤดูกาลของแต่ละวันที่ (pandas Series ของ datetime)"""
    return np.where(dates.dt.month >= 8, dates.dt.year, dates.dt.year - 1)