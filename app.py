import pandas as pd
import streamlit as st

import data_prep
import evaluation as ev
import predictor as ml
import ui
from config import LEAGUES, season_of
from fetch_football_data import DataError, get_historical_data, get_upcoming_fixtures
import ui

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


@st.cache_data(ttl=3600, show_spinner=False)
def cached_latest_strength(league, teams):
    """Elo / PPM5 ล่าสุดของทุกทีม (= ค่าที่ใช้ทำนายนัดถัดไป หลังนัดที่แข่งจบล่าสุด)
    ใช้วิธีเดียวกับปุ่มจำลองทำนาย: ใส่นัดสมมติหลังนัดล่าสุด แล้วอ่านค่า "ก่อนเตะ" ของแต่ละทีม
    (HomeElo ใน Master คือค่าก่อนแข่งนัดนั้น จุดสุดท้ายของเส้นกราฟจึงช้ากว่าค่าจริงไปหนึ่งนัด)"""
    teams = list(teams)
    n = len(teams)
    fx = pd.DataFrame({"Date": pd.Timestamp.now("UTC").tz_localize(None),
                       "HomeTeam": [teams[i] for i in range(0, n, 2)],
                       "AwayTeam": [teams[(i + 1) % n] for i in range(0, n, 2)]})
    m, _ = data_prep.build_league_master(league, fx)
    f = m[m["is_fixture"]]
    rows = {}
    for side in ("Home", "Away"):
        for team, elo, ppm in zip(f[f"{side}Team"], f[f"{side}Elo"], f[f"{side}_PPM5"]):
            rows[team] = {"Elo": float(elo), "PPM5": float(ppm)}
    return pd.DataFrame.from_dict(rows, orient="index")


OUTCOME_TH = ["เหย้าชนะ", "เสมอ", "เยือนชนะ"]

# ---------------------------------------------------------------- หัวแอป + เลือกลีก
html(ui.app_bar("ML ประเมินประตูคาดหวัง แล้ว Poisson แจกแจงสกอร์"))
c_league, c_refresh = st.columns([4, 1.4], vertical_alignment="center")
league = c_league.radio("เลือกลีกฟุตบอล", list(LEAGUES.keys()), horizontal=True, label_visibility="collapsed")
if c_refresh.button("อัปเดตข้อมูล", icon=":material/refresh:", width="stretch"):
    try:
        placeholder = st.empty()
        placeholder.markdown(ui.spinning_ball_loader("กำลังดึงข้อมูลฟุตบอลล่าสุด..."), unsafe_allow_html=True)
        get_historical_data.clear()
        get_upcoming_fixtures.clear()
        get_historical_data(league)
        cached_master.clear()
        placeholder.empty()
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

tab_fx, tab_season,tab_table, tab_acc  = st.tabs([":material/calendar_month: ทำนาย", ":material/sports_soccer: ผลทั้งฤดูกาล",
                                        ":material/format_list_numbered: ตารางคะแนน" , ":material/monitoring: ความแม่นยำ "])

# =========================== TAB: ทำนายล่วงหน้ารายสัปดาห์ ===========================
with tab_fx:
    if upcoming_error:
        st.error(f"ดึงโปรแกรมไม่ได้: {upcoming_error}")
    if upcoming.empty:
        html(ui.empty("inbox", "ไม่มีข้อมูลโปรแกรมแข่งที่กำหนดเวลาไว้"))
    else:
        upcoming = upcoming.copy()
        upcoming["_kickoff_utc"] = upcoming["_kickoff_utc"].fillna(pd.Timestamp.now("UTC").tz_localize(None))
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
            sim = pd.DataFrame({"Date": [pd.Timestamp.now("UTC").tz_localize(None)],
                                "HomeTeam": [home_team], "AwayTeam": [away_team]})
            m_sim, _ = cached_master(league, sim)
            row = m_sim[m_sim["is_fixture"]].iloc[0]
            p = ml.predict_match(model, row)
            html(ui.hero({"home": home_team, "away": away_team, "home_crest": crests.get(home_team),
                          "away_crest": crests.get(away_team), "kickoff": None, "status": None,
                          "p": (p["p_home"], p["p_draw"], p["p_away"]), "score": p["score"],
                          "xg": (p["xg_home"], p["xg_away"])}, tag="จำลอง"))
            html(ui.note(f"Elo {row['HomeElo']:.0f} vs {row['AwayElo']:.0f} • วันพัก {row['HomeRestDays']:.1f} vs {row['AwayRestDays']:.1f}"))

    html(ui.section("chart", f"แนวโน้มฟอร์มทีมและค่าพลัง Elo · {league}"))
    view_mode = st.radio("รูปแบบกราฟ", ["เส้นแนวโน้มรายทีม", "จุดค่าล่าสุด (เทียบทีม)"],
                         horizontal=True, key="trend_view_mode")
    t_col1, t_col2 = st.columns([2, 1])
    trend_team = t_col1.selectbox("เลือกทีมที่ต้องการดูเส้นกราฟฟอร์ม", teams, key="trend_team_select")
    metric_choice = t_col2.selectbox("เลือกค่าที่ต้องการแสดง", ["Elo (ค่าพลัง)", "PPM5 (แต้มเฉลี่ย 5 นัด)"], key="trend_metric_select")
    col_to_plot = "Elo" if "Elo" in metric_choice else "PPM5"

    if view_mode.startswith("เส้น"):
        if trend_team:
            h_t = played[played["HomeTeam"] == trend_team][["Date", "HomeElo", "Home_PPM5"]].rename(columns={"HomeElo": "Elo", "Home_PPM5": "PPM5"})
            a_t = played[played["AwayTeam"] == trend_team][["Date", "AwayElo", "Away_PPM5"]].rename(columns={"AwayElo": "Elo", "Away_PPM5": "PPM5"})
            timeline_df = pd.concat([h_t, a_t]).sort_values("Date").dropna(subset=["Elo"]).set_index("Date")

            if not timeline_df.empty:
                st.line_chart(timeline_df[[col_to_plot]])
                st.caption(f"กราฟแสดงพัฒนาการของ {trend_team} ตลอดฤดูกาล ช่วยให้เห็นช่วงที่ฟอร์มกำลังพุ่งขึ้นหรือตกลงอย่างชัดเจน")
            else:
                st.info("ยังไม่มีข้อมูลเพียงพอสำหรับสร้างกราฟของทีมนี้")
    else:
        import plotly.graph_objects as go

        latest = cached_latest_strength(league, tuple(teams))
        season_no = season_of(played["Date"])
        in_season = played.loc[season_no == season_no.max()]
        active = set(in_season["HomeTeam"]) | set(in_season["AwayTeam"])
        in_league = [t for t in teams if t in active and t in latest.index]      # ทีมในลีกฤดูกาลล่าสุด
        fmt = ".0f" if col_to_plot == "Elo" else ".2f"
        mean_val = float(latest.loc[in_league, col_to_plot].mean())

        cmp_mode = st.radio("เทียบกับ", ["ทุกทีมในลีก", "เลือกทีมเอง"], horizontal=True, key="trend_cmp_mode")
        if cmp_mode == "ทุกทีมในลีก":
            shown = list(in_league)
        else:
            shown = st.multiselect("เลือกทีมที่ต้องการเทียบ (ทีมที่เลือกด้านบนจะแสดงเสมอ)", teams, key=f"trend_cmp_teams_{league}")
        shown = [t for t in dict.fromkeys([trend_team] + list(shown)) if t in latest.index]

        d = latest.loc[shown, col_to_plot].sort_values()
        stems_x, stems_y = [], []
        for t, v in d.items():                      # เส้นบาง ๆ จากค่าเฉลี่ยลีกไปหาแต่ละทีม ให้เห็นว่าห่างกันเท่าไร
            stems_x += [mean_val, v, None]
            stems_y += [t, t, None]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=stems_x, y=stems_y, mode="lines", hoverinfo="skip", showlegend=False,
                                 line=dict(color="rgba(0,0,0,0.45)", width=2.5))) # 👈 เส้นโยงเข้มขึ้น
        fig.add_trace(go.Scatter(
            x=d.values, y=list(d.index), mode="markers", showlegend=False,
            marker=dict(color=[ui.accent() if t == trend_team else "#8a8576" for t in d.index],
                        size=[18 if t == trend_team else 11 for t in d.index],
                        line=dict(color="white", width=1.5)),
            hovertemplate="%{y}: %{x:" + fmt + "}<extra></extra>"))
        fig.add_vline(x=mean_val, line_dash="dash", line_color="rgba(0,0,0,0.8)", line_width=2,
                      annotation_text=f"ค่าเฉลี่ยลีก {format(mean_val, fmt)}", annotation_position="top",
                      annotation_font=dict(color="black", size=13, family="Prompt, sans-serif")) # 👈 เส้นและตัวหนังสือชัดขึ้น
        fig.update_layout(
            xaxis=dict(
                title=metric_choice, 
                gridcolor="rgba(0,0,0,0.4)",  # 👈 เข้มขึ้นมาก
                zeroline=False,
                tickfont=dict(color="black", size=13, family="Prompt, sans-serif"),
                title_font=dict(color="black", size=14, family="Prompt, sans-serif")
            ),
            yaxis=dict(
                title="", 
                categoryorder="array", 
                categoryarray=list(d.index), 
                gridcolor="rgba(0,0,0,0.2)",  # 👈 เพิ่มเส้นแกน Y แนวนอนให้ชัดขึ้น
                tickfont=dict(color="black", size=13, family="Prompt, sans-serif")
            ),
            margin=dict(l=20, r=20, t=40, b=20), 
            height=max(280, 30 * len(d) + 100),
            plot_bgcolor="rgba(0,0,0,0)", 
            paper_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(fig, width="stretch")

        if trend_team in in_league:
            me = float(latest.loc[trend_team, col_to_plot])
            rank = int((latest.loc[in_league, col_to_plot] > me).sum()) + 1
            st.caption(f"{trend_team}: {format(me, fmt)} • ต่างจากค่าเฉลี่ยลีก {format(me - mean_val, '+' + fmt)} "
                       f"• อันดับ {rank}/{len(in_league)} ของลีกฤดูกาลล่าสุด • ค่าล่าสุด = ค่าที่ใช้ทำนายนัดถัดไป")
        else:
            me = float(latest.loc[trend_team, col_to_plot]) if trend_team in latest.index else None
            st.caption(f"{trend_team} ไม่ได้อยู่ในลีกฤดูกาลล่าสุด ค่าที่แสดงเป็นค่าสุดท้ายที่มี (Elo ถูกดึงเข้าหาค่ากลางทุกต้นฤดูกาลตามกติกาของโมเดล)")
        with st.expander("ดูตัวเลขเทียบกัน"):
            tbl = d.sort_values(ascending=False).rename(col_to_plot).rename_axis("ทีม").reset_index()
            tbl.insert(0, "ลำดับ", range(1, len(tbl) + 1))
            if me is not None:
                tbl[f"ต่างจาก {trend_team}"] = tbl[col_to_plot] - me
            st.dataframe(tbl.round(0 if col_to_plot == "Elo" else 2), width="stretch", hide_index=True)

    with st.expander(":material/insights: ฟีเจอร์ไหนสำคัญที่สุดต่อโมเดล"):
        imp = ml.feature_importance(model).rename("ความสำคัญ").rename_axis("ฟีเจอร์").reset_index()
        try:   # เรียงจากมากไปน้อย (streamlit รุ่นเก่าไม่รองรับ sort/horizontal)
            st.bar_chart(imp, x="ฟีเจอร์", y="ความสำคัญ", horizontal=True, sort="-ความสำคัญ", color=ui.accent())
        except TypeError:
            st.bar_chart(imp.set_index("ฟีเจอร์"))

# =========================== TAB: ผลทั้งฤดูกาลนี้ ===========================
with tab_season:
    placeholder = st.empty()
    placeholder.markdown(ui.spinning_ball_loader("กำลังจำลองผลการแข่งขันทั้งฤดูกาล..."), unsafe_allow_html=True)
    season_res = cached_season(played, features, params)
    placeholder.empty()
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
        exact_acc = exact.mean() * 100

        html(ui.section("trophy", f"ผลทั้งฤดูกาลนี้ · {league}", f"{n} นัด"))
        html(ui.tiles(
            ui.tile(int(right.sum()), f"/{n}", f"ทายผลถูก ({acc:.0f}%)", "lime" if acc >= 50 else "amber"),
            ui.tile(int(exact.sum()), f"/{n}", f"สกอร์ตรงเป๊ะ ({exact_acc:.0f}%)", "blue"),
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
        # จัดรูปแบบ DataFrame สำหรับส่งออกเป็น CSV ในสไตล์เดียวกัน
        export_season = pd.DataFrame({
            "วันที่": disp["วันที่"], 
            "ทีมเหย้า": disp["ทีมเหย้า"], 
            "ทีมเยือน": disp["ทีมเยือน"],
            "ผลจริง": disp["ผลจริง"], 
            "AI ทายสกอร์": disp["AI ทายสกอร์"],
            "เหย้าชนะ %": disp["เหย้าชนะ %"], 
            "เสมอ %": disp["เสมอ %"], 
            "เยือนชนะ %": disp["เยือนชนะ %"],
            "ผลที่ AI เชื่อ": disp["ผลที่ AI เชื่อ"],
            "ผลจริง (H/D/A)": disp["ผลจริง (H/D/A)"],
            "ถูก/ผิด": disp["ถูก/ผิด"],
        })
        
        st.download_button(
            "ดาวน์โหลดผลทั้งฤดูกาล (CSV)", 
            export_season.to_csv(index=False).encode("utf-8-sig"),
            f"season_{league.replace(' ', '_')}.csv", 
            "text/csv", 
            icon=":material/download:"
        )
# =========================== TAB: ตารางคะแนน ===========================
with tab_table:
    from config import current_season_year, season_of
    html(ui.section("trophy", f"ตารางคะแนน · {league}"))
    
    curr_matches = played[season_of(played["Date"]) == current_season_year()]
    if curr_matches.empty:
        curr_matches = played
        
    table_dict = {}
    for _, r in curr_matches.iterrows():
        h, a = r["HomeTeam"], r["AwayTeam"]
        hg, ag = int(r["FTHG"]), int(r["FTAG"])
        
        for t in [h, a]:
            if t not in table_dict:
                table_dict[t] = {"P": 0, "W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "Pts": 0}
                
        table_dict[h]["P"] += 1; table_dict[a]["P"] += 1
        table_dict[h]["GF"] += hg; table_dict[h]["GA"] += ag
        table_dict[a]["GF"] += ag; table_dict[a]["GA"] += hg
        
        if hg > ag:
            table_dict[h]["W"] += 1; table_dict[h]["Pts"] += 3
            table_dict[a]["L"] += 1
        elif hg < ag:
            table_dict[a]["W"] += 1; table_dict[a]["Pts"] += 3
            table_dict[h]["L"] += 1
        else:
            table_dict[h]["D"] += 1; table_dict[h]["Pts"] += 1
            table_dict[a]["D"] += 1; table_dict[a]["Pts"] += 1
            
    tdf = pd.DataFrame.from_dict(table_dict, orient="index")
    tdf["GD"] = tdf["GF"] - tdf["GA"]
    tdf = tdf.sort_values(by=["Pts", "GD", "GF"], ascending=False).reset_index()
    tdf.rename(columns={
        "index": "ทีม", "P": "แข่ง", "W": "ชนะ", "D": "เสมอ", 
        "L": "แพ้", "GF": "ได้", "GA": "เสีย", "GD": "ลูกได้เสีย", "Pts": "แต้ม"
    }, inplace=True)
    tdf["อันดับ"] = range(1, len(tdf) + 1)
    
    # 🌟 เรียกใช้ฟังก์ชัน HTML ของ UI ตัวเดียวจบ จัดระเบียบหัวและตารางให้อัตโนมัติ
    html(ui.league_table(tdf, crests))
    html(ui.note("ตารางคะแนนคำนวณอัตโนมัติจากผลการแข่งขันจริง • แถบสีเขียว = โซนหัวตาราง • แถบสีแดง = โซนท้ายตาราง"))


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
            placeholder = st.empty()
            placeholder.markdown(ui.spinning_ball_loader("กำลังย้อนทำนายทีละสัปดาห์ (โปรดรอสักครู่)..."), unsafe_allow_html=True)
            out = cached_walk_forward(played, features, params, n_eval)
            placeholder.empty()
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

                st.caption(f"โอกาสเสมอที่โมเดลให้เฉลี่ย {s['draw_pred'] * 100:.1f}% • เสมอจริง {s['draw_real'] * 100:.1f}% "
                            f"(ต่าง {s['draw_gap'] * 100:+.1f} จุด, z = {s['draw_z']:+.2f})")

                st.markdown("##### 📊 กราฟสรุปประสิทธิภาพการทำนาย")
                import plotly.graph_objects as go
                
                categories = ["ทายผลถูก (1X2)", "ทายถูกจากสกอร์", "ทายสกอร์ตรงเป๊ะ"]
                values = [s['accuracy'] * 100, s['accuracy_from_score'] * 100, s['exact_score'] * 100]
                
                fig = go.Figure(data=[
                    go.Bar(
                        x=categories,
                        y=values,
                        text=[f"{v:.1f}%" for v in values],
                        textposition='auto',
                        marker_color=ui.accent(),
                        marker_line_color='rgba(0,0,0,0.1)',
                        marker_line_width=1,
                        opacity=0.9
                    )
                ])
                fig.update_layout(
                    yaxis=dict(
                        range=[0, 100], 
                        title="เปอร์เซ็นต์ความแม่นยำ (%)",
                        gridcolor='rgba(0, 0, 0, 0.25)',       # 👈 เพิ่ม: ให้เส้นตารางด้านหลังสีเข้มและชัดขึ้น
                        zerolinecolor='rgba(0, 0, 0, 0.4)',    # 👈 เพิ่ม: ให้เส้นฐานที่ 0 เข้มขึ้น
                        tickfont=dict(color='black', size=12), # 👈 เพิ่ม: เปลี่ยนตัวเลขแกน Y เป็นสีดำ
                        title_font=dict(color='black', size=13) # 👈 เพิ่ม: เปลี่ยนชื่อแกน Y เป็นสีดำ
                    ),
                    xaxis=dict(
                        title="",
                        tickfont=dict(color='black', size=13)  # 👈 เพิ่ม: เปลี่ยนตัวอักษรแกน X เป็นสีดำ
                    ),
                    margin=dict(l=20, r=20, t=30, b=20),
                    height=350,
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)'
                )
                st.plotly_chart(fig, width="stretch")

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
            placeholder = st.empty()
            placeholder.markdown(ui.spinning_ball_loader("กำลังจูนพารามิเตอร์ Random Forest..."), unsafe_allow_html=True)
            st.session_state[tkey] = cached_tuning(played, features)
            placeholder.empty()
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
    st.markdown(ui.model_info_html(), unsafe_allow_html=True)