"""สมองกลของระบบ (ขั้นที่ 1: ML ประเมินประตูคาดหวัง λ, ขั้นที่ 2: Poisson แจกแจงสกอร์)

  (อัปเกรด 🌟: ปรับจูนพารามิเตอร์ Random Forest เพื่อรับมือกับ Advanced Features ป้องกัน Overfitting)
  Train   : Random Forest 2 ตัว (ประตูเหย้า / ประตูเยือน) เรียนจากฟีเจอร์ใน Master
  Predict : λ_เหย้า, λ_เยือน -> ตาราง Poisson 0..MAX_GOALS -> สกอร์ที่น่าจะเป็นที่สุด + P(ชนะ/เสมอ/แพ้)
  Tuning  : ลองชุด n_estimators / max_depth / min_samples_leaf ด้วย walk-forward log-loss
            (ช่วง "จูน" แยกจากช่วง "ตรวจ" เหมือนเดิม และใช้ค่าใหม่ก็ต่อเมื่อชนะค่าตั้งต้นในช่วงตรวจ)
ไฟล์นี้ไม่อ่าน/เขียน CSV ดิบ ยกเว้นไฟล์พารามิเตอร์ที่จูนแล้ว และไม่ import streamlit
"""
import json

import numpy as np
import pandas as pd
from scipy.stats import poisson
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline

from config import DATA_DIR, LEAGUES

MAX_GOALS = 10
LAMBDA_MIN, LAMBDA_MAX = 0.15, 4.5

# 🌟 อัปเดต DEFAULT_PARAMS: เพิ่มต้นไม้ ลดความลึก และเพิ่มใบ เพื่อบังคับให้โมเดลไม่ท่องจำข้อมูลมากเกินไป
DEFAULT_PARAMS = {"kind": "rf", "n_estimators": 300, "max_depth": 7, "min_samples_leaf": 15}

# 🌟 อัปเดต GRID: ขยายตารางค้นหาพารามิเตอร์ให้ครอบคลุมชุดข้อมูลที่มีฟีเจอร์ซับซ้อนขึ้น
GRID = {"n_estimators": [150, 300], "max_depth": [5, 7, 9], "min_samples_leaf": [10, 15, 25]}


# ---------------------------------------------------------------- train
def _regressor(p):
    """สร้างท่อส่งต่อข้อมูลให้โมเดล (เพิ่ม max_features='sqrt' เพื่อกระจายความสำคัญของตัวแปร)"""
    return make_pipeline(
        SimpleImputer(strategy="median"),   # ฟีเจอร์ที่ยังไม่มีประวัติ (ต้นฤดูกาล/ทีมใหม่) -> ค่ากลาง
        RandomForestRegressor(
            n_estimators=int(p["n_estimators"]), 
            max_depth=p["max_depth"],
            min_samples_split=20,                       # 🌟 บังคับกิ่งต้องมีอย่างน้อย 20 นัดถึงจะแตกต่อ
            min_samples_leaf=int(p["min_samples_leaf"]), 
            max_features="sqrt",                        # 🌟 สุ่มฟีเจอร์แค่รากที่สอง (กันตัวแปรเดิมๆ แย่งซีน)
            n_jobs=-1, 
            random_state=42,
        ),
    )


def train(master, features, params=None, before=None):
    """เทรนจากนัดที่แข่งจบแล้ว (ถ้าระบุ before จะใช้เฉพาะนัดก่อนวันนั้น) คืน dict โมเดล หรือ None"""
    p = {**DEFAULT_PARAMS, **(params or {})}
    d = master[master["FTHG"].notna()]
    if before is not None:
        d = d[d["Date"] < pd.Timestamp(before)]
    if len(d) < 30:
        return None
    X = d[list(features)]
    return {
        "kind": "rf",
        "features": list(features),
        "params": p,
        "home": _regressor(p).fit(X, d["FTHG"]),
        "away": _regressor(p).fit(X, d["FTAG"]),
        "teams": sorted(set(d["HomeTeam"]) | set(d["AwayTeam"])),
        "n_train": len(d),
    }


def expected_goals(model, rows):
    """λ เหย้า/เยือน (numpy array) ของทุกแถวใน rows"""
    X = rows[model["features"]]
    return (np.clip(model["home"].predict(X), LAMBDA_MIN, LAMBDA_MAX),
            np.clip(model["away"].predict(X), LAMBDA_MIN, LAMBDA_MAX))


def feature_importance(model):
    """ความสำคัญของฟีเจอร์ (เฉลี่ยโมเดลเหย้า+เยือน) เรียงมาก->น้อย"""
    # Pipeline มี 2 step (Imputer=0, RF=1)
    imp = sum(model[k][-1].feature_importances_ for k in ("home", "away")) / 2
    return pd.Series(imp, index=model["features"]).sort_values(ascending=False)


# ---------------------------------------------------------------- Poisson
def score_matrix(lam_h, lam_a, max_goals=MAX_GOALS):
    """ตารางความน่าจะเป็นสกอร์ [เหย้า, เยือน] (normalize ให้รวม 1)"""
    k = np.arange(max_goals + 1)
    m = np.outer(poisson.pmf(k, lam_h), poisson.pmf(k, lam_a))
    return m / m.sum()


def describe_matrix(m, lam_h, lam_a):
    i, j = np.unravel_index(np.argmax(m), m.shape)
    return {
        "score": f"{i} - {j}",
        "p_home": float(np.tril(m, -1).sum() * 100),   # เหย้ายิงมากกว่า
        "p_draw": float(np.trace(m) * 100),
        "p_away": float(np.triu(m, 1).sum() * 100),
        "xg_home": float(lam_h),
        "xg_away": float(lam_a),
    }


def predict_rows(model, rows):
    """ทำนายหลายนัดพร้อมกัน คืน list ของ dict (key เดิมของแอป: score, p_home, p_draw, p_away, xg_home, xg_away, missing)"""
    if not model or len(rows) == 0:
        return []
    lh, la = expected_goals(model, rows)
    known = set(model["teams"])
    out = []
    for (_, r), h, a in zip(rows.iterrows(), lh, la):
        res = describe_matrix(score_matrix(h, a), h, a)
        res["missing"] = [t for t in (r["HomeTeam"], r["AwayTeam"]) if t not in known]
        out.append(res)
    return out


def predict_match(model, row):
    """ทำนายนัดเดียว (row = 1 แถวจาก Master ที่มีฟีเจอร์ครบ)"""
    res = predict_rows(model, row.to_frame().T if isinstance(row, pd.Series) else row)
    return res[0] if res else None


# ---------------------------------------------------------------- พารามิเตอร์ที่จูนแล้ว
def _params_path(league_name):
    return DATA_DIR / f"tuned_ml_{LEAGUES[league_name]['csv_code']}.json"


def load_params(league_name):
    try:
        d = json.loads(_params_path(league_name).read_text(encoding="utf-8"))
        if d.get("kind") == "rf":
            return {"kind": "rf", "n_estimators": int(d["n_estimators"]),
                    "max_depth": d["max_depth"], "min_samples_leaf": int(d["min_samples_leaf"])}
    except Exception:  # noqa: BLE001
        pass
    return dict(DEFAULT_PARAMS)


def save_params(league_name, params):
    DATA_DIR.mkdir(exist_ok=True)
    keep = {k: params[k] for k in ("n_estimators", "max_depth", "min_samples_leaf")}
    _params_path(league_name).write_text(json.dumps({"kind": "rf", **keep}), encoding="utf-8")


def reset_params(league_name):
    try:
        _params_path(league_name).unlink()
    except FileNotFoundError:
        pass


def is_default(params):
    return all(params.get(k) == DEFAULT_PARAMS[k] for k in ("n_estimators", "max_depth", "min_samples_leaf"))


# ---------------------------------------------------------------- tuning
def run_tuning(master, features, n_tune=380, n_holdout=380, step_weeks=3, n_trials=20):
    """จูนพารามิเตอร์ของ Random Forest ด้วย Bayesian Optimization (Optuna)
    คืน dict: grid, best, holdout, improved, n_tune, n_holdout หรือ None ถ้าข้อมูลไม่พอ
    step_weeks: ตอนจูนเทรนใหม่ทุกกี่สัปดาห์ (ยิ่งมากยิ่งเร็ว)
    n_trials: จำนวนครั้งในการสุ่มจูนของ Optuna
    """
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    from evaluation import MIN_TRAIN_MATCHES, compare_models, summarize, walk_forward  # กัน import วน

    played = int(master["FTHG"].notna().sum())
    avail = played - MIN_TRAIN_MATCHES
    if avail < 200:
        return None
    n_holdout = min(n_holdout, avail // 2)
    n_tune = min(n_tune, avail - n_holdout)

    rows = []
    
    def objective(trial):
        ne = trial.suggest_int("n_estimators", 100, 500, step=50)
        md = trial.suggest_int("max_depth", 3, 10)
        leaf = trial.suggest_int("min_samples_leaf", 5, 30)
        
        p = {"kind": "rf", "n_estimators": ne, "max_depth": md, "min_samples_leaf": leaf}
        s = summarize(walk_forward(master, features, p, n_tune, skip_last=n_holdout,
                                   step_weeks=step_weeks)["results"])
        if s is None:
            raise optuna.TrialPruned()
            
        rows.append({"n_estimators": ne, "max_depth": md, "min_samples_leaf": leaf, 
                     "logloss": s["logloss"], "accuracy": s["accuracy"]})
                     
        return s["logloss"]

    study = optuna.create_study(direction="minimize")
    study.optimize(objective, n_trials=n_trials)
    
    if not rows:
        return None

    # แปลงประวัติการจูนเป็นตารางและเรียงตาม logloss น้อยสุด
    grid = pd.DataFrame(rows).sort_values("logloss").drop_duplicates(subset=["n_estimators", "max_depth", "min_samples_leaf"]).reset_index(drop=True)
    
    best_params = study.best_params
    best = {"kind": "rf", "n_estimators": int(best_params["n_estimators"]),
            "max_depth": int(best_params["max_depth"]), "min_samples_leaf": int(best_params["min_samples_leaf"])}

    holdout = compare_models(master, n_holdout, {
        "RF (จูนด้วย Optuna)": (features, best),
        "RF (ค่าตั้งต้น)": (features, dict(DEFAULT_PARAMS)),
    }, step_weeks=step_weeks)
    
    ll = dict(zip(holdout["โมเดล"], holdout["Log-loss"]))
    return {"grid": grid, "best": best, "holdout": holdout,
            "improved": bool(ll["RF (จูนด้วย Optuna)"] < ll["RF (ค่าตั้งต้น)"]),
            "n_tune": n_tune, "n_holdout": n_holdout}