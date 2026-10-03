import pandas as pd
import streamlit as st

from data_fetcher import (
    LEAGUES,
    DataError,
    get_historical_data,
    get_recent_finished_matches,
    get_upcoming_fixtures,
)
from predictor import predict_match, train_model

st.set_page_config(page_title="AI Football Predictor", page_icon="⚽", layout="wide")

st.title("⚽ AI Football Predictor")
st.caption("ระบบทำนายผลฟุตบอล 3 ลีกใหญ่ (สถิติอัปเดตวันละ 1 ครั้ง / โปรแกรมและผลล่าสุดอัปเดตทุกชั่วโมง)")


def outcome(h, a):
    return "H" if h > a else ("A" if h < a else "D")


league_choice = st.selectbox("เลือกลีกฟุตบอล", list(LEAGUES.keys()))

# ---- โหลดสถิติย้อนหลัง + เทรนโมเดลสำหรับใช้งานจริง ----
try:
    with st.spinner("กำลังโหลดสถิติย้อนหลัง..."):
        hist_df = get_historical_data(league_choice)
except DataError as e:
    st.error(f"ไม่สามารถโหลดสถิติย้อนหลังของลีกนี้ได้: {e}")
    st.stop()

model = train_model(hist_df)

tab1, tab2 = st.tabs(["📊 ตรวจสอบผลย้อนหลัง 5 นัด (Backtest)", "📅 โปรแกรมล่วงหน้า & ทำนายผล"])

# =========================== TAB 1: Backtest ===========================
with tab1:
    st.subheader(f"🔍 ผลการแข่งขันจริง vs ผลที่ AI ทำนาย ({league_choice})")

    try:
        recent_df = get_recent_finished_matches(league_choice)
    except DataError as e:
        st.error(f"ไม่สามารถดึงผลการแข่งขันล่าสุดได้: {e}")
        recent_df = pd.DataFrame()

    if recent_df.empty:
        st.info("ยังไม่มีข้อมูลผลการแข่งขันล่าสุด")
    else:
        # เทรนด้วยข้อมูลก่อนนัดเก่าสุดที่เอามาทดสอบ เพื่อไม่ให้โมเดล "เห็นเฉลย"
        cutoff = recent_df["match_date"].min().normalize()
        train_df = hist_df[hist_df["Date"] < cutoff]
        bt_model = train_model(train_df, ref_date=cutoff) if len(train_df) >= 30 else None

        if bt_model is None:
            st.info("ข้อมูลก่อนหน้านัดเหล่านี้ไม่พอสำหรับทดสอบย้อนหลัง")
        else:
            rows, unmatched = [], set()
            exact = correct = 0
            for _, r in recent_df.iterrows():
                p = predict_match(bt_model, r["ทีมเหย้า"], r["ทีมเยือน"])
                unmatched.update(p["missing"])
                pred_h, pred_a = map(int, p["score"].split(" - "))

                if r["ผลจริง"] == p["score"]:
                    status = "🎯 แม่นยำ (ตรงทั้งสกอร์)"
                    exact += 1
                    correct += 1
                elif outcome(r["real_home"], r["real_away"]) == outcome(pred_h, pred_a):
                    status = "✅ ถูกต้อง (ทายผลแพ้/ชนะถูก)"
                    correct += 1
                else:
                    status = "❌ พลาด"

                rows.append({
                    "วัน-เวลา (ไทย)": r["วัน-เวลา (ไทย)"],
                    "คู่แข่งขัน": f"{r['ทีมเหย้า']} vs {r['ทีมเยือน']}",
                    "ผลสกอร์จริง": r["ผลจริง"],
                    "AI ทำนายสกอร์": p["score"],
                    "ผลประเมิน": status,
                })

            n = len(rows)
            c1, c2 = st.columns(2)
            c1.metric("ทายผลแพ้/เสมอ/ชนะถูก", f"{correct}/{n}")
            c2.metric("ทายสกอร์ตรงเป๊ะ", f"{exact}/{n}")
            st.dataframe(pd.DataFrame(rows), width="stretch")
            st.caption("โมเดลถูกเทรนด้วยข้อมูลก่อนวันแข่งของนัดเหล่านี้เท่านั้น • ตัวอย่างแค่ 5 นัดจึงแกว่งได้มาก")

            if unmatched:
                st.warning(
                    "จับคู่ชื่อทีมกับสถิติไม่ได้ (ใช้ค่าเฉลี่ยลีกแทน): " + ", ".join(sorted(unmatched))
                    + " — เพิ่มชื่อใน NAME_MAP ของ team_names.py"
                )

# =========================== TAB 2: Upcoming + manual ===========================
with tab2:
    st.subheader(f"📅 โปรแกรม 5 นัดถัดไป ({league_choice})")

    try:
        upcoming_df = get_upcoming_fixtures(league_choice)
    except DataError as e:
        st.error(f"ไม่สามารถดึงโปรแกรมการแข่งขันได้: {e}")
        upcoming_df = pd.DataFrame()

    if upcoming_df.empty:
        st.info("ไม่มีข้อมูลโปรแกรมแข่งที่กำหนดเวลาไว้")
    else:
        shown, unmatched = upcoming_df.copy(), set()
        preds = []
        for _, r in shown.iterrows():
            p = predict_match(model, r["ทีมเหย้า"], r["ทีมเยือน"])
            unmatched.update(p["missing"])
            preds.append(p)
        shown["AI ทำนายสกอร์"] = [p["score"] for p in preds]
        shown["เหย้าชนะ %"] = [round(p["p_home"], 1) for p in preds]
        shown["เสมอ %"] = [round(p["p_draw"], 1) for p in preds]
        shown["เยือนชนะ %"] = [round(p["p_away"], 1) for p in preds]
        st.dataframe(shown, width="stretch")

        if unmatched:
            st.warning(
                "จับคู่ชื่อทีมกับสถิติไม่ได้ (ใช้ค่าเฉลี่ยลีกแทน): " + ", ".join(sorted(unmatched))
            )

    st.divider()
    st.subheader("🔮 จำลองทำนายผลสกอร์คู่อื่นๆ")

    teams = model["teams"]
    col1, col2 = st.columns(2)
    with col1:
        home_team = st.selectbox("ทีมเหย้า", teams, index=0)
    with col2:
        away_team = st.selectbox("ทีมเยือน", teams, index=min(1, len(teams) - 1))

    if st.button("ทำนายผลการแข่งขัน (Predict)", type="primary"):
        if home_team == away_team:
            st.warning("กรุณาเลือกทีมเหย้าและทีมเยือนไม่ให้เป็นทีมเดียวกัน")
        else:
            p = predict_match(model, home_team, away_team)
            st.success(f"### ผลที่คาด: **{home_team} {p['score']} {away_team}**")

            m1, m2, m3 = st.columns(3)
            m1.metric(f"{home_team} ชนะ", f"{p['p_home']:.1f}%")
            m2.metric("เสมอ", f"{p['p_draw']:.1f}%")
            m3.metric(f"{away_team} ชนะ", f"{p['p_away']:.1f}%")
            st.caption(f"ประตูที่คาดหวัง (xG): {home_team} {p['xg_home']:.2f} • {away_team} {p['xg_away']:.2f}")