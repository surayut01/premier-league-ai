"""จูนพารามิเตอร์ Random Forest ด้วย walk-forward log-loss แบบ Bayesian Optimization (Optuna)

เพื่อไม่ให้ตัวเลข "ดีเกินจริง" จากการเลือกค่าที่เข้ากับข้อมูลทดสอบพอดี ใช้ 2 ช่วงแยกกัน:
  - ช่วงจูน   : ข้อมูลเก่ากว่า -> ให้ Optuna ลองหาชุดค่าที่ทำให้ log-loss ต่ำสุด
  - ช่วงตรวจ  : ข้อมูลล่าสุดที่ไม่เคยใช้เลือกค่า -> เทียบค่าที่จูนได้ vs ค่าตั้งต้น
จะนำค่าใหม่ไปใช้ก็ต่อเมื่อดีกว่าค่าตั้งต้นในช่วงตรวจเท่านั้น

ไฟล์นี้ไม่ import streamlit และไม่ถูก predictor.py / evaluation.py เรียกกลับ (ไม่มี import วน)
การโหลด/บันทึก/รีเซ็ตค่าที่จูนแล้วใช้ฟังก์ชันของ predictor.py (ไฟล์ data/tuned_ml_<รหัสลีก>.json)
"""
import optuna
import pandas as pd

from evaluation import MIN_TRAIN_MATCHES, compare_models, summarize, walk_forward
from predictor import DEFAULT_PARAMS, is_default, load_params, reset_params, save_params  # noqa: F401

# ปิด log ของ Optuna ไม่ให้รก console
optuna.logging.set_verbosity(optuna.logging.WARNING)

TUNED_NAME = "RF (จูนด้วย Optuna)"
DEFAULT_NAME = "RF (ค่าตั้งต้น)"


def run_tuning(master, features, n_tune=380, n_holdout=380, step_weeks=3, n_trials=20, seed=42):
    """คืน dict: grid, best, holdout (ตารางเทียบโมเดล), improved, n_tune, n_holdout
    หรือ None ถ้าข้อมูลไม่พอ

    master     : Master DataFrame จาก data_prep (ต้องมีคอลัมน์ FTHG/FTAG/Date)
    features   : รายชื่อฟีเจอร์ที่ใช้เทรน
    step_weeks : ตอนจูนเทรนใหม่ทุกกี่สัปดาห์ (ยิ่งมากยิ่งเร็ว)
    n_trials   : จำนวนครั้งที่ Optuna ลอง
    seed       : ตรึงการสุ่มของ Optuna ให้รันซ้ำแล้วได้ผลเดิม
    """
    played = int(master["FTHG"].notna().sum())
    avail = played - MIN_TRAIN_MATCHES
    if avail < 200:
        return None
    n_holdout = min(n_holdout, avail // 2)
    n_tune = min(n_tune, avail - n_holdout)

    rows = []

    # ฟังก์ชันเป้าหมายของ Optuna (ต้องการ log-loss ต่ำที่สุดในช่วงจูน)
    def objective(trial):
        params = {
            "kind": "rf",
            "n_estimators": trial.suggest_int("n_estimators", 100, 500, step=50),
            "max_depth": trial.suggest_int("max_depth", 3, 10),
            "min_samples_leaf": trial.suggest_int("min_samples_leaf", 5, 30),
        }
        res = walk_forward(master, features, params, n_tune, skip_last=n_holdout, step_weeks=step_weeks)
        s = summarize(res["results"])
        if s is None:
            raise optuna.TrialPruned()

        rows.append({
            "n_estimators": params["n_estimators"],
            "max_depth": params["max_depth"],
            "min_samples_leaf": params["min_samples_leaf"],
            "logloss": s["logloss"],
            "accuracy": s["accuracy"],
        })
        return s["logloss"]

    study = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=seed))
    study.optimize(objective, n_trials=n_trials)

    if not rows:
        return None

    # แปลงประวัติการจูนเป็นตาราง เรียงตาม logloss น้อยสุด
    grid = (pd.DataFrame(rows)
            .sort_values("logloss")
            .drop_duplicates(subset=["n_estimators", "max_depth", "min_samples_leaf"])
            .reset_index(drop=True))

    bp = study.best_params
    best = {"kind": "rf", "n_estimators": int(bp["n_estimators"]),
            "max_depth": int(bp["max_depth"]), "min_samples_leaf": int(bp["min_samples_leaf"])}

    # ช่วงตรวจ: นัดล่าสุดที่ไม่เคยใช้เลือกค่า เทียบค่าที่จูนได้ vs ค่าตั้งต้น
    holdout = compare_models(master, n_holdout, {
        TUNED_NAME: (features, best),
        DEFAULT_NAME: (features, dict(DEFAULT_PARAMS)),
    }, step_weeks=step_weeks)

    ll = dict(zip(holdout["โมเดล"], holdout["Log-loss"]))
    return {
        "grid": grid,
        "best": best,
        "holdout": holdout,
        "improved": bool(ll[TUNED_NAME] < ll[DEFAULT_NAME]),
        "n_tune": n_tune,
        "n_holdout": n_holdout,
    }