"""
หน่วยดึงข้อมูลจากเว็บ FBref (ผ่าน soccerdata) - ฉบับจัดเต็ม (Max Features & Robust Search)
รวมสถิติจากตาราง standard, shooting, keeper และ misc
(อัปเกรดเพิ่มฟีเจอร์เชิงลึก: CS%, SoT%, G/Sh, OppPKatt)
"""
import sys
import warnings
import pandas as pd

warnings.simplefilter(action='ignore', category=FutureWarning)

from config import FBREF_DIR, LEAGUES, current_season_year, season_start_years
from fetch_football_data import DataError
from team_names import clean_display_name

FBREF_SD_LEAGUES = {name: cfg["fbref_id"] for name, cfg in LEAGUES.items()}

# กำหนดคีย์เวิร์ดสำหรับค้นหาคอลัมน์ในแต่ละตารางแบบยืดหยุ่น
_FBREF_RAW = {
    "standard": {
        "Poss": ["Poss", "Possession"], 
        "MP": ["MP", "Matches"], 
        "Nineties": ["90s"],
        "CrdY": ["CrdY", "Yellow Cards"], 
        "CrdR": ["CrdR", "Red Cards"],
        "Age": ["Age"],                            # อายุเฉลี่ย
        "NPG": ["G-PK", "Non-Penalty Goals"],      # ประตูไม่รวมจุดโทษ
        "Ast": ["Ast", "Assists"]                  # แอสซิสต์
    },
    "shooting": {
        "SoT90": ["SoT/90", "Shots on Target"], 
        "GperSoT": ["G/SoT", "Goals per Shot"],
        "Sh90": ["Sh/90", "Shots Total per 90"],   # ปริมาณการยิงทั้งหมด/90นาที
        "Dist": ["Dist", "Average Shot Distance"], # ระยะยิงเฉลี่ย
        "SoT_Pct": ["SoT%", "Shots on Target %"],  # ใหม่: ความแม่นยำยิงเข้ากรอบ (เปอร์เซ็นต์)
        "GperSh": ["G/Sh", "Goals per Shot"]       # ใหม่: ความเด็ดขาดในการจบสกอร์ (ต่อโอกาสยิงทั้งหมด)
    },
    "keeper": {
        "SoTA": ["SoTA", "Shots on Target Against"], 
        "SavePct": ["Save%", "Save Percentage"],
        "KNineties": ["90s"],
        "CS_Pct": ["CS%", "Clean Sheet Percentage"], # ใหม่: เปอร์เซ็นต์คลีนชีต
        "OppPKatt": ["PKatt", "Penalty Kicks Attempted"] # ใหม่: จำนวนจุดโทษที่เสียให้คู่แข่ง (ในตารางโกล)
    },
    "misc": {
        "TklW": ["TklW", "Tackles Won"],           # สกัดบอลชนะ (เกมรับ)
        "Int": ["Int", "Interceptions"],           # ตัดบอล (เกมรับ)
        "Fls": ["Fls", "Fouls Committed"],         # ความดุดัน: ทำฟาวล์
        "Fld": ["Fld", "Fouls Drawn"],             # ความดุดัน: เรียกฟาวล์
        "AerWonPct": ["Won%", "Aerial Win %"]      # ลูกกลางอากาศ
    }
}

# รายชื่อคอลัมน์ผลลัพธ์ที่จะเซฟลง CSV (เรียงกลุ่มให้ดูง่าย และเพิ่มฟีเจอร์ใหม่)
FBREF_SEASON_COLUMNS = [
    "Team", "Season", "MP", "Age", "Poss", 
    "NPG90", "Ast90", "Sh90", "Dist", "SoT90", "GperSoT", "SoT_Pct", "GperSh",  # รุก (เพิ่ม SoT_Pct, GperSh)
    "SoTA90", "SavePct", "CS_Pct", "OppPKatt", "TklW90", "Int90", "AerWonPct",  # รับ (เพิ่ม CS_Pct, OppPKatt)
    "Fls90", "Fld90", "CrdY90", "CrdR90"                                        # ความดุดัน
]

def _fbref_season_file(league_name, year):
    return FBREF_DIR / f"{LEAGUES[league_name]['csv_code']}_season_{year}.csv"

def _find_col(df, targets):
    if isinstance(targets, str):
        targets = [targets]
    for c in df.columns:
        # รวมชื่อ MultiIndex เป็น String เดียวเพื่อให้ค้นหาง่าย
        col_str = " ".join([str(x) for x in (c if isinstance(c, tuple) else (c,))]).lower()
        for t in targets:
            if t.lower() in col_str.split() or t.lower() in col_str:
                return c
    return None

def fetch_fbref_season_stats(league_name, year):
    try:
        import soccerdata as sd
    except ImportError as e:
        raise DataError("ยังไม่ได้ติดตั้ง soccerdata") from e

    season_str = f"{str(year)[-2:]}{str(year+1)[-2:]}"
    fb = sd.FBref(leagues=FBREF_SD_LEAGUES[league_name], seasons=season_str, no_cache=True)
    
    merged = None
    for stat_type, wanted in _FBREF_RAW.items():
        try:
            t = fb.read_team_season_stats(stat_type=stat_type)
        except Exception as e:
            print(f"  ข้ามตาราง {stat_type}: {e}")
            continue
            
        part = pd.DataFrame({"Team": t.index.get_level_values("team")})
        for out_col, targets in wanted.items():
            src = _find_col(t, targets)
            part[out_col] = pd.to_numeric(t[src], errors="coerce").to_numpy() if src is not None else float("nan")
                
        merged = part if merged is None else merged.merge(part, on="Team", how="outer")
        
    if merged is None:
        raise DataError(f"ดึงสถิติ FBref ของ {league_name} {year} ไม่ได้เลย")

    # หาจำนวนเวลาลงเล่น เพื่อนำมาหารสถิติให้เป็นค่าเฉลี่ยต่อ 90 นาที
    n90 = merged.get("Nineties", merged.get("MP", float("nan")))
    def safe_div(col_name):
        return (merged[col_name] / n90) if col_name in merged else float("nan")

    # จัดเตรียมข้อมูลผลลัพธ์
    out = pd.DataFrame({"Team": merged["Team"].apply(clean_display_name), "Season": year})
    out["MP"] = merged.get("MP", float("nan"))
    out["Age"] = merged.get("Age", float("nan"))
    out["Poss"] = merged.get("Poss", float("nan"))
    
    # กลุ่มเกมรุก (เพิ่มสถิติใหม่)
    out["NPG90"] = safe_div("NPG")
    out["Ast90"] = safe_div("Ast")
    out["Sh90"] = merged.get("Sh90", float("nan"))
    out["Dist"] = merged.get("Dist", float("nan"))
    out["SoT90"] = merged.get("SoT90", float("nan"))
    out["GperSoT"] = merged.get("GperSoT", float("nan"))
    out["SoT_Pct"] = merged.get("SoT_Pct", float("nan"))
    out["GperSh"] = merged.get("GperSh", float("nan"))
    
    # กลุ่มเกมรับ (เพิ่มสถิติใหม่)
    kn90 = merged.get("KNineties", n90)
    out["SoTA90"] = (merged["SoTA"] / kn90) if "SoTA" in merged else float("nan")
    out["SavePct"] = merged.get("SavePct", float("nan"))
    out["CS_Pct"] = merged.get("CS_Pct", float("nan"))
    out["OppPKatt"] = merged.get("OppPKatt", float("nan"))
    out["TklW90"] = safe_div("TklW")
    out["Int90"] = safe_div("Int")
    out["AerWonPct"] = merged.get("AerWonPct", float("nan"))
    
    # กลุ่มความดุดัน
    out["Fls90"] = safe_div("Fls")
    out["Fld90"] = safe_div("Fld")
    out["CrdY90"] = safe_div("CrdY")
    out["CrdR90"] = safe_div("CrdR")
    
    return out[FBREF_SEASON_COLUMNS]

def update_fbref(league_name=None, force=False):
    """ดึงฤดูกาลที่จบแล้ว (รวมปีก่อนข้อมูลผลแข่งอีก 1 ปี) ไฟล์ที่มีอยู่แล้วจะข้าม ยกเว้นสั่ง force=True"""
    years = season_start_years()
    wanted = range(years[0] - 1, current_season_year())
    
    FBREF_DIR.mkdir(parents=True, exist_ok=True)
    
    for lg in ([league_name] if league_name else list(LEAGUES)):
        for year in wanted:
            path = _fbref_season_file(lg, year)
            if path.exists() and not force:
                print(f"[FBref] {lg} {year}: มีไฟล์แล้ว ข้าม (ใช้ --force เพื่อดึงใหม่)")
                continue
            try:
                print(f"[FBref] กำลังดึงข้อมูล {lg} {year} (Max Features)...")
                df = fetch_fbref_season_stats(lg, year)
                df.to_csv(path, index=False)
                print(f"  บันทึกสำเร็จ ({len(df)} ทีม) -> มีฟีเจอร์ครบ {len(FBREF_SEASON_COLUMNS)-2} ตัว")
            except DataError as e:
                print(f"  ข้าม ({e})")

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    print("เริ่มการดึงข้อมูล FBref (Max Features + Advanced Stats Version)...")
    update_fbref(args[0] if args else None, force="--force" in sys.argv)