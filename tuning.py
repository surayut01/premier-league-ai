"""จูนพารามิเตอร์ของ Dixon-Coles ด้วย walk-forward log-loss

เพื่อไม่ให้ตัวเลข "ดีเกินจริง" จากการเลือกค่าที่เข้ากับข้อมูลทดสอบพอดี ใช้ 2 ช่วงแยกกัน:
  - ช่วงจูน   : ข้อมูลเก่ากว่า -> ลองทุกค่าใน GRID แล้วเลือกค่าที่ log-loss ต่ำสุด
  - ช่วงตรวจ  : ข้อมูลล่าสุดที่ไม่เคยใช้เลือกค่า -> เทียบค่าที่จูนได้ vs ค่าตั้งต้น vs โมเดลเดิม
จะนำค่าใหม่ไปใช้ก็ต่อเมื่อดีกว่าค่าตั้งต้นในช่วงตรวจเท่านั้น
"""
import json

import pandas as pd
import streamlit as st

from data_fetcher import DATA_DIR, LEAGUES
from evaluation import MIN_TRAIN_MATCHES, compare_models, run_walk_forward, summarize
from predictor import DEFAULT_PARAMS, SIMPLE_PARAMS

GRID_HALF_LIFE = [180, 270, 365, 540, 730]   # วัน
GRID_REG = [1.0, 3.0, 8.0, 20.0]             # ความแรงของการดึงเข้าหาค่าเฉลี่ย


def _params_path(league_name):
    return DATA_DIR / f"tuned_{LEAGUES[league_name]['csv_code']}.json"


def load_params(league_name):
    """พารามิเตอร์ที่จูนไว้ของลีกนี้ ถ้าไม่มีหรือไฟล์ผิดรูปแบบใช้ค่าตั้งต้น"""
    try:
        data = json.loads(_params_path(league_name).read_text(encoding="utf-8"))
        hl, reg = float(data["half_life_days"]), float(data["reg"])
        if data.get("kind") == "dc" and 30 <= hl <= 2000 and 0 < reg <= 200:
            return {"kind": "dc", "half_life_days": hl, "reg": reg}
    except Exception:  # noqa: BLE001
        pass
    return dict(DEFAULT_PARAMS)


def save_params(league_name, params):
    DATA_DIR.mkdir(exist_ok=True)
    _params_path(league_name).write_text(
        json.dumps({"kind": "dc", "half_life_days": params["half_life_days"], "reg": params["reg"]}),
        encoding="utf-8",
    )


def reset_params(league_name):
    try:
        _params_path(league_name).unlink()
    except FileNotFoundError:
        pass


def is_default(params):
    return (params.get("half_life_days") == DEFAULT_PARAMS["half_life_days"]
            and params.get("reg") == DEFAULT_PARAMS["reg"])


@st.cache_data(ttl=86400, show_spinner=False)
def run_tuning(df, n_tune=380, n_holdout=380):
    """คืน dict: grid, best, holdout (ตารางเทียบโมเดล), improved, n_tune, n_holdout
    หรือ None ถ้าข้อมูลไม่พอ"""
    avail = len(df) - MIN_TRAIN_MATCHES
    if avail < 200:
        return None
    n_holdout = min(n_holdout, avail // 2)
    n_tune = min(n_tune, avail - n_holdout)

    rows = []
    for hl in GRID_HALF_LIFE:
        for reg in GRID_REG:
            params = {"kind": "dc", "half_life_days": float(hl), "reg": float(reg)}
            s = summarize(run_walk_forward(df, n_tune, params, skip_last=n_holdout)["results"])
            if s is None:
                continue
            rows.append({"half_life_days": hl, "reg": reg, "logloss": s["logloss"], "accuracy": s["accuracy"]})
    if not rows:
        return None

    grid = pd.DataFrame(rows).sort_values("logloss").reset_index(drop=True)
    top = grid.iloc[0]
    best = {"kind": "dc", "half_life_days": float(top["half_life_days"]), "reg": float(top["reg"])}

    holdout = compare_models(
        df, n_holdout,
        {
            "Dixon-Coles (ค่าที่จูนได้)": best,
            "Dixon-Coles (ค่าตั้งต้น)": dict(DEFAULT_PARAMS),
            "Poisson แบบเดิม": dict(SIMPLE_PARAMS),
        },
    )
    ll = dict(zip(holdout["โมเดล"], holdout["Log-loss"]))
    improved = ll["Dixon-Coles (ค่าที่จูนได้)"] < ll["Dixon-Coles (ค่าตั้งต้น)"]

    return {
        "grid": grid,
        "best": best,
        "holdout": holdout,
        "improved": bool(improved),
        "n_tune": n_tune,
        "n_holdout": n_holdout,
    }
