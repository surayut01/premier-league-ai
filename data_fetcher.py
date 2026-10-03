import os
import time
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests
import streamlit as st

from team_names import clean_display_name

API_BASE = "https://api.football-data.org/v4"

# api_id = รหัสลีกของ football-data.org (csv_code ไม่ได้ใช้แล้ว)
LEAGUES = {
    "Premier League": {"api_id": 2021, "csv_code": "E0"},
    "La Liga": {"api_id": 2014, "csv_code": "SP1"},
    "Bundesliga": {"api_id": 2002, "csv_code": "D1"},
}

HISTORY_SEASONS_BACK = 3  # ลองดึงกี่ฤดูกาลล่าสุด (รวมฤดูกาลปัจจุบัน)


class DataError(Exception):
    """ข้อผิดพลาดในการดึงข้อมูล (raise แล้ว Streamlit จะไม่แคชผลล้มเหลวไว้)"""

    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


def _api_key():
    try:
        return st.secrets["FOOTBALL_API_KEY"]
    except Exception:
        return os.environ.get("FOOTBALL_API_KEY")


def _get_matches(api_id, params):
    key = _api_key()
    if not key:
        raise DataError(
            "ไม่พบ API key กรุณาตั้งค่า FOOTBALL_API_KEY ใน .streamlit/secrets.toml "
            "หรือ environment variable"
        )
    try:
        resp = requests.get(
            f"{API_BASE}/competitions/{api_id}/matches",
            headers={"X-Auth-Token": key},
            params=params,
            timeout=12,
        )
    except requests.RequestException as e:
        raise DataError(f"เชื่อมต่อ API ไม่ได้: {e}") from e

    if resp.status_code == 429:
        raise DataError("เรียก API ถี่เกินกำหนด (แพ็กเกจฟรี 10 ครั้ง/นาที) ลองใหม่ภายหลัง", 429)
    if resp.status_code in (401, 403):
        raise DataError(f"API key ไม่ถูกต้องหรือไม่มีสิทธิ์เข้าถึง (HTTP {resp.status_code})", resp.status_code)
    if resp.status_code != 200:
        raise DataError(f"API ตอบกลับผิดปกติ: HTTP {resp.status_code}", resp.status_code)
    return resp.json().get("matches", [])


def _to_bangkok(utc_raw):
    return pd.to_datetime(utc_raw, utc=True).tz_convert("Asia/Bangkok")


def _by_kickoff(matches):
    return sorted(matches, key=lambda m: m.get("utcDate", ""))


# ---------------------------------------------------------------- upcoming
@st.cache_data(ttl=3600, show_spinner=False)
def get_upcoming_fixtures(league_name):
    """5 นัดที่กำลังแข่ง/ใกล้จะแข่งที่สุด"""
    api_id = LEAGUES[league_name]["api_id"]
    statuses = "SCHEDULED,TIMED,IN_PLAY,PAUSED"  # TIMED = นัดที่ยืนยันเวลาแล้ว

    now = datetime.now(timezone.utc)
    params = {
        "status": statuses,
        "dateFrom": now.strftime("%Y-%m-%d"),
        "dateTo": (now + timedelta(days=14)).strftime("%Y-%m-%d"),
    }
    try:
        matches = _get_matches(api_id, params)
    except DataError as e:
        if e.status != 400:
            raise
        matches = []

    if not matches:
        matches = _get_matches(api_id, {"status": statuses})

    status_map = {
        "IN_PLAY": "🔴 กำลังแข่ง (Live)",
        "PAUSED": "⏸ พักครึ่ง",
        "SCHEDULED": "⏳ ยังไม่เริ่ม",
        "TIMED": "⏳ ยังไม่เริ่ม",
    }
    rows = []
    for m in _by_kickoff(matches)[:5]:
        utc_raw = m.get("utcDate")
        time_str = _to_bangkok(utc_raw).strftime("%d/%m/%Y %H:%M น.") if utc_raw else "ไม่ระบุเวลา"
        rows.append({
            "สถานะ": status_map.get(m.get("status"), "⏳ ยังไม่เริ่ม"),
            "วัน-เวลาแข่งขัน (ไทย)": time_str,
            "ทีมเหย้า": clean_display_name(m.get("homeTeam", {}).get("name", "")),
            "ทีมเยือน": clean_display_name(m.get("awayTeam", {}).get("name", "")),
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- historical
def _season_start_years(n=HISTORY_SEASONS_BACK):
    """ปีเริ่มต้นของฤดูกาลล่าสุด n ฤดู เช่น [2024, 2025, 2026] (ฤดูกาลใหม่เริ่มเดือน ส.ค.)"""
    now = datetime.now(timezone.utc)
    start = now.year if now.month >= 8 else now.year - 1
    return list(range(start - n + 1, start + 1))


def _fetch_season(api_id, year):
    """ดึงนัดที่จบแล้วของฤดูกาล year (ติด 429 ให้รอแล้วลองอีกครั้งเดียว)"""
    params = {"season": year, "status": "FINISHED"}
    try:
        return _get_matches(api_id, params)
    except DataError as e:
        if e.status != 429:
            raise
        time.sleep(35)  # โควต้าฟรี 10 ครั้ง/นาที
        return _get_matches(api_id, params)


@st.cache_data(ttl=86400, show_spinner=False)
def get_historical_data(league_name):
    """สถิติย้อนหลังจาก football-data.org (ไม่ต้องพึ่งเว็บ football-data.co.uk)

    ฤดูกาลที่แพ็กเกจของคุณไม่มีสิทธิ์ (HTTP 403) จะถูกข้าม ใช้เท่าที่ดึงได้
    ถ้าไม่ได้สักฤดูกาลจะ raise (Streamlit จะไม่แคชผลล้มเหลว)
    """
    api_id = LEAGUES[league_name]["api_id"]

    rows, errors, used = [], [], []
    for year in _season_start_years():
        try:
            matches = _fetch_season(api_id, year)
        except DataError as e:
            errors.append(f"ฤดูกาล {year}/{str(year + 1)[2:]}: {e}")
            continue
        if not matches:
            continue
        used.append(year)
        for m in matches:
            full = m.get("score", {}).get("fullTime", {})
            h, a = full.get("home"), full.get("away")
            utc_raw = m.get("utcDate")
            if h is None or a is None or not utc_raw:
                continue
            rows.append({
                "Date": pd.to_datetime(utc_raw, utc=True).tz_localize(None),
                "HomeTeam": clean_display_name(m.get("homeTeam", {}).get("name", "")),
                "AwayTeam": clean_display_name(m.get("awayTeam", {}).get("name", "")),
                "FTHG": int(h),
                "FTAG": int(a),
            })

    if not rows:
        detail = "; ".join(errors) if errors else "ไม่พบข้อมูลนัดที่จบแล้ว"
        raise DataError(f"ดึงสถิติย้อนหลังจาก API ไม่สำเร็จ ({detail})")

    return pd.DataFrame(rows).sort_values("Date").reset_index(drop=True)


# ---------------------------------------------------------------- recent results
@st.cache_data(ttl=3600, show_spinner=False)
def get_recent_finished_matches(league_name):
    """5 นัดล่าสุดที่จบแล้ว (เก่า->ใหม่ ถูกกลับให้เป็นใหม่->เก่า)"""
    api_id = LEAGUES[league_name]["api_id"]

    now = datetime.now(timezone.utc)
    params = {
        "status": "FINISHED",
        "dateFrom": (now - timedelta(days=30)).strftime("%Y-%m-%d"),
        "dateTo": now.strftime("%Y-%m-%d"),
    }
    try:
        matches = _get_matches(api_id, params)
    except DataError as e:
        if e.status != 400:
            raise
        matches = []

    if not matches:  # 30 วันนี้ไม่มีนัด (เช่นช่วงพักฤดูกาล)
        matches = _get_matches(api_id, {"status": "FINISHED"})

    rows = []
    for m in reversed(_by_kickoff(matches)):
        full = m.get("score", {}).get("fullTime", {})
        h, a = full.get("home"), full.get("away")
        if h is None or a is None:  # ไม่มีสกอร์ -> ข้าม ไม่เดาเป็น 0
            continue
        utc_raw = m.get("utcDate")
        if not utc_raw:
            continue
        rows.append({
            "วัน-เวลา (ไทย)": _to_bangkok(utc_raw).strftime("%d/%m/%Y %H:%M"),
            "ทีมเหย้า": clean_display_name(m.get("homeTeam", {}).get("name", "")),
            "ทีมเยือน": clean_display_name(m.get("awayTeam", {}).get("name", "")),
            "ผลจริง": f"{h} - {a}",
            "real_home": int(h),
            "real_away": int(a),
            "match_date": pd.to_datetime(utc_raw, utc=True).tz_localize(None),
        })
        if len(rows) == 5:
            break
    return pd.DataFrame(rows)