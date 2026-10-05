import pandas as pd
import streamlit as st

import data_prep
import evaluation as ev
import predictor as ml
import ui
from config import LEAGUES
from fetch_football_data import DataError, get_historical_data, get_upcoming_fixtures

st.set_page_config(page_title="AI Football Predictor", page_icon=":material/sports_soccer:", layout="wide",
                   initial_sidebar_state="collapsed")
st.markdown(ui.CSS, unsafe_allow_html=True)


def html(s):
    st.markdown(s, unsafe_allow_html=True)


# ---------------------------------------------------------------- cached wrappers
@st.cache_data(ttl=3600, show_spinner=False)
def cached_master(league, fixtures=None):
    return data_prep.build_league_master(league, fixtures)


@st.cache_data(ttl=86400, show_spinner=False)
def cached_model(master, features, params, before=None):
    return ml.train(master, features, params, before)


@st.cache_data(ttl=86400, show_spinner=False)
def cached_walk_forward(master, features, params, n_eval):
    return ev.walk_forward(master, features, params, n_eval)


@st.cache_data(ttl=86400, show_spinner=False)
def cached_tuning(master, features):
    return ml.run_tuning(master, features)


@st.cache_data(ttl=86400, show_spinner=False)
def cached_season(master, features, params):
    return ev.season_predictions(master, features, params)


OUTCOME_TH = ["เหย้าชนะ", "เสมอ", "เยือนชนะ"]

# ---------------------------------------------------------------- หัวแอป + เลือกลีก
html(ui.app_bar("ML ประเมินประตูคาดหวัง แล้ว Poisson แจกแจงสกอร์"))
c_league, c_refresh = st.columns([4, 1.4], vertical_alignment="center")
league = c_league.radio("เลือกลีกฟุตบอล", list(LEAGUES.keys()), horizontal=True, label_visibility="collapsed")
if c_refresh.button("อัปเดตข้อมูล", icon=":material/refresh:", width="stretch"):
    try:
        with st.spinner("กำลังดึงข้อมูล..."):
            get_historical_data.clear()
            get_upcoming_fixtures.clear()
            get_historical_data(league)
        cached_master.clear()
        st.rerun()
    except DataError as e:
        st.error(str(e))

try:
    master, prep_warnings = cached_master(league)
except FileNotFoundError as e:
    st.error(f"{e}\n\nรัน `python fetch_football_data.py` หรือกดปุ่มอัปเดตข้อมูลก่อน")
    st.stop()

fsets = data_prep.feature_sets(master)
set_name = next(iter(fsets))
features = tuple(fsets[set_name])
params = ml.load_params(league)
for w in prep_warnings:
    st.warning(w)
if "ไม่มี FBref" in set_name:
    st.warning("ยังไม่มีไฟล์ FBref ใน data/fbref/ (รัน `python fetch_fbref_data.py`)")

played = master[~master["is_fixture"]]
model = cached_model(master, features, params)

# โปรแกรมทั้งหมดที่ยังไม่แข่ง (ดึงครั้งเดียว ใช้ทั้งแท็บทำนายและตราสโมสรของแท็บผลแข่ง)
try:
    upcoming = get_upcoming_fixtures(league, limit=None)
except DataError as e:
    upcoming = pd.DataFrame()
    upcoming_error = str(e)
else:
    upcoming_error = None
crests = ui.crest_map(upcoming)

tab_fx, tab_season, tab_acc = st.tabs([":material/calendar_month: ทำนาย", ":material/sports_soccer: ผลทั้งฤดูกาล",
                                       ":material/monitoring: ความแม่นยำ"])

# =========================== TAB: ทำนายล่วงหน้ารายสัปดาห์ ===========================
with tab_fx:
    if upcoming_error:
        st.error(f"ดึงโปรแกรมไม่ได้: {upcoming_error}")
    if upcoming.empty:
        html(ui.empty("inbox", "ไม่มีข้อมูลโปรแกรมแข่งที่กำหนดเวลาไว้"))
    else:
        upcoming = upcoming.copy()
        upcoming["_kickoff_utc"] = upcoming["_kickoff_utc"].fillna(pd.Timestamp.utcnow().tz_localize(None))
        upcoming["_week"] = data_prep.matchweek_start(upcoming["_kickoff_utc"])
        weeks = sorted(upcoming["_week"].unique())
        counts = upcoming["_week"].value_counts()

        def week_label(w):
            w = pd.Timestamp(w)
            return f"{w:%d/%m} – {w + pd.Timedelta(days=6):%d/%m/%Y}  ({counts[w]} นัด)"

        week = st.selectbox("สัปดาห์ที่จะทำนาย (ค่าเริ่มต้น = สัปดาห์ที่กำลังจะถึง)", weeks, index=0, format_func=week_label)
        wk = upcoming[upcoming["_week"] == week].sort_values("_kickoff_utc").reset_index(drop=True)

        known = set(played["HomeTeam"]) | set(played["AwayTeam"])
        fx = wk.rename(columns={"ทีมเหย้า": "HomeTeam", "ทีมเยือน": "AwayTeam", "_kickoff_utc": "Date"})
        fx, not_found = data_prep.prepare_fixtures(fx[["Date", "HomeTeam", "AwayTeam"]], known)
        m_fx, _ = cached_master(league, fx)          # ใส่เฉพาะนัดของสัปดาห์นี้ ฟอร์ม/วันพักจึงคำนวณจากนัดที่แข่งจบแล้วล้วน ๆ
        preds = ml.predict_rows(model, m_fx[m_fx["is_fixture"]])

        items = [{
            "home": r["ทีมเหย้า"], "away": r["ทีมเยือน"],
            "home_crest": crests.get(r["ทีมเหย้า"]), "away_crest": crests.get(r["ทีมเยือน"]),
            "kickoff": r["_kickoff_utc"], "status": r.get("_status"),
            "p": (p["p_home"], p["p_draw"], p["p_away"]), "score": p["score"], "xg": (p["xg_home"], p["xg_away"]),
        } for (_, r), p in zip(wk.iterrows(), preds)]

        html(ui.section("calendar", f"ทำนายล่วงหน้า · {league}", f"{len(items)} นัด"))
        html(ui.hero(items[0]))
        if len(items) > 1:
            html(ui.section("ball", "นัดที่เหลือของสัปดาห์"))
            html(ui.match_grid(items[1:]))
        html(ui.note("ผลที่ AI เชื่อ = ผลที่ความน่าจะเป็นสูงสุด (ใช้ตัวนี้เป็นหลัก) • สกอร์ที่แสดงคือสกอร์เดี่ยวที่น่าจะเป็นที่สุด มักออก 1 - 1"))

        export = pd.DataFrame({
            "วัน-เวลา (ไทย)": wk["วัน-เวลาแข่งขัน (ไทย)"], "ทีมเหย้า": wk["ทีมเหย้า"], "ทีมเยือน": wk["ทีมเยือน"],
            "AI ทำนายสกอร์": [i["score"] for i in items],
            "เหย้าชนะ %": [round(i["p"][0], 1) for i in items], "เสมอ %": [round(i["p"][1], 1) for i in items],
            "เยือนชนะ %": [round(i["p"][2], 1) for i in items],
            "ผลที่ AI เชื่อ": [OUTCOME_TH[max(range(3), key=lambda k: i["p"][k])] for i in items],
        })
        st.download_button("ดาวน์โหลดคำทำนาย (CSV)", export.to_csv(index=False).encode("utf-8-sig"),
                           f"upcoming_{league.replace(' ', '_')}.csv", "text/csv", icon=":material/download:")
        if not_found:
            st.warning("ไม่พบสถิติของ: " + ", ".join(not_found) + " (ใช้ Elo เริ่มต้น/ค่ากลางแทน)")

    html(ui.section("zap", "จำลองทำนายคู่อื่น ๆ"))
    teams = model["teams"]
    c1, c2 = st.columns(2)
    home_team = c1.selectbox("ทีมเหย้า", teams, index=0)
    away_team = c2.selectbox("ทีมเยือน", teams, index=min(1, len(teams) - 1))
    if st.button("ทำนายผลการแข่งขัน", type="primary", icon=":material/bolt:"):
        if home_team == away_team:
            st.warning("กรุณาเลือกสองทีมที่ต่างกัน")
        else:
            sim = pd.DataFrame({"Date": [pd.Timestamp.utcnow().tz_localize(None)],
                                "HomeTeam": [home_team], "AwayTeam": [away_team]})
            m_sim, _ = cached_master(league, sim)
            row = m_sim[m_sim["is_fixture"]].iloc[0]
            p = ml.predict_match(model, row)
            html(ui.hero({"home": home_team, "away": away_team, "home_crest": crests.get(home_team),
                          "away_crest": crests.get(away_team), "kickoff": None, "status": None,
                          "p": (p["p_home"], p["p_draw"], p["p_away"]), "score": p["score"],
                          "xg": (p["xg_home"], p["xg_away"])}, tag="จำลอง"))
            html(ui.note(f"Elo {row['HomeElo']:.0f} vs {row['AwayElo']:.0f} • วันพัก {row['HomeRestDays']:.1f} vs {row['AwayRestDays']:.1f}"))

    with st.expander(":material/insights: ฟีเจอร์ไหนสำคัญที่สุดต่อโมเดล"):
        imp = ml.feature_importance(model).rename("ความสำคัญ").rename_axis("ฟีเจอร์").reset_index()
        try:   # เรียงจากมากไปน้อย (streamlit รุ่นเก่าไม่รองรับ sort/horizontal)
            st.bar_chart(imp, x="ฟีเจอร์", y="ความสำคัญ", horizontal=True, sort="-ความสำคัญ", color=ui.accent())
        except TypeError:
            st.bar_chart(imp.set_index("ฟีเจอร์"))

# =========================== TAB: ผลทั้งฤดูกาลนี้ ===========================
with tab_season:
    with st.spinner("กำลังย้อนทำนายทั้งฤดูกาล..."):
        season_res = cached_season(played, features, params)
    if season_res.empty:
        html(ui.empty("inbox", "ฤดูกาลนี้ยังไม่มีนัดที่แข่งจบ"))
    else:
        P = season_res[["p_home", "p_draw", "p_away"]].to_numpy()
        believed = P.argmax(axis=1)
        real = season_res["real_idx"].to_numpy()
        right = believed == real
        exact = (season_res["pred_score"] == season_res["real_score"]).to_numpy()
        n = len(season_res)
        s = ev.summarize(season_res)
        acc = right.mean() * 100

        html(ui.section("trophy", f"ผลทั้งฤดูกาลนี้ · {league}", f"{n} นัด"))
        html(ui.tiles(
            ui.tile(int(right.sum()), f"/{n}", f"ทายผลถูก ({acc:.0f}%)", "lime" if acc >= 50 else "amber"),
            ui.tile(int(exact.sum()), f"/{n}", "สกอร์ตรงเป๊ะ", "blue"),
            ui.tile(f"{s['logloss']:.3f}", "", "Log-loss (ต่ำ = ดี)", "amber"),
        ))
        rows = []
        for i, name in enumerate(OUTCOME_TH):
            mask = believed == i
            if mask.any():
                rows.append((f"เมื่อ AI เชื่อ{name}", right[mask].mean() * 100, f"{int(mask.sum())} นัด"))
        rows.append(("เทียบ: เดาเจ้าบ้านชนะทุกนัด", s["baseline_home_acc"] * 100, f"{n} นัด"))
        html("<div style='height:.8rem'></div>" + ui.bars(rows))
        html(ui.note(f"ทายถูกคลาดเคลื่อนได้ราว ±{s['accuracy_ci'] * 100:.0f} จุด • Log-loss "
                     f"{s['logloss'] - s['baseline_logloss']:+.3f} เทียบสัดส่วนเฉลี่ยของลีก • "
                     "ย้อนทายทีละสัปดาห์ด้วยข้อมูลก่อนวันเตะเท่านั้น (ไม่แอบดูผล) • ทีมเลื่อนชั้นไม่ถูกข้ามแต่ติดป้ายทีมใหม่"))

        flt = st.radio("กรองผล", ["ทั้งหมด", "ทายถูก", "พลาด"], horizontal=True, label_visibility="collapsed", key=f"flt_{league}")
        order = list(range(n - 1, -1, -1))                            # นัดล่าสุดอยู่บนสุด
        if flt == "ทายถูก":
            order = [i for i in order if right[i]]
        elif flt == "พลาด":
            order = [i for i in order if not right[i]]
        out_rows = []
        for i in order:
            r = season_res.iloc[i]
            out_rows.append(ui.result_row({
                "kickoff": r["Date"], "home": r["HomeTeam"], "away": r["AwayTeam"],
                "home_crest": crests.get(r["HomeTeam"]), "away_crest": crests.get(r["AwayTeam"]),
                "real": r["real_score"], "pred": r["pred_score"], "p": tuple(P[i] * 100),
                "right": bool(right[i]), "exact": bool(exact[i]), "new_team": bool(r["new_team"]),
            }))
        html("".join(out_rows) if out_rows else ui.empty("inbox", "ไม่มีนัดที่ตรงกับตัวกรอง"))

        disp = ev.results_for_display(season_res)
        st.download_button("ดาวน์โหลดผลทั้งฤดูกาล (CSV)", disp.to_csv(index=False).encode("utf-8-sig"),
                           f"season_{league.replace(' ', '_')}.csv", "text/csv", icon=":material/download:")

# =========================== TAB: วัดความแม่นยำ ===========================
with tab_acc:
    st.markdown(ui.section("chart", f"วัดความแม่นยำแบบ Walk-forward · {league}"), unsafe_allow_html=True)
    st.caption("ย้อนทำนายนัดในอดีตทีละสัปดาห์ด้วยข้อมูลก่อนวันเตะเท่านั้น แล้วเทียบกับ baseline (สัดส่วนชนะ/เสมอ/แพ้เฉลี่ยของลีก)")
    max_eval = len(played) - ev.MIN_TRAIN_MATCHES
    if max_eval < 50:
        st.info("ข้อมูลยังไม่พอ")
    else:
        top = min(max_eval, 900)
        n_eval = st.slider("จำนวนนัดล่าสุดที่ใช้ทดสอบ", 50, top, min(380, top), step=10)
        key = f"wf_{league}"
        if st.button("เริ่มวัดผล", type="primary"):
            st.session_state[key] = True
        if st.session_state.get(key):
            with st.spinner("กำลังย้อนทำนายทีละสัปดาห์ (อาจใช้เวลา 30–90 วินาที)..."):
                out = cached_walk_forward(played, features, params, n_eval)
            s = ev.summarize(out["results"])
            if s is None:
                st.warning("ไม่มีนัดที่ทดสอบได้")
            else:
                st.markdown(f"ทดสอบ **{s['n']} นัด** ({s['date_from']:%d/%m/%Y} – {s['date_to']:%d/%m/%Y})"
                            + (f" • ข้าม {out['skipped']} นัด" if out["skipped"] else ""))
                c1, c2, c3 = st.columns(3)
                c1.metric("ทายแพ้/เสมอ/ชนะถูก", f"{s['accuracy'] * 100:.1f}%",
                          delta=f"{(s['accuracy'] - s['baseline_home_acc']) * 100:+.1f} จุด เทียบเดาเจ้าบ้านชนะทุกนัด")
                c2.metric("ทายถูก (จากสกอร์ที่แสดง)", f"{s['accuracy_from_score'] * 100:.1f}%")
                c3.metric("ทายสกอร์ตรงเป๊ะ", f"{s['exact_score'] * 100:.1f}%")
                c4, c5 = st.columns(2)
                c4.metric("Log-loss (ต่ำ=ดี)", f"{s['logloss']:.3f}",
                          delta=f"{s['logloss'] - s['baseline_logloss']:+.3f} เทียบสัดส่วนเฉลี่ยลีก", delta_color="inverse")
                c5.metric("Brier (ต่ำ=ดี)", f"{s['brier']:.3f}",
                          delta=f"{s['brier'] - s['baseline_brier']:+.3f} เทียบสัดส่วนเฉลี่ยลีก", delta_color="inverse")
                st.caption(f"accuracy คลาดเคลื่อนได้ราว ±{s['accuracy_ci'] * 100:.1f} จุด (95%)")

                st.markdown("##### Calibration")
                st.dataframe(ev.calibration_table(out["results"]), width="stretch", hide_index=True)
                with st.expander("ดูผลรายนัด"):
                    disp = ev.results_for_display(out["results"])
                    st.dataframe(disp, width="stretch", hide_index=True)
                    st.download_button("ดาวน์โหลด (CSV)", disp.to_csv(index=False).encode("utf-8-sig"),
                                       f"walk_forward_{league.replace(' ', '_')}.csv", "text/csv")

    st.divider()
    with st.expander(":material/tune: จูนพารามิเตอร์ของ Random Forest"):
        st.caption("ลอง n_estimators / max_depth / min_samples_leaf บนช่วงเก่า แล้วตรวจกับช่วงล่าสุดที่ไม่เคยใช้เลือกค่า (ใช้เวลาหลายนาที)")
        tkey = f"tune_{league}"
        if st.button("เริ่มจูน"):
            with st.spinner("กำลังลองทุกชุดค่า..."):
                st.session_state[tkey] = cached_tuning(played, features)
            if st.session_state[tkey] is None:
                st.warning("ข้อมูลยังไม่พอสำหรับการจูน")
        tr = st.session_state.get(tkey)
        if tr:
            st.markdown(f"ค่าที่ดีที่สุดในช่วงจูน ({tr['n_tune']} นัด): `{tr['best']}`")
            st.dataframe(tr["grid"].round(4), width="stretch", hide_index=True)
            st.caption(f"ตรวจกับ {tr['n_holdout']} นัดล่าสุดที่ไม่ได้ใช้เลือกค่า")
            st.dataframe(tr["holdout"], width="stretch", hide_index=True)
            if tr["improved"]:
                st.success("ดีกว่าค่าตั้งต้นในช่วงตรวจ แนะนำให้ใช้")
                if st.button("ใช้ค่านี้กับลีกนี้"):
                    ml.save_params(league, tr["best"])
                    st.session_state.pop(tkey, None)
                    st.rerun()
            else:
                st.info("ไม่ดีกว่าค่าตั้งต้นในช่วงตรวจ จึงไม่แนะนำให้เปลี่ยน")
        if not ml.is_default(params) and st.button("รีเซ็ตเป็นค่าตั้งต้น"):
            ml.reset_params(league)
            st.rerun()

# ---------------------------------------------------------------- ข้อมูลโมเดล
with st.expander(":material/info: ข้อมูลโมเดลและข้อมูลที่ใช้"):
    cov = (master["Home_PrevPoss"].notna().mean() if "Home_PrevPoss" in master else 0) * 100
    st.markdown(
        f"- ฟีเจอร์: {set_name} ({len(features)} ตัว)\n"
        f"- เทรนด้วย {len(played):,} นัด ({played['Date'].min():%d/%m/%Y} – {played['Date'].max():%d/%m/%Y})\n"
        f"- Random Forest {params['n_estimators']} ต้น, depth {params['max_depth']}, leaf {params['min_samples_leaf']} "
        f"({'ค่าตั้งต้น' if ml.is_default(params) else 'ค่าที่จูนแล้ว'})\n"
        f"- ครอบคลุมสถิติ FBref {cov:.0f}% ของนัด"
    )