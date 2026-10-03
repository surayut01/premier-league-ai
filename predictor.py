import numpy as np
import pandas as pd
import streamlit as st
from scipy.stats import poisson

from team_names import resolve_team

MAX_GOALS = 10      # คิดสกอร์สูงสุดทีมละ 10 ประตู (เดิม 5 ทำให้ความน่าจะเป็นรวมไม่ครบ 100%)
SHRINK = 4.0        # "จำนวนนัดสมมติ" ที่ดึงค่าทีมเข้าหาค่าเฉลี่ยลีก ลดความเพี้ยนจากข้อมูลน้อย
HALF_LIFE_DAYS = 365  # นัดเก่าครบ 1 ปีมีน้ำหนักเหลือครึ่งเดียว


def _team_rate(d, team_col, goal_col, league_avg):
    """อัตราประตู (ถ่วงน้ำหนักเวลา + shrink) หารด้วยค่าเฉลี่ยลีก"""
    g = (
        d.assign(wg=d["w"] * d[goal_col])
        .groupby(team_col)
        .agg(wg=("wg", "sum"), w=("w", "sum"))
    )
    rate = (g["wg"] + SHRINK * league_avg) / (g["w"] + SHRINK) / league_avg
    return rate.to_dict()


@st.cache_data(ttl=86400, show_spinner=False)
def train_model(df, ref_date=None, half_life_days=HALF_LIFE_DAYS):
    """คำนวณพลังรุก/รับของแต่ละทีม

    ref_date: วันอ้างอิงสำหรับถ่วงน้ำหนัก (ค่าเริ่มต้น = วันที่ล่าสุดในข้อมูล)
    ส่ง df ที่ตัดนัดอนาคตออกแล้วเพื่อ Backtest โดยไม่ให้ข้อมูลรั่ว
    """
    if df is None or df.empty:
        return None

    d = df.copy()
    ref = pd.Timestamp(ref_date) if ref_date is not None else d["Date"].max()
    age_days = (ref - d["Date"]).dt.days.clip(lower=0)
    d["w"] = 0.5 ** (age_days / half_life_days)

    avg_home = float(np.average(d["FTHG"], weights=d["w"]))
    avg_away = float(np.average(d["FTAG"], weights=d["w"]))

    return {
        "avg_home": avg_home,
        "avg_away": avg_away,
        "home_attack": _team_rate(d, "HomeTeam", "FTHG", avg_home),
        "home_defence": _team_rate(d, "HomeTeam", "FTAG", avg_away),
        "away_attack": _team_rate(d, "AwayTeam", "FTAG", avg_away),
        "away_defence": _team_rate(d, "AwayTeam", "FTHG", avg_home),
        "teams": sorted(set(d["HomeTeam"]) | set(d["AwayTeam"])),
    }


def predict_match(model, home_team, away_team):
    """ทำนายผลคู่หนึ่ง คืน dict

    keys: score, p_home, p_draw, p_away (เป็น %), xg_home, xg_away,
          missing (ชื่อทีมที่จับคู่กับข้อมูลสถิติไม่ได้ -> ใช้ค่าเฉลี่ยลีกแทน)
    """
    if not model:
        return None

    h = resolve_team(home_team, model["teams"])
    a = resolve_team(away_team, model["teams"])
    missing = [name for name, found in ((home_team, h), (away_team, a)) if found is None]

    ha = model["home_attack"].get(h, 1.0)
    hd = model["home_defence"].get(h, 1.0)
    aa = model["away_attack"].get(a, 1.0)
    ad = model["away_defence"].get(a, 1.0)

    lambda_home = max(0.2, ha * ad * model["avg_home"])
    lambda_away = max(0.2, aa * hd * model["avg_away"])

    goals = np.arange(MAX_GOALS + 1)
    matrix = np.outer(poisson.pmf(goals, lambda_home), poisson.pmf(goals, lambda_away))
    matrix /= matrix.sum()

    home_win = np.tril(matrix, -1).sum()   # แถว = ประตูเหย้า > คอลัมน์ = ประตูเยือน
    draw = np.trace(matrix)
    away_win = np.triu(matrix, 1).sum()

    hg, ag = np.unravel_index(np.argmax(matrix), matrix.shape)

    return {
        "score": f"{hg} - {ag}",
        "p_home": float(home_win * 100),
        "p_draw": float(draw * 100),
        "p_away": float(away_win * 100),
        "xg_home": float(lambda_home),
        "xg_away": float(lambda_away),
        "missing": missing,
    }
