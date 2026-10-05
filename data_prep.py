"""หน่วยเตรียมและประกอบร่างข้อมูล -> Master DataFrame (1 แถว = 1 นัด)

(Stable Version: ถอดลอจิกซ้ำซ้อน กลับสู่ความเรียบง่ายและเสถียรที่สุด)
- ใช้ Single Elo มาตรฐาน (เสถียรกว่าการแยก Attack/Defense)
- ใช้ K=20 คงที่ (ลบ Crisis Detector ที่สร้าง Noise และบั๊กออก)
- ใช้ PrevPoss ดิบ (ลบ ContextPoss ที่ซ้ำซ้อน)
- คงการแยกฟอร์ม 5 นัดในบ้าน (HomeGF_Home) และนอกบ้าน (AwayGA_Away)
- ตัด Feature ที่เป็น Noise ออก (GA5, ใบแดง) 
- ส่งออก Clean Data เป็น CSV แยกตามฤดูกาล
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
ELO_K = 20.0  

FB_FLAGS = []  
LEAGUE_AVG_GOALS, LEAGUE_AVG_PTS = 1.4, 1.37   

# 🌟 ฟีเจอร์ที่สะอาดและผ่านการทดสอบว่าเสถียรที่สุด (Single Elo)
BASE_FEATURES = [
    "HomeElo", "AwayElo", "EloDiff", "HomeRestDays", "AwayRestDays",
    "Home_PPM5", "Away_PPM5",
    "HomeGF_Home", "AwayGA_Away"
]

# 🌟 ใช้สถิติดิบ และตัด CrdR90 (ใบแดง) ออก
FBREF_FEATURES = [
    c for c in [f"{s}_Prev{k}" for s in ("Home", "Away") for k in FB_STATS]
    if "CrdR90" not in c
]

# ---------------------------------------------------------------- โหลดไฟล์ดิบ
def load_results(code, api_dir=API_DIR):
    files = sorted(glob.glob(str(Path(api_dir) / f"{code}_*.csv")))
    frames = [pd.read_csv(f, parse_dates=["Date"]) for f in files]
    frames = [f for f in frames if not f.empty]
    if not frames:
        raise FileNotFoundError(f"ไม่พบไฟล์ {code}_*.csv ใน {api_dir}")
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

# ---------------------------------------------------------------- Elo (Single Elo มาตรฐาน)
def compute_elo(df):
    d = df.sort_values("Date", kind="stable").reset_index(drop=True)
    ratings = {}
    last_played = None
    t0 = d["Date"].min()
    start_pool_until = t0 + pd.Timedelta(days=SEASON_GAP_DAYS)
    
    h_elo, a_elo = np.empty(len(d)), np.empty(len(d))

    def get_rtg(team, when):
        if team not in ratings:
            ratings[team] = ELO_START if when <= start_pool_until else ELO_NEWCOMER
        return ratings[team]

    for i, r in enumerate(d.itertuples(index=False)):
        played = pd.notna(r.FTHG) and pd.notna(r.FTAG)
        if played and last_played is not None and (r.Date - last_played).days > SEASON_GAP_DAYS:
            for t in ratings:                                
                ratings[t] = (1 - ELO_SEASON_REGRESS) * ratings[t] + ELO_SEASON_REGRESS * ELO_START
                
        rh, ra = get_rtg(r.HomeTeam, r.Date), get_rtg(r.AwayTeam, r.Date)
        h_elo[i], a_elo[i] = rh, ra
        
        if not played:
            continue
            
        last_played = r.Date
        
        exp_h = 1 / (1 + 10 ** (-(rh + ELO_HOME_ADV - ra) / 400))
        score_h = 1.0 if r.FTHG > r.FTAG else (0.5 if r.FTHG == r.FTAG else 0.0)
        
        margin = abs(r.FTHG - r.FTAG)
        mult = 1.0 if margin <= 1 else (11 + margin) / 8
        
        delta = ELO_K * mult * (score_h - exp_h)
        ratings[r.HomeTeam] += delta
        ratings[r.AwayTeam] -= delta
        
    d["HomeElo"], d["AwayElo"] = h_elo, a_elo
    d["EloDiff"] = d["HomeElo"] - d["AwayElo"]
    return d

# ---------------------------------------------------------------- rolling / rest 
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

    d["match_id"] = np.arange(len(d))
    
    d = compute_elo(d)

    long = _add_rolling(_team_long(d))
    keep = ["RestDays", "GF5", "GA5", "PPM5", "HomeGF_Home", "AwayGA_Away"]
    for side in ("Home", "Away"):
        part = long.loc[long["side"] == side, ["match_id"] + keep].set_index("match_id")
        part.columns = [f"{side}RestDays" if c == "RestDays" else (c if c in ["HomeGF_Home", "AwayGA_Away"] else f"{side}_{c}") for c in keep]
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

    cols = [c for c in FBREF_FEATURES if c in d]
    d.attrs["fbref_coverage"] = float(d[cols].notna().all(axis=1).mean()) if cols else 0.0
    return d

def feature_sets(master):
    fb = [c for c in FBREF_FEATURES if c in master and master[c].notna().mean() > 0.2]
    if not fb:
        return {"Elo + วันพัก + ฟอร์ม (ไม่มี FBref)": list(BASE_FEATURES)}
    return {"Elo + วันพัก + ฟอร์ม + สถิติ FBref": BASE_FEATURES + fb + FB_FLAGS}

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
        warnings.append(f"ไม่พบไฟล์ FBref ({code}_season_*.csv) ใน {Path(fbref_dir)}")
    if unmatched:
        warnings.append(f"จับคู่ชื่อ FBref กับผลแข่งไม่ได้: {', '.join(unmatched)}")
    if fb is not None:
        miss = fbref_missing_seasons(results, fb)
        if miss:
            warnings.append("ยังไม่มีไฟล์ FBref ของฤดูกาล " + ", ".join(map(str, miss)))
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

# ---------------------------------------------------------------- Export Clean Data 🌟
def export_clean_data(league_name):
    print(f"\nกำลังประมวลผลข้อมูลของลีก: {league_name}...")
    
    master_df, warnings = build_league_master(league_name)
    if warnings:
        for w in warnings:
            print(f"  ⚠️ {w}")
            
    clean_dir = DATA_DIR / "clean_data"
    clean_dir.mkdir(parents=True, exist_ok=True)
    
    master_df["Season_Year"] = season_of(master_df["Date"])
    
    for year, group in master_df.groupby("Season_Year"):
        code = LEAGUES[league_name]['csv_code']
        file_name = f"{code}_{year}_clean.csv"
        file_path = clean_dir / file_name
        
        save_df = group.drop(columns=["Season_Year"])
        save_df.to_csv(file_path, index=False, encoding='utf-8-sig')
        
        print(f"  ✅ บันทึก {file_name} สำเร็จ (จำนวน {len(save_df)} นัด)")

if __name__ == "__main__":
    print("--- 🚀 เริ่มกระบวนการสร้างและส่งออก Clean Data ---")
    for league in LEAGUES.keys():
        export_clean_data(league)
    print("\n--- ✨ เสร็จสิ้นกระบวนการทั้งหมด ข้อมูลอยู่ในโฟลเดอร์ Data/clean_data ---")