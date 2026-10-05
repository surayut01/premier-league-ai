"""
หน่วยดึงข้อมูลจาก API: football-data.org
เก็บผลการแข่งขัน (FTHG, FTAG) และโปรแกรมล่วงหน้า
บันทึกไฟล์ลงในโฟลเดอร์ data/api/
"""
import os
import time
import sys
from datetime import datetime, timedelta, timezone
import pandas as pd
import requests

try:
    import streamlit as st
except ImportError:
    class _NoStreamlit:
        secrets = {}
        @staticmethod
        def cache_data(*_a, **_k):
            return lambda f: f
    st = _NoStreamlit()

from config import API_DIR, LEAGUES
from config import current_season_year as _current_season_year
from config import season_start_years as _season_start_years
from team_names import clean_display_name

API_BASE = "https://api.football-data.org/v4"

MIN_FULL_SEASON_MATCHES = 300
SEASON_COLUMNS = ["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG"]

class DataError(Exception):
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
        raise DataError("ไม่พบ API key กรุณาตั้งค่า FOOTBALL_API_KEY")
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
        raise DataError("เรียก API ถี่เกินกำหนด (แพ็กเกจฟรี 10 ครั้ง/นาที)", 429)
    if resp.status_code in (401, 403):
        raise DataError(f"API key ไม่ถูกต้องหรือไม่มีสิทธิ์ (HTTP {resp.status_code})", resp.status_code)
    if resp.status_code != 200:
        raise DataError(f"API ตอบกลับผิดปกติ: HTTP {resp.status_code}", resp.status_code)
    return resp.json().get("matches", [])

def _to_bangkok(utc_raw):
    return pd.to_datetime(utc_raw, utc=True).tz_convert("Asia/Bangkok")

def _by_kickoff(matches):
    return sorted(matches, key=lambda m: m.get("utcDate", ""))

@st.cache_data(ttl=3600, show_spinner=False)
def get_upcoming_fixtures(league_name, limit=5):
    """โปรแกรมที่ยังไม่แข่ง เรียงตามเวลาเตะ limit=None -> คืนทุกนัดที่กำหนดโปรแกรมไว้แล้ว"""
    api_id = LEAGUES[league_name]["api_id"]
    statuses = "SCHEDULED,TIMED,IN_PLAY,PAUSED"
    now = datetime.now(timezone.utc)
    params = {
        "status": statuses,
        "dateFrom": now.strftime("%Y-%m-%d"),
        "dateTo": (now + timedelta(days=14)).strftime("%Y-%m-%d"),
    }
    if limit is None:
        matches = _get_matches(api_id, {"status": statuses})
    else:
        try:
            matches = _get_matches(api_id, params)
        except DataError as e:
            if e.status != 400: raise
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
    for m in _by_kickoff(matches)[:limit]:
        utc_raw = m.get("utcDate")
        time_str = _to_bangkok(utc_raw).strftime("%d/%m/%Y %H:%M น.") if utc_raw else "ไม่ระบุเวลา"
        rows.append({
            "สถานะ": status_map.get(m.get("status"), "⏳ ยังไม่เริ่ม"),
            "วัน-เวลาแข่งขัน (ไทย)": time_str,
            "ทีมเหย้า": clean_display_name(m.get("homeTeam", {}).get("name", "")),
            "ทีมเยือน": clean_display_name(m.get("awayTeam", {}).get("name", "")),
            "_kickoff_utc": pd.to_datetime(utc_raw, utc=True).tz_localize(None) if utc_raw else pd.NaT,
        })
    return pd.DataFrame(rows)

def _season_file(league_name, year, kind="final"):
    code = LEAGUES[league_name]["csv_code"]
    suffix = {"final": ".csv", "live": "_live.csv", "unavailable": ".unavailable"}[kind]
    return API_DIR / f"{code}_{year}{suffix}"

def list_saved_seasons(league_name):
    return [y for y in _season_start_years() if _season_file(league_name, y).exists()]

def _matches_to_df(matches):
    rows = []
    for m in matches:
        full = m.get("score", {}).get("fullTime", {})
        h, a = full.get("home"), full.get("away")
        utc_raw = m.get("utcDate")
        if h is None or a is None or not utc_raw: continue
        rows.append({
            "Date": pd.to_datetime(utc_raw, utc=True).tz_localize(None),
            "HomeTeam": clean_display_name(m.get("homeTeam", {}).get("name", "")),
            "AwayTeam": clean_display_name(m.get("awayTeam", {}).get("name", "")),
            "FTHG": int(h),
            "FTAG": int(a),
        })
    return pd.DataFrame(rows, columns=SEASON_COLUMNS)

def _read_saved(path):
    try:
        if path.exists():
            df = pd.read_csv(path, parse_dates=["Date"])
            if set(SEASON_COLUMNS).issubset(df.columns) and not df.empty:
                return df[SEASON_COLUMNS]
    except Exception:
        pass
    return None

def _save(df, path):
    try:
        API_DIR.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, index=False)
    except OSError:
        pass

def _fetch_season(api_id, year):
    params = {"season": year, "status": "FINISHED"}
    try:
        return _get_matches(api_id, params)
    except DataError as e:
        if e.status != 429: raise
        time.sleep(35)
        return _get_matches(api_id, params)

@st.cache_data(ttl=86400, show_spinner=False)
def get_historical_data(league_name):
    api_id = LEAGUES[league_name]["api_id"]
    current = _current_season_year()
    frames, errors = [], []
    
    API_DIR.mkdir(parents=True, exist_ok=True)

    for year in _season_start_years():
        label = f"{year}/{str(year + 1)[2:]}"
        is_past = year < current

        if is_past:
            saved = _read_saved(_season_file(league_name, year))
            if saved is not None:
                frames.append(saved)
                continue
            if _season_file(league_name, year, "unavailable").exists():
                continue

        try:
            matches = _fetch_season(api_id, year)
        except DataError as e:
            errors.append(f"ฤดูกาล {label}: {e}")
            if is_past and e.status == 403:
                _save(pd.DataFrame({"x": []}), _season_file(league_name, year, "unavailable"))
            elif not is_past:
                fallback = _read_saved(_season_file(league_name, year, "live"))
                if fallback is not None:
                    frames.append(fallback)
            continue

        df = _matches_to_df(matches)
        if df.empty: continue
        if is_past and len(df) >= MIN_FULL_SEASON_MATCHES:
            _save(df, _season_file(league_name, year))
        elif not is_past:
            _save(df, _season_file(league_name, year, "live"))
        frames.append(df)

    if not frames:
        detail = "; ".join(errors) if errors else "ไม่พบข้อมูลนัดที่จบแล้ว"
        raise DataError(f"ดึงสถิติย้อนหลังจาก API ไม่สำเร็จ ({detail})")

    return pd.concat(frames, ignore_index=True).sort_values("Date").reset_index(drop=True)

@st.cache_data(ttl=3600, show_spinner=False)
def get_recent_finished_matches(league_name):
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
        if e.status != 400: raise
        matches = []

    if not matches:
        matches = _get_matches(api_id, {"status": "FINISHED"})

    rows = []
    for m in reversed(_by_kickoff(matches)):
        full = m.get("score", {}).get("fullTime", {})
        h, a = full.get("home"), full.get("away")
        if h is None or a is None: continue
        utc_raw = m.get("utcDate")
        if not utc_raw: continue
        rows.append({
            "วัน-เวลา (ไทย)": _to_bangkok(utc_raw).strftime("%d/%m/%Y %H:%M"),
            "ทีมเหย้า": clean_display_name(m.get("homeTeam", {}).get("name", "")),
            "ทีมเยือน": clean_display_name(m.get("awayTeam", {}).get("name", "")),
            "ผลจริง": f"{h} - {a}",
            "real_home": int(h),
            "real_away": int(a),
            "match_date": pd.to_datetime(utc_raw, utc=True).tz_localize(None),
        })
        if len(rows) == 5: break
    return pd.DataFrame(rows)

if __name__ == "__main__":
    print("ทดสอบดึงข้อมูล API (จะบันทึกลงโฟลเดอร์ data/api/)...")
    for lg in LEAGUES:
        try:
            print(f"{lg}: {len(get_historical_data(lg))} นัด")
        except Exception as e:
            print(f"{lg}: Error -> {e}")