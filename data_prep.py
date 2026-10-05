"""หน่วยเตรียมและประกอบร่างข้อมูล -> Master DataFrame (1 แถว = 1 นัด)

(อัปเกรด 🌟: Advanced Football Context & Contextual Scaling)
- แยก AttackElo / DefenseElo เพื่อจับทางบอลบุกและบอลอุด
- Dynamic K-Factor (Crisis Detector) หักคะแนนทีมใหญ่ฟอร์มตก
- แยกคำนวณฟอร์ม 5 นัดในบ้าน (HomeGF_Home) และนอกบ้าน (AwayGA_Away)
- Contextual Scaling (หักเปอร์เซ็นต์ครองบอลถ้าเจอทีมที่ Elo ห่างกันมาก)
"""
import glob
from pathlib import Path

import numpy as np
import pandas as pd

from config import API_DIR, DATA_DIR, FB_STATS, FBREF_DIR, LEAGUES, season_of
from team_names import resolve_fbref_team, resolve_team

# ---------------------------------------------------------------- พารามิเตอร์ Elo / rolling
ELO_START, ELO_NEWCOMER = 1500.0, 1450.0
ELO_HOME_ADV = 65.0
ELO_SEASON_REGRESS = 0.25          
SEASON_GAP_DAYS = 60
ROLL_N, ROLL_MIN = 5, 3
REST_CAP = 14

# 🌟 พารามิเตอร์ใหม่สำหรับ Dynamic Rating (Crisis Detector & Contextual Scaling)
ELO_K_NORMAL = 20.0        # K-factor ทีมทั่วไป
ELO_K_TIER1_NORMAL = 10.0  # K-factor ทีมใหญ่ (Tier 1) ตอนปกติ (แพ้แล้วคะแนนไม่ค่อยลด)
ELO_K_TIER1_CRISIS = 35.0  # K-factor ทีมใหญ่ (Tier 1) ตอนวิกฤต (คะแนนร่วงดิ่งพสุธา)
CRISIS_PPM5_THRESHOLD = 1.0 # ถ้าแต้มเฉลี่ย 5 นัดของทีมใหญ่ <= 1.0 จะเปิดโหมดวิกฤตทันที

FB_FLAGS = ["HomeNoPrev", "AwayNoPrev"]  
LEAGUE_AVG_GOALS, LEAGUE_AVG_PTS = 1.4, 1.37   

# 🌟 อัปเดตรายการฟีเจอร์ที่จะส่งให้โมเดล Random Forest เทรน
BASE_FEATURES = (
    ["Home_AttackElo", "Home_DefenseElo", "Away_AttackElo", "Away_DefenseElo", "EloDiff", "HomeRestDays", "AwayRestDays"]
    + [f"{s}_{k}5" for s in ("Home", "Away") for k in ("GA", "PPM")]
    + ["HomeGF_Home", "AwayGA_Away"] # ฟีเจอร์ใหม่: สิงห์สนามศุภฯ
)
FBREF_FEATURES = [f"{s}_Prev{k}" for s in ("Home", "Away") for k in FB_STATS] + ["Home_ContextPoss", "Away_ContextPoss"]

# ---------------------------------------------------------------- โหลดไฟล์ดิบ
def load_results(code, api_dir=API_DIR):
    files = sorted(glob.glob(str(Path(api_dir) / f"{code}_*.csv")))
    frames = [pd.read_csv(f, parse_dates=["Date"]) for f in files]
    frames = [f for f in frames if not f.empty]
    if not frames:
        raise FileNotFoundError(f"ไม่พบไฟล์ {code}_*.csv ใน {api_dir} (รัน python fetch_football_data.py ก่อน)")
    df = pd.concat(frames, ignore_index=True)
    df = df.dropna(subset=["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG"])
    df = df.drop_duplicates(["Date", "HomeTeam", "AwayTeam"], keep="last")
    return df[["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG"]].sort_values("Date").reset_index(drop=True)

def find_fbref_files(code, fbref_dir=FBREF_DIR):
    files = sorted(glob.glob(str(Path(fbref_dir) / f"{code}_season_*.csv")))
    if files:
        return files, None
    flat = sorted(glob.glob(str(DATA_DIR / f"{code}_season_*.csv")))
    if flat:
        return flat, f"พบไฟล์ FBref ใน {DATA_DIR} (ใช้งานได้) แต่ควรย้ายไปไว้ที่ {Path(fbref_dir)}"
    return [], None

def load_fbref(code, known_teams, fbref_dir=FBREF_DIR):
    files, _ = find_fbref_files(code, fbref_dir)
    if not files:
        return None, []
    fb = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    known = list(known_teams)
    mapping, unmatched = {}, []
    for name in fb["Team"].dropna().unique():
        hit = resolve_fbref_team(name, known)
        if hit is None:
            unmatched.append(name)
        mapping[name] = hit
    latest = set(fb.loc[fb["Season"] == fb["Season"].max(), "Team"])
    unmatched = [n for n in unmatched if n in latest]
    fb["Team"] = fb["Team"].map(mapping)
    fb = fb.dropna(subset=["Team", "Season"])
    fb["Season"] = fb["Season"].astype(int)
    keep = []
    for c in FB_STATS:
        if c in fb:
            fb[c] = pd.to_numeric(fb[c], errors="coerce")
            if fb[c].notna().any():
                keep.append(c)
    fb = fb.drop_duplicates(["Team", "Season"], keep="last")
    return fb[["Team", "Season"] + keep], sorted(set(unmatched))

def fbref_missing_seasons(results, fbref):
    have = set(fbref["Season"]) if fbref is not None else set()
    need = {int(s) - 1 for s in np.unique(season_of(pd.to_datetime(results["Date"])))}
    return sorted(need - have)

# ---------------------------------------------------------------- Elo (🌟 อัปเกรด Attack/Defense Elo & Crisis Detector)
def compute_elo(df, long_df=None):
    """คืนค่า AttackElo และ DefenseElo แยกกัน และมีระบบตรวจจับทีมใหญ่วิกฤต (Crisis Detector)"""
    d = df.sort_values("Date", kind="stable").reset_index(drop=True)
    # เตรียม Dictionary แยกสาย
    attack_ratings = {}
    defense_ratings = {}
    last_played = None
    
    # ดึงค่า PPM5 มาจาก long_df (ถ้ามี) เพื่อใช้เช็คฟอร์มวิกฤต (Crisis)
    ppm_history = {}
    if long_df is not None:
        for r in long_df.itertuples(index=False):
            if r.PPM5 is not np.nan:
                ppm_history[f"{r.Team}_{r.Date.date()}"] = r.PPM5

    t0 = d["Date"].min()
    start_pool_until = t0 + pd.Timedelta(days=SEASON_GAP_DAYS)
    
    h_atk, a_atk = np.empty(len(d)), np.empty(len(d))
    h_def, a_def = np.empty(len(d)), np.empty(len(d))

    def get_rtg(team, when, r_dict):
        if team not in r_dict:
            r_dict[team] = ELO_START if when <= start_pool_until else ELO_NEWCOMER
        return r_dict[team]
        
    def get_k_factor(team, date, current_elo):
        """เช็คว่าเป็นทีม Tier 1 หรือไม่ และกำลังฟอร์มตก (PPM5 <= 1.0) หรือเปล่า"""
        ppm = ppm_history.get(f"{team}_{date.date()}", 1.5)
        # ตีความว่าเป็น Tier 1 ถ้าค่าเฉลี่ย Elo (รุก+รับ) สูงกว่า 1700
        is_tier_1 = current_elo > 1700 
        
        if is_tier_1:
            if ppm <= CRISIS_PPM5_THRESHOLD:
                return ELO_K_TIER1_CRISIS # วิกฤต! คะแนนไหลรูด
            else:
                return ELO_K_TIER1_NORMAL # ปกติล้มยาก
        return ELO_K_NORMAL

    for i, r in enumerate(d.itertuples(index=False)):
        played = pd.notna(r.FTHG) and pd.notna(r.FTAG)
        if played and last_played is not None and (r.Date - last_played).days > SEASON_GAP_DAYS:
            for t in attack_ratings:                                
                attack_ratings[t] = (1 - ELO_SEASON_REGRESS) * attack_ratings[t] + ELO_SEASON_REGRESS * ELO_START
                defense_ratings[t] = (1 - ELO_SEASON_REGRESS) * defense_ratings[t] + ELO_SEASON_REGRESS * ELO_START
                
        # ดึงเรตติ้งปัจจุบัน
        rh_atk, ra_atk = get_rtg(r.HomeTeam, r.Date, attack_ratings), get_rtg(r.AwayTeam, r.Date, attack_ratings)
        rh_def, ra_def = get_rtg(r.HomeTeam, r.Date, defense_ratings), get_rtg(r.AwayTeam, r.Date, defense_ratings)
        
        h_atk[i], a_atk[i] = rh_atk, ra_atk
        h_def[i], a_def[i] = rh_def, ra_def
        
        if not played:
            continue
            
        last_played = r.Date
        
        # คำนวณ K-Factor แยกทีมตามวิกฤตฟอร์ม
        k_home = get_k_factor(r.HomeTeam, r.Date, (rh_atk + rh_def)/2)
        k_away = get_k_factor(r.AwayTeam, r.Date, (ra_atk + ra_def)/2)
        
        # 🌟 จำลองการต่อสู้ 2 คู่: [บุกเหย้า vs รับเยือน] และ [รับเหย้า vs บุกเยือน]
        # 1. เหย้าบุก (Home Attack vs Away Defense)
        exp_h_atk = 1 / (1 + 10 ** (-(rh_atk + ELO_HOME_ADV - ra_def) / 400))
        score_h_atk = 1.0 if r.FTHG >= 1 else 0.0 # ยิงได้ = ชนะการดวล
        mult_h = 1.0 if r.FTHG <= 1 else (11 + r.FTHG) / 8
        delta_atk = k_home * mult_h * (score_h_atk - exp_h_atk)
        attack_ratings[r.HomeTeam] += delta_atk
        defense_ratings[r.AwayTeam] -= delta_atk
        
        # 2. เยือนบุก (Away Attack vs Home Defense)
        exp_a_atk = 1 / (1 + 10 ** (-(ra_atk - rh_def - ELO_HOME_ADV) / 400))
        score_a_atk = 1.0 if r.FTAG >= 1 else 0.0 # เยือนยิงได้ = ชนะการดวล
        mult_a = 1.0 if r.FTAG <= 1 else (11 + r.FTAG) / 8
        delta_def = k_away * mult_a * (score_a_atk - exp_a_atk)
        attack_ratings[r.AwayTeam] += delta_def
        defense_ratings[r.HomeTeam] -= delta_def
        
    d["Home_AttackElo"], d["Away_AttackElo"] = h_atk, a_atk
    d["Home_DefenseElo"], d["Away_DefenseElo"] = h_def, a_def
    
    # สร้าง EloDiff จากค่าเฉลี่ยเพื่อเก็บไว้ใช้ทำ Contextual Scaling
    d["HomeElo"] = (h_atk + h_def) / 2
    d["AwayElo"] = (a_atk + a_def) / 2
    return d

# ---------------------------------------------------------------- rolling / rest (🌟 อัปเกรด HomeGF / AwayGA)
def _team_long(d):
    home = d[["match_id", "Date", "HomeTeam", "FTHG", "FTAG"]].set_axis(["match_id", "Date", "Team", "GF", "GA"], axis=1)
    home["side"] = "Home"
    away = d[["match_id", "Date", "AwayTeam", "FTAG", "FTHG"]].set_axis(["match_id", "Date", "Team", "GF", "GA"], axis=1)
    away["side"] = "Away"
    long = pd.concat([home, away], ignore_index=True).sort_values(["Date", "match_id"], kind="stable")
    played = long["GF"].notna()
    long["PTS"] = np.where(~played, np.nan, np.where(long["GF"] > long["GA"], 3.0, np.where(long["GF"] == long["GA"], 1.0, 0.0)))
    return long

def _add_rolling(long):
    long = long.sort_values(["Team", "Date"], kind="stable").copy()
    g = long.groupby("Team", sort=False)
    prev = g["Date"].shift(1)
    long["RestDays"] = ((long["Date"] - prev).dt.total_seconds() / 86400).clip(upper=REST_CAP)

    def roll(col):
        return g[col].transform(lambda s: s.shift(1).rolling(ROLL_N, min_periods=ROLL_MIN).mean())

    long["GF5"], long["GA5"], long["PPM5"] = roll("GF"), roll("GA"), roll("PTS")
    
    # 🌟 ฟีเจอร์ใหม่: สิงห์สนามศุภฯ (แยกฟอร์มในบ้าน และ นอกบ้าน)
    home_games = long[long["side"] == "Home"].copy()
    home_games["HomeGF_Home"] = home_games.groupby("Team", sort=False)["GF"].transform(lambda s: s.shift(1).rolling(ROLL_N, min_periods=ROLL_MIN).mean())
    
    away_games = long[long["side"] == "Away"].copy()
    away_games["AwayGA_Away"] = away_games.groupby("Team", sort=False)["GA"].transform(lambda s: s.shift(1).rolling(ROLL_N, min_periods=ROLL_MIN).mean())
    
    long = long.merge(home_games[["match_id", "HomeGF_Home"]], on="match_id", how="left")
    long = long.merge(away_games[["match_id", "AwayGA_Away"]], on="match_id", how="left")
    
    return long

def _clean_form(d):
    played = d["FTHG"].notna()
    cnt = played.cumsum().shift(1)
    goals = (d["FTHG"].fillna(0) + d["FTAG"].fillna(0)).cumsum().shift(1)
    pts = pd.Series(np.where(played, np.where(d["FTHG"] == d["FTAG"], 2.0, 3.0), 0.0), index=d.index).cumsum().shift(1)
    lg_goals = (goals / (2 * cnt)).replace([np.inf, -np.inf], np.nan).fillna(LEAGUE_AVG_GOALS)
    lg_pts = (pts / (2 * cnt)).replace([np.inf, -np.inf], np.nan).fillna(LEAGUE_AVG_PTS)
    for side in ("Home", "Away"):
        d[f"{side}RestDays"] = d[f"{side}RestDays"].fillna(REST_CAP)
        d[f"{side}_GF5"] = d[f"{side}_GF5"].fillna(lg_goals)
        d[f"{side}_GA5"] = d[f"{side}_GA5"].fillna(lg_goals)
        d[f"{side}_PPM5"] = d[f"{side}_PPM5"].fillna(lg_pts)
        
    d["HomeGF_Home"] = d["HomeGF_Home"].fillna(lg_goals)
    d["AwayGA_Away"] = d["AwayGA_Away"].fillna(lg_goals)
    return d

def build_master(results, fbref=None, fixtures=None):
    d = results[["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG"]].copy()
    d["is_fixture"] = False
    if fixtures is not None and len(fixtures):
        fx = fixtures[["Date", "HomeTeam", "AwayTeam"]].copy()
        fx["FTHG"], fx["FTAG"], fx["is_fixture"] = np.nan, np.nan, True
        d = pd.concat([d, fx], ignore_index=True)
    d["Date"] = pd.to_datetime(d["Date"])

    # เพื่อให้ compute_elo รู้ฟอร์ม PPM5 ของแต่ละทีม ต้องทำ rolling ขั้นต้นก่อน
    d["match_id"] = np.arange(len(d))
    long_init = _add_rolling(_team_long(d))
    
    d = compute_elo(d, long_init)
    d["EloDiff"] = d["HomeElo"] - d["AwayElo"]

    long = _add_rolling(_team_long(d))
    keep = ["RestDays", "GF5", "GA5", "PPM5", "HomeGF_Home", "AwayGA_Away"]
    for side in ("Home", "Away"):
        part = long.loc[long["side"] == side, ["match_id"] + keep].set_index("match_id")
        # เปลี่ยนชื่อคอลัมน์ไม่ให้ซ้ำตอน merge
        part.columns = [f"{side}RestDays" if c == "RestDays" else (c if c in ["HomeGF_Home", "AwayGA_Away"] else f"{side}_{c}") for c in keep]
        # เอา HomeGF_Home เฉพาะฝั่งเจ้าบ้าน และ AwayGA_Away เฉพาะฝั่งเยือน
        if side == "Home":
            part = part.drop(columns=["AwayGA_Away"], errors="ignore")
        else:
            part = part.drop(columns=["HomeGF_Home"], errors="ignore")
            
        d = d.join(part, on="match_id")

    d = _clean_form(d)

    if fbref is not None and not fbref.empty:
        stats = [c for c in FB_STATS if c in fbref]
        prev = fbref[["Team", "Season"] + stats].copy()
        prev["Season"] = prev["Season"] + 1
        prev["_has"] = 1.0
        negative_stats = {"SoTA90", "CrdY90", "CrdR90", "Fls90", "OppPKatt"}
        lg_base = pd.DataFrame(index=prev["Season"].unique())
        for c in stats:
            if c in negative_stats:
                lg_base[c] = prev.groupby("Season")[c].quantile(0.75)
            else:
                lg_base[c] = prev.groupby("Season")[c].quantile(0.25)
        d["_season"] = season_of(d["Date"])
        for side in ("Home", "Away"):
            ren = {"Team": f"{side}Team", "Season": "_season", "_has": f"_has{side}",
                   **{c: f"{side}_Prev{c}" for c in stats}}
            d = d.merge(prev.rename(columns=ren), on=[f"{side}Team", "_season"], how="left")
            d[f"{side}NoPrev"] = d[f"_has{side}"].isna().astype(float)
            for c in stats:
                d[f"{side}_Prev{c}"] = d[f"{side}_Prev{c}"].fillna(d["_season"].map(lg_base[c]))
        d = d.drop(columns=["_season", "_hasHome", "_hasAway"])
        
        # 🌟 Contextual Scaling: ปรับลดการครองบอลตามช่องว่าง Elo
        # (ห่างกัน 100 Elo เปลี่ยนแปลง 2.5% โดยลิมิตเพดานไว้ที่ 25% - 75%)
        if "Home_PrevPoss" in d.columns and "Away_PrevPoss" in d.columns:
            elo_impact = (d["EloDiff"] / 100) * 2.5 
            d["Home_ContextPoss"] = (d["Home_PrevPoss"] + elo_impact).clip(lower=25.0, upper=75.0)
            d["Away_ContextPoss"] = (d["Away_PrevPoss"] - elo_impact).clip(lower=25.0, upper=75.0)

    cols = [c for c in FBREF_FEATURES if c in d]
    d.attrs["fbref_coverage"] = float(d[cols].notna().all(axis=1).mean()) if cols else 0.0
    return d

def feature_sets(master):
    fb = [c for c in FBREF_FEATURES if c in master and master[c].notna().mean() > 0.2]
    if not fb:
        return {"Elo + วันพัก + ฟอร์ม (ไม่มี FBref)": list(BASE_FEATURES)}
    flags = [c for c in FB_FLAGS if c in master]
    return {"Elo + วันพัก + ฟอร์ม + สถิติ FBref (อัปเกรดแล้ว)": BASE_FEATURES + fb + flags}

def build_league_master(league_name, fixtures=None, api_dir=API_DIR, fbref_dir=FBREF_DIR):
    code = LEAGUES[league_name]["csv_code"]
    results = load_results(code, api_dir)
    teams = set(results["HomeTeam"]) | set(results["AwayTeam"])
    fb, unmatched = load_fbref(code, teams, fbref_dir)
    warnings = []
    files, where_warn = find_fbref_files(code, fbref_dir)
    if where_warn:
        warnings.append(where_warn)
    if not files:
        warnings.append(f"ไม่พบไฟล์ FBref ({code}_season_*.csv) ใน {Path(fbref_dir)} จึงใช้เฉพาะ Elo/วันพัก/ฟอร์ม "
                        "(รัน python fetch_fbref_data.py)")
    if unmatched:
        warnings.append(f"จับคู่ชื่อ FBref กับผลแข่งไม่ได้: {', '.join(unmatched)} "
                        "(เพิ่มชื่อใน FBREF_ALIASES ของไฟล์ team_names.py)")
    if fb is not None:
        miss = fbref_missing_seasons(results, fb)
        if miss:
            warnings.append("ยังไม่มีไฟล์ FBref ของฤดูกาล " + ", ".join(map(str, miss)) +
                            f" ทำให้นัดในฤดูกาล {', '.join(str(m + 1) for m in miss)} ไม่มีค่าตั้งต้นจากปีก่อน "
                            "(รัน python fetch_fbref_data.py)")
    return build_master(results, fb, fixtures), warnings

def prepare_fixtures(fixtures, known_teams):
    fx, missing = fixtures.copy(), []
    for col in ("HomeTeam", "AwayTeam"):
        resolved = fx[col].map(lambda n: resolve_team(n, known_teams))
        missing += list(fx.loc[resolved.isna(), col])
        fx[col] = resolved.fillna(fx[col])
    return fx, sorted(set(missing))

def matchweek_start(kickoff_utc):
    t = pd.to_datetime(kickoff_utc) + pd.Timedelta(hours=7 - 6)
    return t.dt.normalize() - pd.to_timedelta(t.dt.dayofweek, unit="D")