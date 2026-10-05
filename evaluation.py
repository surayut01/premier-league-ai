"""วัดความแม่นยำแบบ walk-forward (แยกอิสระจากโค้ดเทรน)

ย้อนไปทำนายนัดในอดีตทีละสัปดาห์ โดยเทรนด้วยนัดที่แข่ง "ก่อนวันเตะของสัปดาห์นั้นเท่านั้น"
(ฟีเจอร์ใน Master ถูกคำนวณจากอดีตล้วน ๆ อยู่แล้ว จึงไม่รั่ว) แล้วเทียบกับ baseline:
  1) เดาเจ้าบ้านชนะทุกนัด (accuracy)  2) ใช้สัดส่วน H/D/A เฉลี่ยของลีก (log-loss, Brier)
และเปรียบเทียบ "ชุดฟีเจอร์" ต่าง ๆ บนนัดชุดเดียวกัน เช่น ก่อน/หลังเพิ่ม FBref
"""
import numpy as np
import pandas as pd

import predictor as ml

MIN_TRAIN_MATCHES = 150
_EPS = 1e-12


def outcome_index(home_goals, away_goals):
    """0 = เจ้าบ้านชนะ, 1 = เสมอ, 2 = ทีมเยือนชนะ"""
    return 0 if home_goals > away_goals else (2 if home_goals < away_goals else 1)


def walk_forward(master, features, params=None, n_eval=380, skip_last=0, step_weeks=1):
    """คืน dict: results (DataFrame รายนัด), skipped (จำนวนนัดที่ข้าม)
    skip_last: ข้ามนัดล่าสุดกี่นัด (แยกช่วงจูนออกจากช่วงตรวจ) • step_weeks: เทรนใหม่ทุกกี่สัปดาห์"""
    params = params or ml.DEFAULT_PARAMS
    d = master[master["FTHG"].notna()].sort_values("Date", kind="stable").reset_index(drop=True)
    n_eval = min(int(n_eval), len(d) - MIN_TRAIN_MATCHES - int(skip_last))
    if n_eval <= 0:
        return {"results": pd.DataFrame(), "skipped": 0}

    end = len(d) - int(skip_last)
    test = d.iloc[end - n_eval:end]
    start = test["Date"].min().normalize()
    block_no = ((test["Date"] - start).dt.days // 7) // max(1, int(step_weeks))

    rows, skipped = [], 0
    for _, block in test.groupby(block_no):
        cutoff = block["Date"].min().normalize()
        train = d[d["Date"] < cutoff]
        if len(train) < MIN_TRAIN_MATCHES:
            skipped += len(block)
            continue
        model = ml.train(train, features, params)

        t_out = np.where(train["FTHG"] > train["FTAG"], 0, np.where(train["FTHG"] < train["FTAG"], 2, 1))
        base = np.bincount(t_out, minlength=3) / len(t_out)

        preds = ml.predict_rows(model, block)
        for (_, r), p in zip(block.iterrows(), preds):
            if p["missing"]:        # ทีมที่ยังไม่เคยมีสถิติ (เช่นทีมเลื่อนชั้น) ข้ามเพื่อความยุติธรรม
                skipped += 1
                continue
            ph, pa = map(int, p["score"].split(" - "))
            real_idx = outcome_index(r["FTHG"], r["FTAG"])
            p_real = (p["p_home"], p["p_draw"], p["p_away"])[real_idx] / 100
            rows.append({
                "Date": r["Date"], "HomeTeam": r["HomeTeam"], "AwayTeam": r["AwayTeam"],
                "real_score": f"{int(r['FTHG'])} - {int(r['FTAG'])}", "pred_score": p["score"],
                "real_idx": real_idx, "score_idx": outcome_index(ph, pa),
                "p_home": p["p_home"] / 100, "p_draw": p["p_draw"] / 100, "p_away": p["p_away"] / 100,
                "b_home": base[0], "b_draw": base[1], "b_away": base[2],
                "ll": float(-np.log(np.clip(p_real, _EPS, 1))),   # log-loss รายนัด ใช้เทียบโมเดลแบบจับคู่
            })
    return {"results": pd.DataFrame(rows), "skipped": skipped}


def summarize(res):
    """สรุปตัวชี้วัด คืน None ถ้าไม่มีข้อมูล"""
    if res is None or res.empty:
        return None
    n = len(res)
    y = res["real_idx"].to_numpy()
    idx = np.arange(n)
    P = res[["p_home", "p_draw", "p_away"]].to_numpy()
    B = res[["b_home", "b_draw", "b_away"]].to_numpy()
    onehot = np.eye(3)[y]
    acc = float((P.argmax(axis=1) == y).mean())

    # ความเอนเอียงของโอกาส "เสมอ": โมเดล Poisson อิสระมักทายเสมอต่ำไป
    # draw_gap = p_draw เฉลี่ย − สัดส่วนเสมอจริง (ติดลบ = ทายต่ำไป) • draw_z = draw_gap / SE (|z| > 1.96 = ต่างอย่างมีนัยสำคัญ)
    is_draw = (y == 1).astype(float)
    d_err = P[:, 1] - is_draw
    d_se = float(d_err.std(ddof=1) / np.sqrt(n)) if n > 1 else 0.0
    d_gap = float(d_err.mean())
    return {
        "draw_pred": float(P[:, 1].mean()),
        "draw_real": float(is_draw.mean()),
        "draw_gap": d_gap,
        "draw_z": d_gap / d_se if d_se > 0 else 0.0,
        "n": n,
        "accuracy": acc,
        "accuracy_ci": float(1.96 * np.sqrt(acc * (1 - acc) / n)),
        "accuracy_from_score": float((res["score_idx"].to_numpy() == y).mean()),
        "exact_score": float((res["pred_score"] == res["real_score"]).mean()),
        "baseline_home_acc": float((y == 0).mean()),
        "logloss": float(-np.mean(np.log(np.clip(P[idx, y], _EPS, 1)))),
        "baseline_logloss": float(-np.mean(np.log(np.clip(B[idx, y], _EPS, 1)))),
        "brier": float(np.mean(np.sum((P - onehot) ** 2, axis=1))),
        "baseline_brier": float(np.mean(np.sum((B - onehot) ** 2, axis=1))),
        "date_from": res["Date"].min(),
        "date_to": res["Date"].max(),
    }


COL_DELTA = "Δ Log-loss (เทียบโมเดลแรก)"
COL_SE = "± SE"
COL_VERDICT = "สรุป"


def _paired_diff(res, ref):
    """ส่วนต่าง log-loss แบบจับคู่รายนัด (res − ref) พร้อมค่าคลาดเคลื่อนมาตรฐาน (SE)
    ติดลบ = res ดีกว่า ref • ถ้า |ส่วนต่าง| ไม่เกิน 1.96×SE ถือว่าแยกจากโชคไม่ได้
    จับคู่ด้วย (วันที่, ทีมเหย้า, ทีมเยือน) จึงเทียบได้แม้บางนัดถูกข้ามไม่เท่ากัน"""
    keys = ["Date", "HomeTeam", "AwayTeam"]
    m = res[keys + ["ll"]].merge(ref[keys + ["ll"]], on=keys, suffixes=("", "_ref"))
    if len(m) < 2:
        return {}
    d = (m["ll"] - m["ll_ref"]).to_numpy()
    mean = float(d.mean())
    se = float(d.std(ddof=1) / np.sqrt(len(d)))
    return {COL_DELTA: round(mean, 4), COL_SE: round(se, 4),
            COL_VERDICT: "ต่างอย่างมีนัยสำคัญ" if abs(mean) > 1.96 * se else "แยกจากโชคไม่ได้"}


def compare_models(master, n_eval, configs, skip_last=0, step_weeks=1):
    """เทียบหลายโมเดล/ชุดฟีเจอร์บนนัดชุดเดียวกัน
    configs = {ชื่อ: (รายการฟีเจอร์, params)}  คืน DataFrame (บรรทัดแรกสุดคือ baseline สัดส่วนเฉลี่ยของลีก)
    คอลัมน์ Δ / ± SE / สรุป: เทียบแต่ละโมเดลกับโมเดลแรกใน configs แบบจับคู่รายนัด (โมเดลแรกเองเว้นว่างไว้)"""
    rows, base_row, ref = [], None, None
    for name, (features, params) in configs.items():
        res = walk_forward(master, features, params, n_eval, skip_last, step_weeks)["results"]
        s = summarize(res)
        if s is None:
            continue
        if base_row is None:
            base_row = {"โมเดล": "baseline: สัดส่วนเฉลี่ยของลีก", "จำนวนนัด": s["n"], "Accuracy %": np.nan,
                        "Log-loss": round(s["baseline_logloss"], 4), "Brier": round(s["baseline_brier"], 4)}
        row = {"โมเดล": name, "จำนวนนัด": s["n"], "Accuracy %": round(s["accuracy"] * 100, 1),
               "Log-loss": round(s["logloss"], 4), "Brier": round(s["brier"], 4)}
        if ref is None:
            ref = res
        else:
            row.update(_paired_diff(res, ref))
        rows.append(row)
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame([base_row] + rows)


def calibration_table(res):
    """ความน่าจะเป็นที่โมเดลให้ vs ความถี่ที่เกิดขึ้นจริง (รวมทั้ง 3 ผลลัพธ์)"""
    if res is None or res.empty:
        return pd.DataFrame()
    P = res[["p_home", "p_draw", "p_away"]].to_numpy().ravel()
    hits = np.eye(3)[res["real_idx"].to_numpy()].ravel()
    edges = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 1.0001]
    labels = ["0–10%", "10–20%", "20–30%", "30–40%", "40–50%", "50–60%", "60–70%", "70%+"]
    t = pd.DataFrame({"p": P, "hit": hits})
    t["bin"] = pd.cut(t["p"], bins=edges, labels=labels, right=False)
    g = t.groupby("bin", observed=True).agg(n=("p", "size"), pred=("p", "mean"), real=("hit", "mean"))
    return pd.DataFrame({
        "ช่วงที่โมเดลให้": g.index.astype(str),
        "จำนวนครั้ง": g["n"].to_numpy(),
        "โมเดลบอกเฉลี่ย (%)": (g["pred"] * 100).round(1).to_numpy(),
        "เกิดขึ้นจริง (%)": (g["real"] * 100).round(1).to_numpy(),
    })


def results_for_display(res):
    """ตารางรายนัดภาษาไทยสำหรับแสดง/ดาวน์โหลด"""
    out = pd.DataFrame({
        "วันที่": res["Date"].dt.strftime("%d/%m/%Y"),
        "ทีมเหย้า": res["HomeTeam"], "ทีมเยือน": res["AwayTeam"],
        "ผลจริง": res["real_score"], "AI ทายสกอร์": res["pred_score"],
        "เหย้าชนะ %": (res["p_home"] * 100).round(1),
        "เสมอ %": (res["p_draw"] * 100).round(1),
        "เยือนชนะ %": (res["p_away"] * 100).round(1),
    })
    labels = np.array(["เหย้าชนะ", "เสมอ", "เยือนชนะ"])
    P = res[["p_home", "p_draw", "p_away"]].to_numpy()
    out["ผลที่ AI เชื่อ"] = labels[P.argmax(axis=1)]
    out["ผลจริง (H/D/A)"] = labels[res["real_idx"].to_numpy()]
    out["ถูก/ผิด"] = np.where(P.argmax(axis=1) == res["real_idx"].to_numpy(), "✅", "❌")
    return out

# ---------------------------------------------------------------- permutation importance
def feature_groups(features):
    """จัดฟีเจอร์เป็นกลุ่มที่สลับค่าพร้อมกัน: Home_X + Away_X เป็นสถิติเดียวกัน, Elo ทั้ง 3 ตัวอยู่กลุ่มเดียว"""
    groups = {}
    for f in features:
        if f in ("HomeElo", "AwayElo", "EloDiff"):
            key = "Elo"
        elif f in ("HomeNoPrev", "AwayNoPrev"):
            key = "NoPrev"
        elif f in ("HomeRestDays", "AwayRestDays"):
            key = "RestDays"
        else:
            key = f.split("_", 1)[1] if "_" in f else f
        groups.setdefault(key, []).append(f)
    return groups


def _logloss_of(model, rows):
    lh, la = ml.expected_goals(model, rows)
    y = rows.apply(lambda r: outcome_index(r["FTHG"], r["FTAG"]), axis=1).to_numpy()
    p = np.empty(len(rows))
    for i, (h, a) in enumerate(zip(lh, la)):
        m = ml.score_matrix(h, a)
        p[i] = (np.tril(m, -1).sum(), np.trace(m), np.triu(m, 1).sum())[y[i]]
    return float(-np.mean(np.log(np.clip(p, _EPS, 1))))


def permutation_importance(master, features, params=None, n_val=380, skip_last=380, repeats=8, seed=0):
    """ความสำคัญแบบสลับค่า (permutation) วัดด้วย log-loss ของ "ผลแพ้/เสมอ/ชนะ"

    เทรนด้วยนัดเก่า แล้วสลับค่าของแต่ละกลุ่มฟีเจอร์ในช่วงตรวจ n_val นัด (เว้น skip_last นัดล่าสุดไว้เป็นช่วงทดสอบจริง
    ที่ไม่ใช้ตัดสินใจ) ค่า > 0 = ฟีเจอร์ช่วยลด log-loss, ค่า <= 0 = ไม่ช่วย/เป็นสัญญาณรบกวน
    คืน (DataFrame, base): DataFrame มีคอลัมน์ กลุ่ม, delta (เฉลี่ย), std, ฟีเจอร์ในกลุ่ม • base = log-loss ก่อนสลับค่า"""
    d = master[master["FTHG"].notna()].sort_values("Date", kind="stable").reset_index(drop=True)
    end = len(d) - int(skip_last)
    val = d.iloc[end - n_val:end]
    model = ml.train(d, list(features), params or ml.DEFAULT_PARAMS, before=val["Date"].min())
    base = _logloss_of(model, val)
    rng = np.random.default_rng(seed)
    rows = []
    for name, cols in feature_groups(features).items():
        deltas = []
        for _ in range(repeats):
            shuffled = val.copy()
            perm = rng.permutation(len(val))
            shuffled[cols] = val[cols].to_numpy()[perm]
            deltas.append(_logloss_of(model, shuffled) - base)
        rows.append({"กลุ่ม": name, "delta": float(np.mean(deltas)), "std": float(np.std(deltas)), "ฟีเจอร์": cols})
    return pd.DataFrame(rows).sort_values("delta", ascending=False).reset_index(drop=True), base

def season_predictions(master, features, params=None, season=None, step_weeks=1):
    """ทำนายย้อนหลัง \"ทุกนัด\" ของฤดูกาลหนึ่ง (ค่าเริ่มต้น = ฤดูกาลปัจจุบัน) แบบ walk-forward
    แต่ละสัปดาห์เทรนใหม่ด้วยนัดที่แข่งก่อนวันนั้นเท่านั้น จึงไม่แอบดูผล
    ต่างจาก walk_forward ตรงที่ \"ไม่ข้าม\" นัดของทีมเลื่อนชั้น (ทายด้วย Elo เริ่มต้น + ธง NoPrev) แต่ติดป้ายไว้ใน new_team
    คืน DataFrame รายนัด (คอลัมน์เดียวกับ walk_forward + xg_home, xg_away, new_team)"""
    from config import current_season_year, season_of

    params = params or ml.DEFAULT_PARAMS
    season = current_season_year() if season is None else int(season)
    d = master[master["FTHG"].notna()].sort_values("Date", kind="stable").reset_index(drop=True)
    test = d[season_of(d["Date"]) == season]
    if test.empty:
        return pd.DataFrame()
    start = test["Date"].min().normalize()
    block_no = ((test["Date"] - start).dt.days // 7) // max(1, int(step_weeks))

    rows = []
    for _, block in test.groupby(block_no):
        cutoff = block["Date"].min().normalize()
        train = d[d["Date"] < cutoff]
        model = ml.train(train, features, params)
        if model is None:
            continue
        t_out = np.where(train["FTHG"] > train["FTAG"], 0, np.where(train["FTHG"] < train["FTAG"], 2, 1))
        base = np.bincount(t_out, minlength=3) / len(t_out)
        for (_, r), p in zip(block.iterrows(), ml.predict_rows(model, block)):
            ph, pa = map(int, p["score"].split(" - "))
            rows.append({
                "Date": r["Date"], "HomeTeam": r["HomeTeam"], "AwayTeam": r["AwayTeam"],
                "real_score": f"{int(r['FTHG'])} - {int(r['FTAG'])}", "pred_score": p["score"],
                "real_idx": outcome_index(r["FTHG"], r["FTAG"]), "score_idx": outcome_index(ph, pa),
                "p_home": p["p_home"] / 100, "p_draw": p["p_draw"] / 100, "p_away": p["p_away"] / 100,
                "b_home": base[0], "b_draw": base[1], "b_away": base[2],
                "xg_home": p["xg_home"], "xg_away": p["xg_away"], "new_team": bool(p["missing"]),
            })
    return pd.DataFrame(rows)