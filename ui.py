"""หน้าตาของแอป: CSS ธีมมืด, ไอคอน SVG (ชุดเส้นแบบ Lucide) และตัวสร้าง HTML ของการ์ดต่าง ๆ

ไฟล์นี้ไม่ import streamlit (ทดสอบ/พรีวิวนอกเว็บได้) app.py เป็นคนเรียก st.markdown(..., unsafe_allow_html=True)
กติกา: HTML ทุกชิ้นต้องเป็นบรรทัดเดียว ไม่มีบรรทัดว่าง/ย่อหน้า ไม่งั้น markdown จะตีความเป็นโค้ดบล็อก
ข้อมูลจากภายนอก (ชื่อทีม, URL ตราสโมสร) ผ่าน html.escape ทุกครั้ง
"""
import hashlib
import html
import os
import re

import pandas as pd

# ---------------------------------------------------------------- ไอคอน (เส้น 24x24)
_ICON_PATHS = {
    "calendar": '<rect width="18" height="18" x="3" y="4" rx="2"/><path d="M16 2v4"/><path d="M8 2v4"/><path d="M3 10h18"/>',
    "clock": '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
    "check": '<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>',
    "x": '<circle cx="12" cy="12" r="10"/><path d="m15 9-6 6"/><path d="m9 9 6 6"/>',
    "target": '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
    "alert": '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
    "pause": '<rect x="14" y="4" width="4" height="16" rx="1"/><rect x="6" y="4" width="4" height="16" rx="1"/>',
    "chart": '<path d="M3 3v16a2 2 0 0 0 2 2h16"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/>',
    "trophy": '<path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/><path d="M4 22h16"/><path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"/><path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"/><path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"/>',
    "cpu": '<rect width="16" height="16" x="4" y="4" rx="2"/><rect width="6" height="6" x="9" y="9"/><path d="M15 2v2"/><path d="M15 20v2"/><path d="M2 15h2"/><path d="M2 9h2"/><path d="M20 15h2"/><path d="M20 9h2"/><path d="M9 2v2"/><path d="M9 20v2"/>',
    "zap": '<path d="M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z"/>',
    "ball": '<circle cx="12" cy="12" r="10"/><path d="m12 8 3.8 2.8-1.45 4.45h-4.7L8.2 10.8z"/><path d="M12 2v6"/><path d="m21.5 9.5-5.7 1.3"/><path d="m18 20-3.65-4.75"/><path d="M6 20l3.65-4.75"/><path d="m2.5 9.5 5.7 1.3"/>',
    "inbox": '<path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/>',
}


def icon(name, size=18, cls="fb-ic"):
    return (f'<svg class="{cls}" xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" '
            f'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
            f'aria-hidden="true">{_ICON_PATHS[name]}</svg>')


# ---------------------------------------------------------------- CSS
_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Prompt:wght@400;500;600;700&display=swap');
html,body,.stApp,.stApp p,.stApp label,.stApp button,.stApp input,.stApp textarea,.stApp h1,.stApp h2,.stApp h3,.stApp h4,.stApp td,.stApp th,
[data-testid="stMetricValue"],[data-testid="stMetricLabel"],[data-testid="stCaptionContainer"]{font-family:var(--font)}
.stApp{background:radial-gradient(900px 480px at 92% -10%,var(--glow1),transparent 62%),radial-gradient(700px 420px at -8% 0%,var(--glow2),transparent 58%),var(--bg);color:var(--tx)}
[data-testid="stHeader"]{background:transparent}
.block-container{padding:1.1rem 1.2rem 6.5rem;max-width:1160px}
.fb-ic{flex:none;vertical-align:middle}
/* app bar */
.fb-bar{display:flex;align-items:center;gap:.8rem;margin:.1rem 0 .9rem}
.fb-logo{width:44px;height:44px;border-radius:14px;display:grid;place-items:center;color:var(--logo-tx);background:var(--logo-bg);box-shadow:var(--shadow)}
.fb-ttl{font-weight:700;font-size:1.25rem;line-height:1.1;letter-spacing:-.01em;color:var(--tx)}
.fb-sub{color:var(--mut);font-size:.8rem;margin-top:.15rem}
/* pills (st.radio แนวนอน) */
div[role="radiogroup"]{gap:.5rem;flex-wrap:wrap}
div[role="radiogroup"]>label{background:var(--card);border:1px solid var(--line);border-radius:999px;padding:.3rem .95rem;cursor:pointer;margin:0;box-shadow:var(--shadow)}
div[role="radiogroup"]>label>div:first-child{display:none}
div[role="radiogroup"]>label p{font-weight:500;font-size:.88rem;margin:0;color:var(--mut)}
div[role="radiogroup"]>label:has(input:checked){background:var(--sel-bg);border-color:var(--sel-bg)}
div[role="radiogroup"]>label:has(input:checked) p{color:var(--sel-tx);font-weight:600}
/* tabs */
.stTabs [data-baseweb="tab-list"]{gap:.25rem;background:var(--card);padding:.3rem;border-radius:16px;border:1px solid var(--line);box-shadow:var(--shadow)}
.stTabs [data-baseweb="tab"]{height:auto;padding:.5rem 1.1rem;border-radius:12px;background:transparent;white-space:nowrap}
.stTabs [data-baseweb="tab"] p{color:var(--mut);font-weight:500}
.stTabs [data-baseweb="tab"][aria-selected="true"]{background:var(--tabsel-bg)}
.stTabs [data-baseweb="tab"][aria-selected="true"] p{color:var(--tabsel-tx);font-weight:600}
.stTabs [data-baseweb="tab-highlight"],.stTabs [data-baseweb="tab-border"]{display:none}
.stTabs [data-baseweb="tab-panel"]{padding-top:1rem}
/* widgets */
.stButton>button,.stDownloadButton>button{border-radius:12px;border:1px solid var(--line);background:var(--card);color:var(--tx);font-weight:500;box-shadow:var(--shadow)}
.stButton>button:hover,.stDownloadButton>button:hover{border-color:var(--acc);color:var(--tx)}
.stButton>button[kind="primary"]{background:var(--btn-bg);border-color:var(--btn-bg);color:var(--btn-tx)}
[data-baseweb="select"]>div{background:var(--card);border-radius:12px;border:1px solid var(--line)}
[data-testid="stExpander"]{border:1px solid var(--line);border-radius:16px;background:var(--card);box-shadow:var(--shadow)}
[data-testid="stMetric"]{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:.85rem 1rem;box-shadow:var(--shadow)}
[data-testid="stMetricValue"]{font-weight:700}
[data-testid="stDataFrame"]{border-radius:14px;overflow:hidden}
/* section / empty */
.fb-sec{display:flex;align-items:center;gap:.55rem;margin:1.5rem 0 .8rem;font-size:1.05rem;font-weight:600;color:var(--tx)}
.fb-sec .fb-ic{color:var(--acc)}
.fb-sec .fb-aside{margin-left:auto;color:var(--mut);font-size:.8rem;font-weight:400}
.fb-note{color:var(--mut);font-size:.8rem;margin:.4rem 0 .9rem}
.fb-empty{padding:2rem 1rem;text-align:center;color:var(--mut);border:1px dashed var(--line);border-radius:16px}
.fb-empty .fb-ic{display:block;margin:0 auto .6rem}
/* ตราสโมสร */
.fb-bdg{width:34px;height:34px;border-radius:50%;flex:none;display:grid;place-items:center;font-size:.7rem;font-weight:700;overflow:hidden;letter-spacing:.2px;
background:hsl(var(--h,200) var(--bdg-s) var(--bdg-l));color:var(--bdg-tx)}
.fb-bdg.has{background:#fff;border:1px solid var(--line)}
.fb-bdg img{width:78%;height:78%;object-fit:contain}
.fb-bdg.lg{width:54px;height:54px;font-size:.95rem}
.fb-bdg.sm{width:26px;height:26px;font-size:.6rem}
/* แถบความน่าจะเป็น */
.fb-pbar{display:flex;gap:2px;height:8px;border-radius:99px;overflow:hidden;background:var(--track)}
.fb-pbar i{display:block;height:100%}
.fb-pbar .h{background:var(--c-home)}.fb-pbar .d{background:var(--c-draw)}.fb-pbar .a{background:var(--c-away)}
.fb-plab{display:grid;grid-template-columns:1fr 1fr 1fr;font-size:.78rem;color:var(--mut);margin-top:.45rem}
.fb-plab span:nth-child(2){text-align:center}.fb-plab span:nth-child(3){text-align:right}
.fb-plab .on{color:var(--tx);font-weight:600}
/* hero */
.fb-hero{position:relative;overflow:hidden;border-radius:24px;padding:1.4rem;display:grid;grid-template-columns:1.2fr .8fr;gap:1.3rem;align-items:center;
background:var(--hero-bg);color:var(--hero-tx);border:1px solid var(--hero-line);box-shadow:var(--shadow-hero)}
.fb-hero:before{content:"";position:absolute;right:-70px;top:-70px;width:340px;height:340px;border-radius:50%;background:radial-gradient(circle,var(--hero-glow),transparent 65%)}
.fb-hero>*{position:relative}
.fb-hero .fb-pbar{background:var(--hero-chip)}
.fb-hero .fb-pbar .h{background:var(--h-home)}.fb-hero .fb-pbar .d{background:var(--h-draw)}.fb-hero .fb-pbar .a{background:var(--h-away)}
.fb-hero .fb-plab{color:var(--hero-mut)}.fb-hero .fb-plab .on{color:var(--hero-tx)}
.fb-tags{display:flex;flex-wrap:wrap;gap:.45rem}
.fb-tag{display:inline-flex;align-items:center;gap:.4rem;background:var(--hero-chip);border-radius:999px;padding:.28rem .75rem;font-size:.78rem;font-weight:500}
.fb-tag.hot{background:var(--tag-bg);color:var(--tag-tx)}
.fb-vs{display:flex;flex-direction:column;gap:.75rem;margin:1rem 0 .2rem}
.fb-vsrow{display:flex;align-items:center;gap:.85rem}
.fb-vsrow .nm{font-size:1.5rem;font-weight:700;line-height:1.1;flex:1;min-width:0}
.fb-vsrow .sc{font-size:1.8rem;font-weight:700;background:var(--hero-chip);border-radius:12px;min-width:2.7rem;text-align:center;padding:.05rem .5rem;font-variant-numeric:tabular-nums}
.fb-panel{background:var(--panel-bg);border:1px solid var(--hero-line);border-radius:18px;padding:1rem 1.1rem}
.fb-panel .k{color:var(--hero-mut);font-size:.76rem;margin-bottom:.25rem}
.fb-panel .big{font-size:1.35rem;font-weight:700;line-height:1.2;margin-bottom:.8rem}
.fb-panel .big b{color:var(--hero-pop)}
.fb-panel .xg{display:flex;justify-content:space-between;margin-top:.8rem;padding-top:.7rem;border-top:1px solid var(--hero-line);font-size:.8rem;color:var(--hero-mut)}
.fb-panel .xg b{color:var(--hero-tx);font-weight:600}
/* การ์ดแมตช์ */
.fb-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:.9rem}
.fb-mc{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:1rem;box-shadow:var(--shadow)}
.fb-mc-top{display:flex;justify-content:space-between;align-items:center;margin-bottom:.7rem;gap:.5rem}
.fb-chip{display:inline-flex;align-items:center;gap:.35rem;color:var(--mut);font-size:.78rem}
.fb-tm{display:flex;align-items:center;gap:.65rem;padding:.28rem 0}
.fb-tm .nm{flex:1;min-width:0;font-weight:500;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--tx)}
.fb-tm .sc{min-width:1.9rem;text-align:center;background:var(--chip);border-radius:8px;font-weight:600;padding:.08rem .4rem;color:var(--tx)}
.fb-mc .fb-pbar{margin-top:.7rem}
.fb-mc-foot{display:flex;justify-content:space-between;gap:.5rem;margin-top:.75rem;padding-top:.65rem;border-top:1px solid var(--line);font-size:.78rem;color:var(--mut)}
.fb-mc-foot b{color:var(--tx);font-weight:600}
.fb-live{display:inline-flex;align-items:center;gap:.4rem;color:var(--bad);font-size:.76rem;font-weight:600}
.fb-dot{width:8px;height:8px;border-radius:50%;background:var(--bad);animation:fbp 1.4s infinite}
@keyframes fbp{0%,100%{opacity:1}50%{opacity:.3}}
/* ไทล์สรุป + แถบสถิติ */
.fb-tiles{display:grid;grid-template-columns:repeat(3,1fr);gap:.8rem}
.fb-tile{border-radius:16px;overflow:hidden;text-align:center;background:var(--card);border:1px solid var(--line);box-shadow:var(--shadow);display:flex;flex-direction:column}
.fb-tile .v{flex:1;font-size:2rem;font-weight:700;padding:1rem .4rem .6rem;line-height:1.1;color:var(--tx);font-variant-numeric:tabular-nums}
.fb-tile .v small{font-size:.95rem;color:var(--mut);font-weight:500}
.fb-tile .l{padding:.45rem .3rem;font-size:.8rem;font-weight:600;color:var(--tx);border-top:2px solid var(--warn);background:color-mix(in srgb,var(--warn) 16%,transparent)}
.fb-tile .l.lime{border-top-color:var(--good);background:color-mix(in srgb,var(--good) 16%,transparent)}
.fb-tile .l.blue{border-top-color:var(--info);background:color-mix(in srgb,var(--info) 16%,transparent)}
.fb-bars{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:1rem 1.1rem;display:grid;gap:.95rem;box-shadow:var(--shadow)}
.fb-ab-h{display:flex;justify-content:space-between;align-items:baseline;font-size:.88rem;margin-bottom:.35rem;color:var(--tx)}
.fb-ab-h small{color:var(--mut);font-size:.74rem;margin-left:.4rem}
.fb-ab-h b{font-weight:700}
.fb-ab-t{height:6px;border-radius:99px;background:var(--track);overflow:hidden}
.fb-ab-t i{display:block;height:100%;border-radius:99px}
.c-lime{color:var(--good)}.c-amber{color:var(--warn)}.c-red{color:var(--bad)}
i.c-lime{background:var(--good)}i.c-amber{background:var(--warn)}i.c-red{background:var(--bad)}
/* แถวผลการแข่งขัน */
.fb-rr{display:grid;grid-template-columns:84px 1fr auto;gap:.85rem;align-items:center;padding:.8rem 1rem;background:var(--card);border:1px solid var(--line);border-left:3px solid var(--bad);border-radius:14px;margin-bottom:.55rem;box-shadow:var(--shadow)}
.fb-rr.ok{border-left-color:var(--good)}
.fb-rr-d{font-size:.78rem;color:var(--mut);line-height:1.35;white-space:nowrap}
.fb-rr-d b{display:block;color:var(--tx);font-weight:600;font-size:.84rem}
.fb-rr-l{display:flex;align-items:center;gap:.55rem;color:var(--tx)}
.fb-rr-l .t{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:500}
.fb-rr-l .t.r{text-align:right}
.fb-rr-l .s{font-weight:700;font-size:1.05rem;min-width:3.6rem;text-align:center;background:var(--chip);border-radius:9px;padding:.08rem .45rem;white-space:nowrap;font-variant-numeric:tabular-nums}
.fb-rr-ai{margin-top:.4rem;font-size:.76rem;color:var(--mut);text-align:center}
.fb-rr-ai b{color:var(--tx);font-weight:600}
.fb-st{display:flex;flex-direction:column;align-items:center;gap:.25rem;font-size:.72rem;font-weight:600;white-space:nowrap;min-width:56px}
.fb-rr.ok .fb-st .res{color:var(--good)}.fb-rr .fb-st .res{color:var(--bad)}
.fb-st .ex{color:var(--info)}
.fb-st .res,.fb-st .ex{display:flex;align-items:center;gap:.3rem}
@media(max-width:720px){
.block-container{padding:.8rem .8rem 6.5rem}
.fb-hero{grid-template-columns:1fr;padding:1.1rem}
.fb-vsrow .nm{font-size:1.2rem}
.fb-tile .v{font-size:1.55rem}
.fb-rr{grid-template-columns:1fr auto;grid-template-areas:"d st" "m m";gap:.55rem .6rem;padding:.7rem .8rem}
.fb-rr-d{grid-area:d}.fb-rr-d b{display:inline;margin-right:.45rem}
.fb-rr-m{grid-area:m}
.fb-st{grid-area:st;flex-direction:row;gap:.7rem;min-width:0}
.fb-rr-l .s{min-width:3rem}
.fb-rr-l .fb-bdg{display:none}
.fb-rr-l .t{white-space:normal;overflow:visible;text-overflow:clip;line-height:1.2;font-size:.9rem}
.fb-tile .l{min-height:2.7em;display:grid;place-items:center}
}
@media(max-width:640px){
/* แถบแท็บลอยด้านล่างเหมือนแอปมือถือ */
.stTabs [data-baseweb="tab-list"]{position:fixed;left:10px;right:10px;bottom:10px;z-index:999;justify-content:space-around;
background:var(--nav-bg);backdrop-filter:blur(14px);box-shadow:var(--nav-shadow);border-radius:20px}
.stTabs [data-baseweb="tab"]{padding:.5rem .55rem;font-size:.74rem}
.stTabs [data-baseweb="tab"] p{font-size:.74rem}
}
"""

# ---------------------------------------------------------------- ธีม
# เปลี่ยนธีมด้วย:  python set_theme.py cream   (เขียน theme.txt + .streamlit/config.toml ให้ตรงกัน)
# ตัวแปรสี: bg/glow = พื้นหลัง • card/line/tx/mut = การ์ด เส้น ตัวหนังสือ • c_* = แถบเหย้า/เสมอ/เยือน
# good/bad/warn/info = สีบอกความหมาย • hero_* / h_* = การ์ดเด่น • bdg_* = ตัวย่อทีมในวงกลม • cfg = ค่า [theme] ของ Streamlit
THEMES = {
    # ครีมอุ่น: พื้นกระดาษครีม + เขียวป่าหม่น + ส้มดินเผา การ์ดเด่นเป็นเขียวเข้มตัดกับพื้นครีม
    "cream": dict(
        bg="#f4efe4", glow1="rgba(217,160,110,.20)", glow2="rgba(160,190,160,.18)", card="#fffdf8", line="rgba(70,55,35,.11)",
        tx="#2a2823", mut="#7a7365", track="rgba(70,55,35,.09)", chip="rgba(70,55,35,.07)",
        c_home="#2f5d50", c_draw="#d4cab6", c_away="#d9895c", good="#3d7a58", bad="#c1504a", warn="#c48a28", info="#4d6fa3",
        acc="#2f5d50", logo_bg="#2f5d50", logo_tx="#f4efe4", btn_bg="#2f5d50", btn_tx="#fffdf8", sel_bg="#2f5d50", sel_tx="#fffdf8",
        tabsel_bg="rgba(47,93,80,.12)", tabsel_tx="#2f5d50",
        hero_bg="linear-gradient(145deg,#2d5a4c,#1f4237)", hero_tx="#f7f2e6", hero_mut="rgba(247,242,230,.66)",
        hero_line="rgba(255,255,255,.12)", hero_chip="rgba(255,255,255,.12)", panel_bg="rgba(0,0,0,.2)", hero_pop="#f1d79c",
        hero_glow="rgba(240,190,120,.22)", tag_bg="rgba(241,215,156,.18)", tag_tx="#f1d79c",
        h_home="#a8dcc0", h_draw="rgba(255,255,255,.3)", h_away="#eaa97f",
        nav_bg="rgba(255,253,248,.94)", shadow="0 1px 2px rgba(70,55,35,.06),0 8px 22px rgba(70,55,35,.07)",
        shadow_hero="0 14px 34px rgba(31,66,55,.28)", nav_shadow="0 8px 30px rgba(70,55,35,.2)",
        bdg_s="30%", bdg_l="86%", bdg_tx="#3b362b",
        cfg=dict(base="light", primaryColor="#2f5d50", backgroundColor="#f4efe4", secondaryBackgroundColor="#fffdf8", textColor="#2a2823")),
    # สเลตมืดแบบมินิมอล: แบน ไม่มีแสงเรือง สีเดียวคือเขียวเซจ
    "slate": dict(
        bg="#101214", glow1="transparent", glow2="transparent", card="#171a1d", line="rgba(255,255,255,.07)",
        tx="#e7e9eb", mut="#8b9298", track="rgba(255,255,255,.07)", chip="rgba(255,255,255,.06)",
        c_home="#8fb8a6", c_draw="#454c53", c_away="#c8a27c", good="#86b894", bad="#d27a70", warn="#c8a27c", info="#86a6c8",
        acc="#8fb8a6", logo_bg="#8fb8a6", logo_tx="#101214", btn_bg="#8fb8a6", btn_tx="#101a16", sel_bg="#8fb8a6", sel_tx="#101a16",
        tabsel_bg="rgba(143,184,166,.14)", tabsel_tx="#b5d6c7",
        hero_bg="#1a1e22", hero_tx="#eceef0", hero_mut="#8b9298", hero_line="rgba(255,255,255,.08)", hero_chip="rgba(255,255,255,.07)",
        panel_bg="#121518", hero_pop="#8fb8a6", hero_glow="transparent", tag_bg="rgba(143,184,166,.14)", tag_tx="#9cc7b4",
        h_home="#8fb8a6", h_draw="#454c53", h_away="#c8a27c",
        nav_bg="rgba(23,26,29,.94)", shadow="none", shadow_hero="none", nav_shadow="0 8px 30px rgba(0,0,0,.5)",
        bdg_s="10%", bdg_l="24%", bdg_tx="#cfd4d8",
        cfg=dict(base="dark", primaryColor="#8fb8a6", backgroundColor="#101214", secondaryBackgroundColor="#171a1d", textColor="#e7e9eb")),
    # คอนทราสต์: พื้นเทาฟ้าอ่อน + กรมท่าเข้ม + ส้มปะการัง
    "contrast": dict(
        bg="#edf0f5", glow1="rgba(255,122,89,.10)", glow2="rgba(74,99,216,.08)", card="#ffffff", line="rgba(16,26,58,.09)",
        tx="#111a3a", mut="#6a7391", track="rgba(16,26,58,.08)", chip="rgba(16,26,58,.06)",
        c_home="#3f5bd8", c_draw="#cdd3e1", c_away="#ff7a59", good="#2a9d6f", bad="#e0524d", warn="#e2992f", info="#3f5bd8",
        acc="#ff6a47", logo_bg="#111a3a", logo_tx="#ffffff", btn_bg="#111a3a", btn_tx="#ffffff", sel_bg="#111a3a", sel_tx="#ffffff",
        tabsel_bg="#111a3a", tabsel_tx="#ffffff",
        hero_bg="linear-gradient(145deg,#141f4a,#0c1330)", hero_tx="#ffffff", hero_mut="rgba(255,255,255,.62)",
        hero_line="rgba(255,255,255,.1)", hero_chip="rgba(255,255,255,.1)", panel_bg="rgba(255,255,255,.06)", hero_pop="#ff9a7e",
        hero_glow="rgba(255,106,71,.25)", tag_bg="rgba(255,122,89,.2)", tag_tx="#ffa890",
        h_home="#8ea2ff", h_draw="rgba(255,255,255,.28)", h_away="#ff9a7e",
        nav_bg="rgba(255,255,255,.94)", shadow="0 1px 2px rgba(16,26,58,.05),0 10px 28px rgba(16,26,58,.07)",
        shadow_hero="0 16px 38px rgba(12,19,48,.35)", nav_shadow="0 8px 30px rgba(16,26,58,.22)",
        bdg_s="45%", bdg_l="91%", bdg_tx="#1b2557",
        cfg=dict(base="light", primaryColor="#ff6a47", backgroundColor="#edf0f5", secondaryBackgroundColor="#ffffff", textColor="#111a3a")),
}
DEFAULT_THEME = "cream"
_FONT = "'Prompt','Noto Sans Thai','Sarabun',system-ui,-apple-system,'Segoe UI',sans-serif"


def _read_theme():
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "theme.txt"), encoding="utf-8") as f:
            name = f.read().strip()
        if name in THEMES:
            return name
    except OSError:
        pass
    return DEFAULT_THEME


THEME = _read_theme()


def accent(theme=None):
    return THEMES[theme or THEME]["acc"]


def config_toml(theme=None):
    c = THEMES[theme or THEME]["cfg"]
    return "[theme]\n" + "".join(f'{k} = "{v}"\n' for k, v in c.items()) + 'font = "sans serif"\n'


def css(theme=None):
    t = THEMES[theme or THEME]
    vars_ = "".join(f"--{k.replace('_', '-')}:{v};" for k, v in t.items() if k != "cfg")
    body = re.sub(r"\s+", " ", _CSS).replace("{ ", "{").replace(" }", "}")
    return f"<style>:root{{{vars_}--font:{_FONT};}}{body}</style>"


CSS = css()


# ---------------------------------------------------------------- ตัวช่วย
_e = html.escape
_TH_DAY = ["จ.", "อ.", "พ.", "พฤ.", "ศ.", "ส.", "อา."]
_TH_MON = ["ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]
_SKIP = {"fc", "afc", "&", "and", "of", "the", "1.", "cf", "sc"}


def when_text(ts_utc):
    """(วันที่แบบไทยสั้น, เวลา) จากเวลา UTC แบบ naive -> เวลาไทย"""
    t = pd.Timestamp(ts_utc) + pd.Timedelta(hours=7)
    return f"{_TH_DAY[t.weekday()]} {t.day} {_TH_MON[t.month - 1]}", f"{t:%H:%M} น."


def _initials(name):
    words = [w for w in re.split(r"[\s.]+", str(name)) if w and w.lower() not in _SKIP]
    if not words:
        return "?"
    return (words[0][:3] if len(words) == 1 else "".join(w[0] for w in words[:3])).upper()


def badge(name, crest=None, size=""):
    cls = f"fb-bdg {size}".strip()
    if crest and str(crest).startswith("https://"):
        return f'<span class="{cls} has"><img src="{_e(str(crest), quote=True)}" alt="" loading="lazy"></span>'
    hue = int(hashlib.md5(str(name).encode("utf-8")).hexdigest()[:4], 16) % 360
    return f'<span class="{cls}" style="--h:{hue}">{_e(_initials(name))}</span>'


def crest_map(df):
    """ชื่อทีม -> URL ตราสโมสร จากตารางโปรแกรม (ทุกทีมในลีกต้องมีนัดในโปรแกรมอยู่แล้ว)"""
    out = {}
    if df is None or len(df) == 0:
        return out
    for h, a, hc, ac in zip(df["ทีมเหย้า"], df["ทีมเยือน"], df.get("_home_crest", [None] * len(df)), df.get("_away_crest", [None] * len(df))):
        if isinstance(hc, str) and hc:
            out[h] = hc
        if isinstance(ac, str) and ac:
            out[a] = ac
    return out


def _outcome(p):
    """(ดัชนีผลที่ความน่าจะเป็นสูงสุด, ความน่าจะเป็นนั้น) p = (เหย้า, เสมอ, เยือน) หน่วย %"""
    i = max(range(3), key=lambda k: p[k])
    return i, p[i]


def verdict(p, home, away):
    i, v = _outcome(p)
    return [f"{home} ชนะ", "เสมอ", f"{away} ชนะ"][i], v


def prob_bar(p, labeled=True):
    ph, pd_, pa = p
    i, _ = _outcome(p)
    bar = (f'<div class="fb-pbar"><i class="h" style="width:{ph:.1f}%"></i><i class="d" style="width:{pd_:.1f}%"></i>'
           f'<i class="a" style="width:{pa:.1f}%"></i></div>')
    if not labeled:
        return bar
    on = ["on" if k == i else "" for k in range(3)]
    return bar + (f'<div class="fb-plab"><span class="{on[0]}">เหย้า {ph:.1f}%</span>'
                  f'<span class="{on[1]}">เสมอ {pd_:.1f}%</span><span class="{on[2]}">เยือน {pa:.1f}%</span></div>')


def _status_chip(status):
    if status == "IN_PLAY":
        return '<span class="fb-live"><span class="fb-dot"></span>กำลังแข่ง</span>'
    if status == "PAUSED":
        return f'<span class="fb-live">{icon("pause", 14)}พักครึ่ง</span>'
    return ""


def _score_parts(score):
    a, b = str(score).split(" - ")
    return a, b


# ---------------------------------------------------------------- ส่วนประกอบหลัก
def app_bar(subtitle):
    return (f'<div class="fb-bar"><div class="fb-logo">{icon("ball", 24)}</div>'
            f'<div><div class="fb-ttl">AI Football Predictor</div><div class="fb-sub">{_e(subtitle)}</div></div></div>')


def section(icon_name, title, aside=""):
    side = f'<span class="fb-aside">{_e(aside)}</span>' if aside else ""
    return f'<div class="fb-sec">{icon(icon_name, 20)}<span>{_e(title)}</span>{side}</div>'


def note(text):
    return f'<div class="fb-note">{_e(text)}</div>'


def empty(icon_name, text):
    return f'<div class="fb-empty">{icon(icon_name, 28)}{_e(text)}</div>'


def hero(m, tag="แมตช์ถัดไป"):
    """m: dict(home, away, home_crest, away_crest, kickoff, status, p=(%,%,%), score, xg=(h,a))"""
    sh, sa = _score_parts(m["score"])
    v, pct = verdict(m["p"], m["home"], m["away"])
    tags = f'<span class="fb-tag hot">{icon("zap", 14)}{_e(tag)}</span>'
    if m.get("kickoff") is not None and not pd.isna(m["kickoff"]):
        d, t = when_text(m["kickoff"])
        tags += f'<span class="fb-tag">{icon("calendar", 14)}{d}</span><span class="fb-tag">{icon("clock", 14)}{t}</span>'
    tags += _status_chip(m.get("status"))
    row = lambda n, c, s: (f'<div class="fb-vsrow">{badge(n, c, "lg")}<div class="nm">{_e(n)}</div><div class="sc">{s}</div></div>')
    return (f'<div class="fb-hero"><div><div class="fb-tags">{tags}</div>'
            f'<div class="fb-vs">{row(m["home"], m.get("home_crest"), sh)}{row(m["away"], m.get("away_crest"), sa)}</div></div>'
            f'<div class="fb-panel"><div class="k">AI เชื่อว่า</div><div class="big">{_e(v)} <b>{pct:.1f}%</b></div>'
            f'{prob_bar(m["p"])}'
            f'<div class="xg"><span>ประตูคาดหวัง (xG)</span><span><b>{m["xg"][0]:.2f}</b> - <b>{m["xg"][1]:.2f}</b></span></div></div></div>')


def match_card(m):
    sh, sa = _score_parts(m["score"])
    v, pct = verdict(m["p"], m["home"], m["away"])
    d, t = when_text(m["kickoff"])
    top = f'<span class="fb-chip">{icon("calendar", 14)}{d}</span><span class="fb-chip">{icon("clock", 14)}{t}</span>'
    top = f'<div style="display:flex;gap:.8rem">{top}</div>{_status_chip(m.get("status"))}'
    tm = lambda n, c, s: f'<div class="fb-tm">{badge(n, c)}<span class="nm">{_e(n)}</span><span class="sc">{s}</span></div>'
    return (f'<div class="fb-mc"><div class="fb-mc-top">{top}</div>{tm(m["home"], m.get("home_crest"), sh)}{tm(m["away"], m.get("away_crest"), sa)}'
            f'{prob_bar(m["p"])}'
            f'<div class="fb-mc-foot"><span>AI เชื่อ <b>{_e(v)}</b></span><span>xG <b>{m["xg"][0]:.1f}</b> - <b>{m["xg"][1]:.1f}</b></span></div></div>')


def match_grid(items):
    return '<div class="fb-grid">' + "".join(match_card(m) for m in items) + "</div>"


def tile(value, small, label, tone="amber"):
    return f'<div class="fb-tile"><div class="v">{value}<small>{small}</small></div><div class="l {tone}">{_e(label)}</div></div>'


def tiles(*items):
    return '<div class="fb-tiles">' + "".join(items) + "</div>"


def bar_tone(pct):
    return "c-lime" if pct >= 55 else ("c-amber" if pct >= 40 else "c-red")


def bars(rows):
    """rows: [(ชื่อ, เปอร์เซ็นต์, หมายเหตุ)] แถบสีตามค่า (เขียว >= 55, ส้ม >= 40, แดง ต่ำกว่านั้น)"""
    out = []
    for label, pct, sub in rows:
        tone = bar_tone(pct)
        out.append(f'<div><div class="fb-ab-h"><span>{_e(label)}<small>{_e(sub)}</small></span><b class="{tone}">{pct:.0f}%</b></div>'
                   f'<div class="fb-ab-t"><i class="{tone}" style="width:{max(0, min(100, pct)):.0f}%"></i></div></div>')
    return '<div class="fb-bars">' + "".join(out) + "</div>"


def result_row(r):
    """r: dict(kickoff, home, away, home_crest, away_crest, real, pred, p, right, exact, new_team)"""
    d, t = when_text(r["kickoff"])
    v, _ = verdict(r["p"], r["home"], r["away"])
    res = (f'<span class="res">{icon("check", 18)}<span>ทายถูก</span></span>' if r["right"]
           else f'<span class="res">{icon("x", 18)}<span>พลาด</span></span>')
    ex = f'<span class="ex">{icon("target", 16)}<span>ตรงสกอร์</span></span>' if r["exact"] else ""
    warn = f'<span class="ex" style="color:var(--warn)">{icon("alert", 16)}<span>ทีมใหม่</span></span>' if r.get("new_team") else ""
    p = r["p"]
    return (f'<div class="fb-rr {"ok" if r["right"] else "miss"}"><div class="fb-rr-d"><b>{d}</b>{t}</div>'
            f'<div class="fb-rr-m"><div class="fb-rr-l"><span class="t r">{_e(r["home"])}</span>{badge(r["home"], r.get("home_crest"), "sm")}'
            f'<span class="s">{_e(r["real"])}</span>{badge(r["away"], r.get("away_crest"), "sm")}<span class="t">{_e(r["away"])}</span></div>'
            f'<div class="fb-rr-ai">AI ทาย <b>{_e(r["pred"])}</b> · เชื่อ <b>{_e(v)}</b> ({p[0]:.0f} / {p[1]:.0f} / {p[2]:.0f}%)</div></div>'
            f'<div class="fb-st">{res}{ex}{warn}</div></div>')