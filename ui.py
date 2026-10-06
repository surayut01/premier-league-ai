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
    "cpu": '<rect width="16" height="16" x="4" y="4" rx="2"/><rect width="6" height="6" x="9" y="9"/><path d="M15 2v2"/><path d="M15 20v2"/><path d="M2 15h2"/><path d="M20 15h2"/><path d="M20 9h2"/><path d="M9 2v2"/><path d="M9 20v2"/>',
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
/* 🌟 เพิ่มแอนิเมชันลูกฟุตบอลหมุน */
@keyframes fb-spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}
.fb-spin-ball {
    display: inline-block;
    animation: fb-spin 3s linear infinite;
    font-size: 2.2rem;
}
.fb-loader-box {
    text-align: center;
    padding: 2.5rem 1rem;
    color: var(--mut);
    font-weight: 500;
}
@import url('https://fonts.googleapis.com/css2?family=Prompt:wght@400;500;600;700&display=swap');
html,body,.stApp,.stApp p,.stApp label,.stApp button,.stApp input,.stApp textarea,.stApp h1,.stApp h2,.stApp h3,.stApp h4,.stApp td,.stApp th,
[data-testid="stMetricValue"],[data-testid="stMetricLabel"],[data-testid="stCaptionContainer"]{font-family:var(--font)}
.stApp{background:radial-gradient(900px 480px at 92% -10%,var(--glow1),transparent 62%),radial-gradient(700px 420px at -8% 0%,var(--glow2),transparent 58%),var(--bg);color:var(--tx)}


/* 🌟 4. กิมมิก: แอนิเมชันหลอดเปอร์เซ็นต์วิ่งตอนโหลด (Animated Probability Bars) */
.fb-pbar i {
    display: block;
    height: 100%;
    animation: bar-grow 1.2s cubic-bezier(0.1, 0.9, 0.2, 1) forwards;
    transform-origin: left;
}
@keyframes bar-grow {
    0% { transform: scaleX(0); opacity: 0; }
    100% { transform: scaleX(1); opacity: 1; }
}

/* 🌟 5. กิมมิก: ป้ายเตือน Smart Match Tags (สูสี / มั่นใจมาก) */
.fb-tag-tight {
    display: inline-flex; align-items: center; gap: 0.25rem;
    background: linear-gradient(90deg, #f59e0b, #d97706);
    color: #fff;
    padding: 0.15rem 0.55rem;
    border-radius: 6px;
    font-size: 0.7rem;
    font-weight: 700;
    box-shadow: 0 2px 6px rgba(245, 158, 11, 0.3);
    letter-spacing: 0.2px;
    animation: pulse-tight 2s infinite;
}
@keyframes pulse-tight {
    0% { box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.4); }
    70% { box-shadow: 0 0 0 4px rgba(245, 158, 11, 0); }
    100% { box-shadow: 0 0 0 0 rgba(245, 158, 11, 0); }
}
.fb-tag-confident {
    display: inline-flex; align-items: center; gap: 0.25rem;
    background: linear-gradient(90deg, #10b981, #059669);
    color: #fff;
    padding: 0.15rem 0.55rem;
    border-radius: 6px;
    font-size: 0.7rem;
    font-weight: 700;
    box-shadow: 0 2px 6px rgba(16, 185, 129, 0.3);
    letter-spacing: 0.2px;
}

/* 🌟 3. กิมมิก: ลายน้ำลูกฟุตบอลยักษ์หมุนช้าๆ ที่พื้นหลัง */
.stApp::after {
    content: "⚽";
    position: fixed;
    font-size: max(70vw, 400px); /* เพิ่มขนาดให้ใหญ่ขึ้นอีก */ /* ใหญ่ขึ้นให้เห็นชัดเจน */
    bottom: -30vh;
    right: -22vw;
    opacity: 0.15; /* ⚠️ ปรับให้เข้มแบบเห็นชัดทะลุจอ (สว่างมาก) */
    z-index: 0;
    pointer-events: none; /* ทะลุได้ ไม่บังปุ่มกด */
    filter: grayscale(100%) contrast(200%) brightness(120%); /* เพิ่มความสว่างและคอนทราสต์จัดๆ */
    animation: bg-ball-float 40s ease-in-out infinite;
}
@media (max-width: 768px) {      /* 📱 ปรับเฉพาะสำหรับมือถือและแท็บเล็ต */
    .stApp::after {
        font-size: 110vw;        /* ใหญ่สะใจบนมือถือ */
        bottom: -5vh;            /* ให้อยู่กลางจอมากขึ้น */
        right: -25vw;
        opacity: 0.20;           /* เข้มขึ้นนิดหน่อยบนมือถือ */
    }
}
@keyframes bg-ball-float {
    0%, 100% { transform: translateY(0) rotate(-10deg); }
    50% { transform: translateY(-80px) rotate(20deg); }
}
.block-container {
    position: relative;
    z-index: 1; /* ดันเนื้อหาหลักให้อยู่เหนือลายน้ำ */
}

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

/* 🔥 บิ๊กแมตช์ไฮไลต์ (Big Match Glow) */
.fb-mc.big-match {
    border: 1px solid color-mix(in srgb, var(--warn) 50%, transparent);
    box-shadow: 0 8px 24px color-mix(in srgb, var(--warn) 15%, transparent);
    position: relative;
    overflow: hidden;
}
.fb-mc.big-match::after {
    content: "";
    position: absolute;
    top: 0; left: 0; right: 0; height: 4px;
    background: linear-gradient(90deg, #ff8a00, #e52e71, #ff8a00);
    background-size: 200% 100%;
    animation: gradientMove 3s linear infinite;
}
@keyframes gradientMove {
    0% { background-position: 100% 0; }
    100% { background-position: -100% 0; }
}
.fb-bm-tag {
    display: inline-flex; align-items: center; gap: 0.25rem;
    background: linear-gradient(90deg, #ff8a00, #e52e71);
    color: #fff;
    padding: 0.15rem 0.55rem;
    border-radius: 6px;
    font-size: 0.7rem;
    font-weight: 700;
    box-shadow: 0 2px 6px rgba(229, 46, 113, 0.3);
    letter-spacing: 0.2px;
}

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
.fb-ab-t i{
    display:block;
    height:100%;
    border-radius:99px;
    animation: bar-grow 1.2s cubic-bezier(0.1, 0.9, 0.2, 1) forwards; /* 👈 เพิ่มบรรทัดนี้ */
    transform-origin: left; /* 👈 และเพิ่มบรรทัดนี้เพื่อให้หลอดวิ่งจากซ้ายไปขวา */
}
.c-lime{color:var(--good)}.c-amber{color:var(--warn)}.c-red{color:var(--bad)}
i.c-lime{background:var(--good)}i.c-amber{background:var(--warn)}i.c-red{background:var(--bad)}
/* แถวผลการแข่งขัน */
.fb-rr{display:grid;grid-template-columns:95px 1fr 95px;gap:.85rem;align-items:center;padding:.8rem 1rem;background:var(--card);border:1px solid var(--line);border-left:3px solid var(--bad);border-radius:14px;margin-bottom:.55rem;box-shadow:var(--shadow)}
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

/* ตารางคะแนนสไตล์พรีเมียม */
.fb-mc table tr { border-bottom: 1px solid var(--line); transition: background 0.2s ease; }
.fb-mc table tr:hover { background: var(--chip); }
.fb-mc table td { padding: 0.7rem 0.5rem; vertical-align: middle; color: var(--tx); }
.fb-mc table tr.top-4 td:first-child { border-left: 4px solid var(--good); }
.fb-mc table tr.relegation td:first-child { border-left: 4px solid var(--bad); }
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

/* 🌟 1. กิมมิก: แสงไฟสนามเคลื่อนไหวพื้นหลัง (Animated Stadium Lights) */
@keyframes stadiumLights {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}
.stApp {
    background: radial-gradient(ellipse 55% 42% at 12% 0%, var(--spot), transparent 72%),
                radial-gradient(ellipse 55% 42% at 88% 0%, var(--spot), transparent 72%),
                radial-gradient(circle at 15% 50%, var(--glow1), transparent 60%),
                radial-gradient(circle at 85% 30%, var(--glow2), transparent 60%),
                var(--bg) !important;
    background-size: 200% 200% !important;
    animation: stadiumLights 15s ease infinite; /* เคลื่อนไหวช้าๆ ทุก 15 วินาที */
    background-attachment: fixed !important;
}

/* 🌟 2. กิมมิก: การ์ดแข่งขันและสถิติเด้งสู้มือ (Interactive 3D Hover) */
.fb-mc, .fb-tile, .fb-bars {
    transition: transform 0.3s ease, box-shadow 0.3s ease, border-color 0.3s ease;
}
.fb-mc:hover, .fb-tile:hover, .fb-bars:hover {
    transform: translateY(-5px);
    box-shadow: 0 15px 35px rgba(0,0,0,0.2);
    border-color: var(--acc);
}
.fb-hero {
    transition: transform 0.4s ease, box-shadow 0.4s ease;
}
.fb-hero:hover {
    transform: scale(1.015);
    box-shadow: 0 20px 40px rgba(0,0,0,0.35);
}

/* 🖥️ เดสก์ท็อป: ขยายตัวอักษร / โลโก้ / ตราสโมสร และทำให้ชื่อแอปเด่นขึ้น (มือถือไม่เปลี่ยน) */
@media (min-width: 721px) {
    html { font-size: 110% !important; }                         /* ตัวอักษรทั้งแอปใหญ่ขึ้นประมาณ 10% */
    .block-container { padding-top: 2rem; }
    .fb-bar { gap: 1.2rem; margin: .2rem 0 1.6rem; }
    .fb-logo { width: 76px; height: 76px; border-radius: 22px; }
    .fb-logo svg { width: 44px; height: 44px; }
    .fb-ttl { font-size: 2.1rem; font-weight: 800; letter-spacing: -.025em; line-height: 1.05; }
    .fb-ttl .ai { color: var(--acc); }
    .fb-sub { font-size: 1.02rem; margin-top: .35rem; }
    .fb-bdg { width: 46px; height: 46px; font-size: .85rem; }    /* ตราสโมสร */
    .fb-bdg.lg { width: 76px; height: 76px; font-size: 1.15rem; }
    .fb-bdg.sm { width: 36px; height: 36px; font-size: .72rem; }
    .fb-tm .nm { font-size: 1.05rem; }
    .fb-chip, .fb-plab, .fb-mc-foot, .fb-rr-ai, .fb-panel .xg { font-size: .86rem; }
    .fb-rr-d { font-size: .84rem; }
    .fb-note, .fb-sec .fb-aside { font-size: .88rem; }
}

/* ✨ ปรับโฉม UI (ภาษาออกแบบเดียวกันทั้งแอป) — ใช้ตัวแปรสีของธีม จึงเข้ากับทุกธีม
   หมายเหตุ: Streamlit รุ่นใหม่เปลี่ยนโครงสร้าง (แท็บ/ช่องเลือก/เรดิโอ) จึงเพิ่ม selector ตามโครงสร้างจริงด้วย */
:root { --r-sm: 12px; --r-md: 16px; --r-lg: 22px; --ring: color-mix(in srgb, var(--acc) 22%, transparent); }
::selection { background: color-mix(in srgb, var(--acc) 28%, transparent); }
html, .stApp, [data-testid="stMain"], [data-testid="stAppViewContainer"] {
    scrollbar-width: thin; scrollbar-color: color-mix(in srgb, var(--mut) 40%, transparent) transparent;
}

/* หัวแอป: เส้นแบ่ง + แถบเน้นสีไล่เฉด + โลโก้ไล่เฉด */
.fb-bar { position: relative; padding-bottom: 1.15rem; margin-bottom: 1.4rem; border-bottom: 1px solid var(--line); }
.fb-bar:after { content: ""; position: absolute; left: 0; bottom: -1px; width: 120px; height: 3px; border-radius: 3px;
    background: linear-gradient(90deg, var(--acc), var(--c-away)); }
.fb-logo { background: linear-gradient(145deg, color-mix(in srgb, var(--logo-bg), #fff 18%), var(--logo-bg));
    box-shadow: var(--shadow), inset 0 1px 0 rgba(255,255,255,.22); }

/* หัวข้อส่วน: ไอคอนในแผ่นสีอ่อน */
.fb-sec { font-size: 1.15rem; font-weight: 700; margin: 1.8rem 0 .9rem; letter-spacing: -.005em; }
.fb-sec .fb-ic { box-sizing: border-box; width: 34px; height: 34px; padding: 7px; border-radius: 11px;
    background: color-mix(in srgb, var(--acc) 13%, transparent); }

/* ตัวเลือกแบบเรดิโอ -> ปุ่มเม็ดยา (pill) */
[data-testid="stRadioGroup"] { gap: .5rem !important; flex-wrap: wrap; }
label[data-testid="stRadioOption"] { display: inline-flex !important; align-items: center; background: var(--card) !important;
    border: 1px solid var(--line) !important; border-radius: 999px !important; padding: .38rem 1.1rem !important;
    box-shadow: var(--shadow); cursor: pointer; transition: border-color .15s ease, background .15s ease, transform .15s ease; }
label[data-testid="stRadioOption"] > div > div:first-child { display: none !important; }
label[data-testid="stRadioOption"] p { margin: 0; font-weight: 500; color: var(--mut); }
label[data-testid="stRadioOption"]:hover { border-color: var(--acc) !important; transform: translateY(-1px); }
label[data-testid="stRadioOption"]:has(input:checked) { background: var(--sel-bg) !important; border-color: var(--sel-bg) !important; }
label[data-testid="stRadioOption"]:has(input:checked) p { color: var(--sel-tx); font-weight: 600; }

/* แท็บ -> แถบแบบ segmented */
[data-testid="stTabs"] [role="tablist"] { gap: .25rem !important; background: var(--card); padding: .35rem !important;
    border-radius: 18px; border: 1px solid var(--line); box-shadow: var(--shadow); width: fit-content; max-width: 100%; overflow-x: auto; }
[data-testid="stTabs"] [role="tablist"]:after { display: none !important; }
[data-testid="stTab"] { padding: .55rem 1.15rem !important; border-radius: 13px; transition: background .15s ease; }
[data-testid="stTab"]:hover { background: var(--chip); }
[data-testid="stTab"] .react-aria-SelectionIndicator { display: none !important; }
[data-testid="stTab"] p { margin: 0; font-weight: 500; color: var(--mut); }
[data-testid="stTab"][aria-selected="true"] { background: var(--tabsel-bg); box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--tabsel-tx) 22%, transparent); }
[data-testid="stTab"][aria-selected="true"] p { color: var(--tabsel-tx); font-weight: 600; }
[data-testid="stTabPanel"] { padding-top: 1.1rem; }

/* ช่องเลือก (selectbox) + ป้ายกำกับ */
.react-aria-ComboBox [role="group"] { background: var(--card) !important; border: 1px solid var(--line) !important;
    border-radius: var(--r-sm) !important; box-shadow: var(--shadow); min-height: 2.9rem; transition: border-color .15s ease, box-shadow .15s ease; }
.react-aria-ComboBox [role="group"]:hover { border-color: color-mix(in srgb, var(--acc) 55%, var(--line)) !important; }
.react-aria-ComboBox [role="group"]:focus-within { border-color: var(--acc) !important; box-shadow: 0 0 0 3px var(--ring); }
[data-testid="stWidgetLabel"] p { color: var(--mut); font-weight: 500; }
[role="listbox"] { border-radius: var(--r-sm); }

/* ปุ่ม */
[data-testid="stBaseButton-secondary"], [data-testid="stBaseButton-primary"] { border-radius: var(--r-sm) !important; font-weight: 600;
    min-height: 2.7rem; transition: transform .15s ease, box-shadow .15s ease, border-color .15s ease; }
[data-testid="stBaseButton-secondary"]:hover, [data-testid="stBaseButton-primary"]:hover { transform: translateY(-1px);
    box-shadow: 0 8px 20px color-mix(in srgb, var(--acc) 20%, transparent); }
[data-testid="stBaseButton-secondary"]:active, [data-testid="stBaseButton-primary"]:active { transform: none; }

/* การ์ดหลัก: ลายสนามหญ้า + แผงกระจก + แถบความน่าจะเป็นหนาขึ้น */
.fb-hero { border-radius: 26px; }
.fb-hero:after { content: ""; position: absolute; inset: 0; pointer-events: none; z-index: 0;
    background: repeating-linear-gradient(90deg, rgba(255,255,255,.045) 0 64px, transparent 64px 128px);
    -webkit-mask-image: linear-gradient(180deg, #000 0%, transparent 85%); mask-image: linear-gradient(180deg, #000 0%, transparent 85%); }
.fb-hero > * { z-index: 1; }
.fb-panel { backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px); }
.fb-mc { border-radius: 20px; }
.fb-pbar { height: 10px; }
.fb-tm .sc { font-weight: 700; min-width: 2.1rem; }
.fb-tile { border-radius: 18px; }
.fb-bars { border-radius: 18px; }
.fb-rr { border-radius: 16px; transition: transform .2s ease, box-shadow .2s ease; }
.fb-rr:hover { transform: translateY(-1px); box-shadow: 0 10px 24px color-mix(in srgb, var(--tx) 10%, transparent); }

/* ตารางคะแนน: หัวตารางมีสี + แถบสลับสี */
.fb-mc table thead th { background: color-mix(in srgb, var(--chip) 70%, transparent); }
.fb-mc table thead th:first-child { border-top-left-radius: 12px; }
.fb-mc table thead th:last-child { border-top-right-radius: 12px; }
.fb-mc table tbody tr:nth-child(even) { background: color-mix(in srgb, var(--chip) 45%, transparent); }
.fb-mc table th, .fb-mc table td { border-right: none !important; }
.fb-mc table th:not(:first-child), .fb-mc table td:not(:first-child) { border-left: none !important; }

/* กราฟ / ตาราง / expander ให้เป็นการ์ดเดียวกัน */
[data-testid="stPlotlyChart"], [data-testid="stVegaLiteChart"], [data-testid="stDataFrame"] {
    background: var(--card); border: 1px solid var(--line); border-radius: var(--r-md); box-shadow: var(--shadow); padding: .35rem; }
[data-testid="stExpander"] { border-radius: 18px; overflow: hidden; }
[data-testid="stExpander"] details { border: none !important; background: transparent !important; box-shadow: none !important; }
[data-testid="stExpander"] summary { border-radius: 18px; transition: background .15s ease; }
[data-testid="stExpander"] summary:hover { background: var(--chip); }
[data-testid="stCaptionContainer"] { color: var(--mut); }

@media (max-width: 640px) {
    [data-testid="stTabs"] [role="tablist"] { width: 100%; }
    [data-testid="stTab"] { padding: .5rem .75rem !important; }
    [data-testid="stTab"] p { font-size: .88rem; }
    label[data-testid="stRadioOption"] { padding: .32rem .9rem !important; }
}

/* ทยอยโผล่ขึ้นเบา ๆ ตอนโหลดการ์ด (ปิดอัตโนมัติถ้าผู้ใช้ตั้งค่าลดการเคลื่อนไหว) */
@keyframes fb-rise { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: none; } }
@media (prefers-reduced-motion: no-preference) {
    .fb-hero, .fb-mc, .fb-tile, .fb-bars, .fb-rr { animation: fb-rise .45s ease backwards; }
    .fb-grid .fb-mc:nth-child(2), .fb-tiles .fb-tile:nth-child(2) { animation-delay: .06s; }
    .fb-grid .fb-mc:nth-child(3), .fb-tiles .fb-tile:nth-child(3) { animation-delay: .12s; }
    .fb-grid .fb-mc:nth-child(4) { animation-delay: .18s; }
    .fb-grid .fb-mc:nth-child(5) { animation-delay: .24s; }
    .fb-grid .fb-mc:nth-child(n+6) { animation-delay: .3s; }
}

/* ===== อ่านง่ายขึ้นเมื่อทับลายน้ำลูกฟุตบอล ===== */
/* ข้อความรอง (caption / note): ตัวอักษรดำเข้ม ไม่มีพื้นหลัง */
[data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] p,
.fb-note {
    color: var(--tx) !important;        /* สีเดียวกับตัวอักษรบนปุ่ม */
    font-family: var(--font) !important;
    font-weight: 400 !important;         /* บางเท่าข้อความบนปุ่ม ไม่หนา */
}
.fb-note b, .fb-note strong { font-weight: 400 !important; }
[data-testid="stCaptionContainer"], .fb-note {
    background: none;
    border: none;
    padding: 0;
}
.fb-sub { color: var(--mut-strong) !important; font-weight: 500; }

/* ข้อความเตือน "เพื่อการเรียนรู้รายวิชา" ใต้ชื่อแอป: เด่น สีแดง */
.fb-sub-warn {
    display: inline-block; margin-top: .3rem;
    color: #b3261e; font-weight: 700; font-size: .85rem;
    background: rgba(179, 38, 30, .10); border: 1px solid rgba(179, 38, 30, .35);
    border-radius: 999px; padding: .12rem .7rem;
}

/* ===== การ์ดทำนายหลัก: แสงวิ่งผ่านตลอดเวลา + ขอบเรืองแสงเต้นช้า ๆ ===== */
@keyframes fb-sweep {            /* แถบแสงเริ่มและจบนอกการ์ดทั้งสองด้าน = วนซ้ำแล้วไม่มีรอยต่อ */
    from { background-position: 100% 0, 0 0; }
    to   { background-position: 0% 0, 0 0; }
}
@keyframes fb-hero-glow {
    0%, 100% { box-shadow: var(--shadow-hero), 0 0 16px rgba(120, 230, 180, .22); }
    50%      { box-shadow: var(--shadow-hero), 0 0 42px rgba(150, 255, 205, .55); }
}
.fb-hero {
    background:
        linear-gradient(105deg, transparent 41%, rgba(255,255,255,.03) 44%, rgba(255,255,255,.12) 47%, rgba(255,255,255,.26) 50%,
                         rgba(255,255,255,.12) 53%, rgba(255,255,255,.03) 56%, transparent 59%)
            100% 0 / 300% 100% no-repeat,
        var(--hero-bg);
    animation: fb-rise .45s ease backwards, fb-sweep 5s linear infinite, fb-hero-glow 4s ease-in-out infinite;
}
@media (prefers-reduced-motion: reduce) {
    .fb-hero { animation: none; }
}

/* =====================================================================
   PREMIUM POLISH — เพิ่มความหรู: เงาหลายชั้น, ขอบไฮไลต์, ทองแชมเปญ, ปุ่ม/ฟอร์มนุ่มขึ้น
   ===================================================================== */
html { -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; text-rendering: optimizeLegibility; }
::selection { background: color-mix(in srgb, var(--gold) 38%, transparent); }
* { scrollbar-width: thin; scrollbar-color: color-mix(in srgb, var(--tx) 22%, transparent) transparent; }
*::-webkit-scrollbar { width: 8px; height: 8px; }
*::-webkit-scrollbar-thumb { background: color-mix(in srgb, var(--tx) 20%, transparent); border-radius: 99px; }
*::-webkit-scrollbar-track { background: transparent; }

/* หัวแอป: แถวโลโก้ + ชื่อ/คำบรรยายสูงเท่ากัน อยู่กึ่งกลางกัน • ป้ายแดงแยกบรรทัดใต้แถว • เส้นทองปิดท้าย */
.fb-bar-wrap { position: relative; padding-bottom: 1.25rem; margin-bottom: 1.5rem; }
/* เส้นแบ่งเดียวใต้หัวแอป: เส้นทองบางไล่จางไปทางขวา + แถบเน้นเขียว→ทองเรืองแสงที่ปลายซ้าย */
.fb-bar-wrap::before { content: ""; position: absolute; left: 0; right: 0; bottom: 0; height: 1px;
    background: linear-gradient(90deg, var(--gold), color-mix(in srgb, var(--gold) 40%, transparent) 38%, transparent 96%); }
.fb-bar-wrap::after { content: ""; position: absolute; left: 0; bottom: -1px; width: clamp(90px, 18vw, 160px); height: 3px; border-radius: 3px;
    background: linear-gradient(90deg, var(--acc), var(--gold));
    box-shadow: 0 0 14px color-mix(in srgb, var(--gold) 60%, transparent); }
/* ปิดเส้นกรอบ/แถบเดิมของ .fb-bar เพื่อไม่ให้มีเส้นซ้อนกันสองชั้น */
.fb-bar-wrap .fb-bar { margin: 0 0 .85rem; padding-bottom: 0; border-bottom: none; align-items: center; }
.fb-bar-wrap .fb-bar:after { display: none; }
.fb-logo { box-shadow: 0 0 0 2px color-mix(in srgb, var(--gold) 70%, transparent), 0 8px 20px color-mix(in srgb, var(--acc) 35%, transparent); }
/* ===== หัวแอปขนาดใหญ่ เด่น (ขนาดยืดหยุ่นตามความกว้างจอ: มือถือไม่ล้น เดสก์ท็อปใหญ่เต็มที่) ===== */
.fb-bar-wrap .fb-bar { gap: clamp(.8rem, 2.6vw, 1.3rem); }
.fb-bar .fb-logo {
    width: clamp(54px, 13vw, 78px); height: clamp(54px, 13vw, 78px);
    border-radius: clamp(16px, 4vw, 24px);
    background: linear-gradient(145deg, color-mix(in srgb, var(--logo-bg) 78%, #fff), var(--logo-bg) 62%);
    box-shadow: 0 0 0 3px color-mix(in srgb, var(--gold) 80%, transparent),
                0 0 0 7px color-mix(in srgb, var(--gold) 16%, transparent),
                inset 0 2px 0 rgba(255,255,255,.28),
                0 14px 32px -4px color-mix(in srgb, var(--acc) 50%, transparent);
}
.fb-bar .fb-logo svg { width: 54%; height: 54%; }
.fb-bar .fb-ttl { font-size: clamp(1.5rem, 6.2vw, 2.6rem); font-weight: 800; line-height: 1.1; letter-spacing: -.03em; }
.fb-bar .fb-ttl .ai {
    background: linear-gradient(100deg, var(--acc), var(--gold) 90%);
    -webkit-background-clip: text; background-clip: text;
    -webkit-text-fill-color: transparent; color: transparent;
    padding-right: .04em;
}
.fb-bar .fb-sub { font-size: clamp(.84rem, 2.8vw, 1.05rem); font-weight: 500; letter-spacing: .005em; margin-top: .3rem; line-height: 1.35; }
.fb-bar .fb-sub { line-height: 1.3; margin-top: .1rem; }
.fb-bar-wrap .fb-sub-warn { margin-top: 0; }

/* หัวข้อส่วน: ไอคอนอยู่ในกรอบสี่เหลี่ยมมุมโค้ง */
.fb-sec { letter-spacing: -.005em; }
.fb-sec .fb-ic { box-sizing: content-box; padding: 6px; border-radius: 11px;
    background: color-mix(in srgb, var(--acc) 11%, transparent);
    box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--gold) 38%, transparent); }

/* การ์ดทุกใบ: ไล่เฉดบางมาก + เส้นไฮไลต์ด้านในบน + เงาสองชั้น */
.fb-mc, .fb-tile, .fb-bars, .fb-rr, [data-testid="stMetric"], [data-testid="stExpander"],
[data-testid="stPlotlyChart"], [data-testid="stVegaLiteChart"], [data-testid="stDataFrame"] {
    background: linear-gradient(180deg, var(--card), color-mix(in srgb, var(--card) 93%, var(--bg)));
    border-color: color-mix(in srgb, var(--gold) 20%, var(--line));
    box-shadow: inset 0 1px 0 var(--hl), 0 1px 2px rgba(40,30,15,.05), 0 10px 28px -6px rgba(40,30,15,.12);
}
.fb-mc:hover, .fb-tile:hover, .fb-bars:hover {
    transform: translateY(-3px);
    border-color: color-mix(in srgb, var(--gold) 65%, transparent);
    box-shadow: inset 0 1px 0 var(--hl), 0 2px 4px rgba(40,30,15,.06), 0 18px 38px -8px rgba(40,30,15,.2);
}
[data-testid="stPlotlyChart"], [data-testid="stVegaLiteChart"] { border-radius: 20px; padding: .6rem; }
[data-testid="stMetricValue"] { font-variant-numeric: tabular-nums; letter-spacing: -.01em; }

/* ไทล์สรุป: ตัวเลขใหญ่ขึ้นนิด ป้ายล่างนุ่มขึ้น */
.fb-tile .v { letter-spacing: -.02em; }
.fb-tile .l { letter-spacing: .01em; }

/* หลอดความน่าจะเป็น / แถบสถิติ: มีมิติ */
.fb-pbar { height: 9px; box-shadow: inset 0 1px 2px rgba(0,0,0,.12); }
.fb-pbar i.h, .fb-pbar i.d, .fb-pbar i.a, .fb-ab-t i { background-image: linear-gradient(180deg, rgba(255,255,255,.30), rgba(255,255,255,0) 60%); }
.fb-ab-t { height: 7px; box-shadow: inset 0 1px 2px rgba(0,0,0,.10); }

/* การ์ดหลัก: ขอบทองจาง ๆ + แผงกระจกมีขอบบนสว่าง */
.fb-hero { border-color: color-mix(in srgb, var(--hero-pop) 30%, transparent); }
.fb-panel { box-shadow: inset 0 1px 0 rgba(255,255,255,.14), 0 10px 24px rgba(0,0,0,.18); }
.fb-vsrow .nm { letter-spacing: -.015em; text-shadow: 0 2px 10px rgba(0,0,0,.25); }
.fb-tag.hot { box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--hero-pop) 35%, transparent); }

/* ช่องเลือก / กรอกข้อมูล: โฟกัสแล้วมีวงแสงนุ่ม ๆ */
[data-baseweb="select"]>div, [data-baseweb="input"] { transition: border-color .2s ease, box-shadow .2s ease; box-shadow: inset 0 1px 0 var(--hl); }
[data-baseweb="select"]>div:hover { border-color: color-mix(in srgb, var(--gold) 60%, transparent); }
[data-baseweb="select"]:focus-within>div, [data-baseweb="input"]:focus-within {
    border-color: var(--acc); box-shadow: 0 0 0 3px color-mix(in srgb, var(--acc) 18%, transparent); }

/* ตารางคะแนน: หัวตารางเล็กกว่า เว้นวรรคตัวอักษรเล็กน้อย */
.fb-mc table thead th { font-size: .74rem; letter-spacing: .03em; color: var(--mut-strong); font-weight: 600; }
.fb-mc table td { font-variant-numeric: tabular-nums; }

/* แถบเมนูล่างบนมือถือ: ขอบทองบาง ๆ */
@media (prefers-reduced-motion: reduce) {
    .fb-mc:hover, .fb-tile:hover, .fb-bars:hover { transform: none; }
}
"""

# ---------------------------------------------------------------- ธีม
THEMES = {
    "cream": dict(
        bg="#f4efe4", glow1="rgba(240,190,120,.36)", glow2="rgba(190,225,190,.34)", card="#fffdf8", line="rgba(70,55,35,.11)",
        tx="#2a2823", mut="#7a7365", mut_strong="#4f493d", spot="rgba(255,250,230,.95)", gold="#b8934a", hl="rgba(255,255,255,.80)", track="rgba(70,55,35,.09)", chip="rgba(70,55,35,.07)",
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
    "slate": dict(
        bg="#101214", glow1="transparent", glow2="transparent", card="#171a1d", line="rgba(255,255,255,.07)",
        tx="#e7e9eb", mut="#8b9298", mut_strong="#b9c0c6", spot="transparent", gold="#d4b46a", hl="rgba(255,255,255,.05)", track="rgba(255,255,255,.07)", chip="rgba(255,255,255,.06)",
        c_home="#8fb8a6", c_draw="#454c53", c_away="#c8a27c", good="#86b894", bad="#d27a70", warn="#c8a27c", info="#86a6c8",
        acc="#8fb8a6", logo_bg="#8fb8a6", logo_tx="#101214", btn_bg="#8fb8a6", btn_tx="#101a16", sel_bg="#8fb8a6", sel_tx="#101a16",
        tabsel_bg="rgba(143,184,166,.14)", tabsel_tx="#b5d6c7",
        hero_bg="#1a1e22", hero_tx="#eceef0", hero_mut="#8b9298", hero_line="rgba(255,255,255,.08)", hero_chip="rgba(255,255,255,.07)",
        panel_bg="#121518", hero_pop="#8fb8a6", hero_glow="transparent", tag_bg="rgba(143,184,166,.14)", tag_tx="#9cc7b4",
        h_home="#8fb8a6", h_draw="#454c53", h_away="#c8a27c",
        nav_bg="rgba(23,26,29,.94)", shadow="none", shadow_hero="none", nav_shadow="0 8px 30px rgba(0,0,0,.5)",
        bdg_s="10%", bdg_l="24%", bdg_tx="#cfd4d8",
        cfg=dict(base="dark", primaryColor="#8fb8a6", backgroundColor="#101214", secondaryBackgroundColor="#171a1d", textColor="#e7e9eb")),
    "contrast": dict(
        bg="#edf0f5", glow1="rgba(255,122,89,.10)", glow2="rgba(74,99,216,.08)", card="#ffffff", line="rgba(16,26,58,.09)",
        tx="#111a3a", mut="#6a7391", mut_strong="#444d6b", spot="rgba(255,255,255,.55)", gold="#c9a45c", hl="rgba(255,255,255,.85)", track="rgba(16,26,58,.08)", chip="rgba(16,26,58,.06)",
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
    t = pd.Timestamp(ts_utc) + pd.Timedelta(hours=7)
    return f"{_TH_DAY[t.weekday()]} {t.day} {_TH_MON[t.month - 1]}", f"{t:%H:%M} น."


def _initials(name):
    words = [w for w in re.split(r"[\s.]+", str(name)) if w and w.lower() not in _SKIP]
    if not words:
        return "?"
    return (words[0][:3] if len(words) == 1 else "".join(w[0] for w in words[:3])).upper()


TEAM_CRESTS = {
    "Arsenal": "https://en.wikipedia.org/wiki/Special:FilePath/Arsenal_FC.svg",
    "Aston Villa": "https://en.wikipedia.org/wiki/Special:FilePath/Aston_Villa_FC_new_crest.svg",
    "Bournemouth": "https://en.wikipedia.org/wiki/Special:FilePath/AFC_Bournemouth_(2013).svg",
    "AFC Bournemouth": "https://en.wikipedia.org/wiki/Special:FilePath/AFC_Bournemouth_(2013).svg",
    "Brentford": "https://en.wikipedia.org/wiki/Special:FilePath/Brentford_FC_crest.svg",
    "Brighton": "https://en.wikipedia.org/wiki/Special:FilePath/Brighton_and_Hove_Albion_FC_crest.svg",
    "Brighton & Hove Albion": "https://en.wikipedia.org/wiki/Special:FilePath/Brighton_and_Hove_Albion_FC_crest.svg",
    "Chelsea": "https://en.wikipedia.org/wiki/Special:FilePath/Chelsea_FC.svg",
    "Crystal Palace": "https://en.wikipedia.org/wiki/Special:FilePath/Crystal_Palace_FC_logo_(2022).svg",
    "Everton": "https://en.wikipedia.org/wiki/Special:FilePath/Everton_FC_logo.svg",
    "Fulham": "https://en.wikipedia.org/wiki/Special:FilePath/Fulham_FC_(shield).svg",
    "Ipswich": "https://en.wikipedia.org/wiki/Special:FilePath/Ipswich_Town.svg",
    "Ipswich Town": "https://en.wikipedia.org/wiki/Special:FilePath/Ipswich_Town.svg",
    "Leicester": "https://en.wikipedia.org/wiki/Special:FilePath/Leicester_City_FC_crest.svg",
    "Leicester City": "https://en.wikipedia.org/wiki/Special:FilePath/Leicester_City_FC_crest.svg",
    "Liverpool": "https://en.wikipedia.org/wiki/Special:FilePath/Liverpool_FC.svg",
    "Man City": "https://en.wikipedia.org/wiki/Special:FilePath/Manchester_City_FC_badge.svg",
    "Manchester City": "https://en.wikipedia.org/wiki/Special:FilePath/Manchester_City_FC_badge.svg",
    "Man United": "https://en.wikipedia.org/wiki/Special:FilePath/Manchester_United_FC_crest.svg",
    "Manchester United": "https://en.wikipedia.org/wiki/Special:FilePath/Manchester_United_FC_crest.svg",
    "Manchester Utd": "https://en.wikipedia.org/wiki/Special:FilePath/Manchester_United_FC_crest.svg",
    "Newcastle": "https://en.wikipedia.org/wiki/Special:FilePath/Newcastle_United_Logo.svg",
    "Newcastle United": "https://en.wikipedia.org/wiki/Special:FilePath/Newcastle_United_Logo.svg",
    "Newcastle Utd": "https://en.wikipedia.org/wiki/Special:FilePath/Newcastle_United_Logo.svg",
    "Nott'm Forest": "https://en.wikipedia.org/wiki/Special:FilePath/Nottingham_Forest_F.C._logo.svg",
    "Nottingham Forest": "https://en.wikipedia.org/wiki/Special:FilePath/Nottingham_Forest_F.C._logo.svg",
    "Nott'ham Forest": "https://en.wikipedia.org/wiki/Special:FilePath/Nottingham_Forest_F.C._logo.svg",
    "Southampton": "https://en.wikipedia.org/wiki/Special:FilePath/Southampton_FC.svg",
    "Tottenham": "https://en.wikipedia.org/wiki/Special:FilePath/Tottenham_Hotspur.svg",
    "Tottenham Hotspur": "https://en.wikipedia.org/wiki/Special:FilePath/Tottenham_Hotspur.svg",
    "West Ham": "https://en.wikipedia.org/wiki/Special:FilePath/West_Ham_United_FC_logo.svg",
    "West Ham United": "https://en.wikipedia.org/wiki/Special:FilePath/West_Ham_United_FC_logo.svg",
    "Wolves": "https://en.wikipedia.org/wiki/Special:FilePath/Wolverhampton_Wanderers_FC_logo.svg",
    "Wolverhampton Wanderers": "https://en.wikipedia.org/wiki/Special:FilePath/Wolverhampton_Wanderers_FC_logo.svg",
    "Leeds": "https://en.wikipedia.org/wiki/Special:FilePath/Leeds_United_F.C._logo.svg",
    "Leeds United": "https://en.wikipedia.org/wiki/Special:FilePath/Leeds_United_F.C._logo.svg",
    "Burnley": "https://en.wikipedia.org/wiki/Special:FilePath/Burnley_FC_Logo.svg",
    "Sheffield United": "https://en.wikipedia.org/wiki/Special:FilePath/Sheffield_United_FC_logo.svg",
    "Sheffield Utd": "https://en.wikipedia.org/wiki/Special:FilePath/Sheffield_United_FC_logo.svg",
    "Luton": "https://en.wikipedia.org/wiki/Special:FilePath/Luton_Town_FC.svg",
    "Luton Town": "https://en.wikipedia.org/wiki/Special:FilePath/Luton_Town_FC.svg",
    "Hull City": "https://en.wikipedia.org/wiki/Special:FilePath/Hull_City_A.F.C._logo.svg",
    "Coventry": "https://en.wikipedia.org/wiki/Special:FilePath/Coventry_City_FC_crest.svg",
    "Coventry City": "https://en.wikipedia.org/wiki/Special:FilePath/Coventry_City_FC_crest.svg",
    "Sunderland": "https://en.wikipedia.org/wiki/Special:FilePath/Logo_Sunderland.svg",
    "West Brom": "https://en.wikipedia.org/wiki/Special:FilePath/West_Bromwich_Albion.svg",
    "West Bromwich Albion": "https://en.wikipedia.org/wiki/Special:FilePath/West_Bromwich_Albion.svg",
    "Real Madrid": "https://en.wikipedia.org/wiki/Special:FilePath/Real_Madrid_CF.svg",
    "Barcelona": "https://en.wikipedia.org/wiki/Special:FilePath/FC_Barcelona_(crest).svg",
    "Ath Madrid": "https://en.wikipedia.org/wiki/Special:FilePath/Atletico_Madrid_Logo_2024.svg",
    "Club Atlético de Madrid": "https://en.wikipedia.org/wiki/Special:FilePath/Atletico_Madrid_Logo_2024.svg",
    "Atlético Madrid": "https://en.wikipedia.org/wiki/Special:FilePath/Atletico_Madrid_Logo_2024.svg",
    "Atletico Madrid": "https://en.wikipedia.org/wiki/Special:FilePath/Atletico_Madrid_Logo_2024.svg",
    "Atlético de Madrid": "https://en.wikipedia.org/wiki/Special:FilePath/Atletico_Madrid_Logo_2024.svg",
    "Ath Bilbao": "https://en.wikipedia.org/wiki/Special:FilePath/Athletic_Club_(Minas_Gerais).svg",
    "Athletic Club": "https://en.wikipedia.org/wiki/Special:FilePath/Athletic_Club_(Minas_Gerais).svg",
    "Sociedad": "https://en.wikipedia.org/wiki/Special:FilePath/Real_Sociedad_logo.svg",
    "Real Sociedad de Fútbol": "https://en.wikipedia.org/wiki/Special:FilePath/Real_Sociedad_logo.svg",
    "Real Sociedad": "https://en.wikipedia.org/wiki/Special:FilePath/Real_Sociedad_logo.svg",
    "Villarreal": "https://en.wikipedia.org/wiki/Special:FilePath/Villarreal_CF_logo-en.svg",
    "Betis": "https://en.wikipedia.org/wiki/Special:FilePath/Real_Betis_2022_logo.svg",
    "Real Betis Balompié": "https://en.wikipedia.org/wiki/Special:FilePath/Real_Betis_2022_logo.svg",
    "Real Betis": "https://en.wikipedia.org/wiki/Special:FilePath/Real_Betis_2022_logo.svg",
    "Sevilla": "https://en.wikipedia.org/wiki/Special:FilePath/Sevilla_FC_logo.svg",
    "Valencia": "https://en.wikipedia.org/wiki/Special:FilePath/Valenciacf.svg",
    "Osasuna": "https://en.wikipedia.org/wiki/Special:FilePath/CA_Osasuna_2024_crest.svg",
    "CA Osasuna": "https://en.wikipedia.org/wiki/Special:FilePath/CA_Osasuna_2024_crest.svg",
    "Celta": "https://en.wikipedia.org/wiki/Special:FilePath/RC_Celta_de_Vigo_logo.svg",
    "RC Celta de Vigo": "https://en.wikipedia.org/wiki/Special:FilePath/RC_Celta_de_Vigo_logo.svg",
    "Celta Vigo": "https://en.wikipedia.org/wiki/Special:FilePath/RC_Celta_de_Vigo_logo.svg",
    "Getafe": "https://en.wikipedia.org/wiki/Special:FilePath/Getafe_logo.svg",
    "Mallorca": "https://en.wikipedia.org/wiki/Special:FilePath/RCD_Mallorca_logo.svg",
    "RCD Mallorca": "https://en.wikipedia.org/wiki/Special:FilePath/RCD_Mallorca_logo.svg",
    "Las Palmas": "https://en.wikipedia.org/wiki/Special:FilePath/UD_Las_Palmas_logo.svg",
    "UD Las Palmas": "https://en.wikipedia.org/wiki/Special:FilePath/UD_Las_Palmas_logo.svg",
    "Vallecano": "https://en.wikipedia.org/wiki/Special:FilePath/Rayo_Vallecano_logo.svg",
    "Rayo Vallecano": "https://en.wikipedia.org/wiki/Special:FilePath/Rayo_Vallecano_logo.svg",
    "Rayo Vallecano de Madrid": "https://en.wikipedia.org/wiki/Special:FilePath/Rayo_Vallecano_logo.svg",
    "Alaves": "https://en.wikipedia.org/wiki/Special:FilePath/Deportivo_Alaves_logo_(2020).svg",
    "Deportivo Alavés": "https://en.wikipedia.org/wiki/Special:FilePath/Deportivo_Alaves_logo_(2020).svg",
    "Alavés": "https://en.wikipedia.org/wiki/Special:FilePath/Deportivo_Alaves_logo_(2020).svg",
    "Deportivo Alaves": "https://en.wikipedia.org/wiki/Special:FilePath/Deportivo_Alaves_logo_(2020).svg",
    "Girona": "https://en.wikipedia.org/wiki/Special:FilePath/Girona_FC_Logo.svg",
    "Leganes": "https://en.wikipedia.org/wiki/Special:FilePath/CD_Leganés_logo.svg",
    "CD Leganés": "https://en.wikipedia.org/wiki/Special:FilePath/CD_Leganés_logo.svg",
    "Leganés": "https://en.wikipedia.org/wiki/Special:FilePath/CD_Leganés_logo.svg",
    "Valladolid": "https://en.wikipedia.org/wiki/Special:FilePath/Real_Valladolid_logo_2022.svg",
    "Real Valladolid CF": "https://en.wikipedia.org/wiki/Special:FilePath/Real_Valladolid_logo_2022.svg",
    "Real Valladolid": "https://en.wikipedia.org/wiki/Special:FilePath/Real_Valladolid_logo_2022.svg",
    "Espanol": "https://en.wikipedia.org/wiki/Special:FilePath/RCD_Espanyol_crest.svg",
    "Espanyol": "https://en.wikipedia.org/wiki/Special:FilePath/RCD_Espanyol_crest.svg",
    "RCD Espanyol de Barcelona": "https://en.wikipedia.org/wiki/Special:FilePath/RCD_Espanyol_crest.svg",
    "Málaga": "https://en.wikipedia.org/wiki/Special:FilePath/Málaga_CF.svg",
    "Málaga CF": "https://en.wikipedia.org/wiki/Special:FilePath/Málaga_CF.svg",
    "Malaga": "https://en.wikipedia.org/wiki/Special:FilePath/Málaga_CF.svg",
    "Levante": "https://en.wikipedia.org/wiki/Special:FilePath/Levante_Unión_Deportiva,_S.A.D._logo.svg",
    "Levante UD": "https://en.wikipedia.org/wiki/Special:FilePath/Levante_Unión_Deportiva,_S.A.D._logo.svg",
    "Racing Santander": "https://en.wikipedia.org/wiki/Special:FilePath/Racing_de_Santander_logo.svg",
    "Real Racing Club de Santander": "https://en.wikipedia.org/wiki/Special:FilePath/Racing_de_Santander_logo.svg",
    "Deportivo La Coruna": "https://en.wikipedia.org/wiki/Special:FilePath/RC_Deportivo_A_Coruña_logo_2026.svg",
    "La Coruña": "https://en.wikipedia.org/wiki/Special:FilePath/RC_Deportivo_A_Coruña_logo_2026.svg",
    "RC Deportivo La Coruña": "https://en.wikipedia.org/wiki/Special:FilePath/RC_Deportivo_A_Coruña_logo_2026.svg",
    "Deportivo La Coruña": "https://en.wikipedia.org/wiki/Special:FilePath/RC_Deportivo_A_Coruña_logo_2026.svg",
    "Elche": "https://en.wikipedia.org/wiki/Special:FilePath/Elche_CF_logo.svg",
    "Elche CF": "https://en.wikipedia.org/wiki/Special:FilePath/Elche_CF_logo.svg",
    "Cadiz": "https://en.wikipedia.org/wiki/Special:FilePath/Cádiz_CF_logo.svg",
    "Cádiz CF": "https://en.wikipedia.org/wiki/Special:FilePath/Cádiz_CF_logo.svg",
    "Cádiz": "https://en.wikipedia.org/wiki/Special:FilePath/Cádiz_CF_logo.svg",
    "Almeria": "https://en.wikipedia.org/wiki/Special:FilePath/UD_Almería_logo.svg",
    "UD Almería": "https://en.wikipedia.org/wiki/Special:FilePath/UD_Almería_logo.svg",
    "Almería": "https://en.wikipedia.org/wiki/Special:FilePath/UD_Almería_logo.svg",
    "Oviedo": "https://en.wikipedia.org/wiki/Special:FilePath/Real_Oviedo_logo.svg",
    "Real Oviedo": "https://en.wikipedia.org/wiki/Special:FilePath/Real_Oviedo_logo.svg",
    "Bayern Munich": "https://en.wikipedia.org/wiki/Special:FilePath/FC_Bayern_München_logo_(2024).svg",
    "FC Bayern München": "https://en.wikipedia.org/wiki/Special:FilePath/FC_Bayern_München_logo_(2024).svg",
    "Bayern München": "https://en.wikipedia.org/wiki/Special:FilePath/FC_Bayern_München_logo_(2024).svg",
    "Dortmund": "https://en.wikipedia.org/wiki/Special:FilePath/Borussia_Dortmund_logo.svg",
    "Borussia Dortmund": "https://en.wikipedia.org/wiki/Special:FilePath/Borussia_Dortmund_logo.svg",
    "Leverkusen": "https://en.wikipedia.org/wiki/Special:FilePath/Bayer_04_Leverkusen_logo.svg",
    "Bayer 04 Leverkusen": "https://en.wikipedia.org/wiki/Special:FilePath/Bayer_04_Leverkusen_logo.svg",
    "Bayer 04": "https://en.wikipedia.org/wiki/Special:FilePath/Bayer_04_Leverkusen_logo.svg",
    "Bayer Leverkusen": "https://en.wikipedia.org/wiki/Special:FilePath/Bayer_04_Leverkusen_logo.svg",
    "RB Leipzig": "https://en.wikipedia.org/wiki/Special:FilePath/RB_Leipzig_2014_logo.svg",
    "Stuttgart": "https://en.wikipedia.org/wiki/Special:FilePath/VfB_Stuttgart_1893_Logo.svg",
    "VfB Stuttgart": "https://en.wikipedia.org/wiki/Special:FilePath/VfB_Stuttgart_1893_Logo.svg",
    "Ein Frankfurt": "https://en.wikipedia.org/wiki/Special:FilePath/Eintracht_Frankfurt_crest.svg",
    "Eintracht Frankfurt": "https://en.wikipedia.org/wiki/Special:FilePath/Eintracht_Frankfurt_crest.svg",
    "Eint Frankfurt": "https://en.wikipedia.org/wiki/Special:FilePath/Eintracht_Frankfurt_crest.svg",
    "Frankfurt": "https://en.wikipedia.org/wiki/Special:FilePath/Eintracht_Frankfurt_crest.svg",
    "Wolfsburg": "https://en.wikipedia.org/wiki/Special:FilePath/VfL_Wolfsburg_Logo.svg",
    "VfL Wolfsburg": "https://en.wikipedia.org/wiki/Special:FilePath/VfL_Wolfsburg_Logo.svg",
    "Werder Bremen": "https://en.wikipedia.org/wiki/Special:FilePath/SV-Werder-Bremen-Logo.svg",
    "SV Werder Bremen": "https://en.wikipedia.org/wiki/Special:FilePath/SV-Werder-Bremen-Logo.svg",
    "Freiburg": "https://en.wikipedia.org/wiki/Special:FilePath/SC_Freiburg_logo.svg",
    "SC Freiburg": "https://en.wikipedia.org/wiki/Special:FilePath/SC_Freiburg_logo.svg",
    "Augsburg": "https://en.wikipedia.org/wiki/Special:FilePath/FC_Augsburg_logo.svg",
    "FC Augsburg": "https://en.wikipedia.org/wiki/Special:FilePath/FC_Augsburg_logo.svg",
    "Mainz": "https://en.wikipedia.org/wiki/Special:FilePath/1._FSV_Mainz_05_logo.svg",
    "1. FSV Mainz 05": "https://en.wikipedia.org/wiki/Special:FilePath/1._FSV_Mainz_05_logo.svg",
    "Mainz 05": "https://en.wikipedia.org/wiki/Special:FilePath/1._FSV_Mainz_05_logo.svg",
    "Hoffenheim": "https://en.wikipedia.org/wiki/Special:FilePath/Logo_TSG_Hoffenheim.svg",
    "TSG 1899 Hoffenheim": "https://en.wikipedia.org/wiki/Special:FilePath/Logo_TSG_Hoffenheim.svg",
    "TSG Hoffenheim": "https://en.wikipedia.org/wiki/Special:FilePath/Logo_TSG_Hoffenheim.svg",
    "Heidenheim": "https://en.wikipedia.org/wiki/Special:FilePath/1._FC_Heidenheim_Logo.svg",
    "1. FC Heidenheim 1846": "https://en.wikipedia.org/wiki/Special:FilePath/1._FC_Heidenheim_Logo.svg",
    "1. Heidenheim 1846": "https://en.wikipedia.org/wiki/Special:FilePath/1._FC_Heidenheim_Logo.svg",
    "1. Union Berlin": "https://en.wikipedia.org/wiki/Special:FilePath/1._FC_Union_Berlin_Logo.svg",
    "Union Berlin": "https://en.wikipedia.org/wiki/Special:FilePath/1._FC_Union_Berlin_Logo.svg",
    "Bochum": "https://en.wikipedia.org/wiki/Special:FilePath/VfL_Bochum_logo.svg",
    "VfL Bochum 1848": "https://en.wikipedia.org/wiki/Special:FilePath/VfL_Bochum_logo.svg",
    "St Pauli": "https://en.wikipedia.org/wiki/Special:FilePath/FC_St._Pauli_Logo.svg",
    "FC St. Pauli 1910": "https://en.wikipedia.org/wiki/Special:FilePath/FC_St._Pauli_Logo.svg",
    "St. Pauli": "https://en.wikipedia.org/wiki/Special:FilePath/FC_St._Pauli_Logo.svg",
    "St. Pauli 1910": "https://en.wikipedia.org/wiki/Special:FilePath/FC_St._Pauli_Logo.svg",
    "Kiel": "https://en.wikipedia.org/wiki/Special:FilePath/Holstein_Kiel_Logo.svg",
    "Holstein Kiel": "https://en.wikipedia.org/wiki/Special:FilePath/Holstein_Kiel_Logo.svg",
    "M'gladbach": "https://en.wikipedia.org/wiki/Special:FilePath/Borussia_Mönchengladbach_logo.svg",
    "Borussia Mönchengladbach": "https://en.wikipedia.org/wiki/Special:FilePath/Borussia_Mönchengladbach_logo.svg",
    "Gladbach": "https://en.wikipedia.org/wiki/Special:FilePath/Borussia_Mönchengladbach_logo.svg",
    "M'Gladbach": "https://en.wikipedia.org/wiki/Special:FilePath/Borussia_Mönchengladbach_logo.svg",
    "Hamburg": "https://en.wikipedia.org/wiki/Special:FilePath/Hamburger_SV_logo.svg",
    "Hamburger SV": "https://en.wikipedia.org/wiki/Special:FilePath/Hamburger_SV_logo.svg",
    "Hamburger": "https://en.wikipedia.org/wiki/Special:FilePath/Hamburger_SV_logo.svg",
    "SC Paderborn": "https://en.wikipedia.org/wiki/Special:FilePath/SC_Paderborn_07_Logo_new.svg",
    "SC Paderborn 07": "https://en.wikipedia.org/wiki/Special:FilePath/SC_Paderborn_07_Logo_new.svg",
    "Paderborn 07": "https://en.wikipedia.org/wiki/Special:FilePath/SC_Paderborn_07_Logo_new.svg",
    "FC Koln": "https://en.wikipedia.org/wiki/Special:FilePath/Wappen_1_FC_Koeln.svg",
    "1. FC Köln": "https://en.wikipedia.org/wiki/Special:FilePath/Wappen_1_FC_Koeln.svg",
    "1. Köln": "https://en.wikipedia.org/wiki/Special:FilePath/Wappen_1_FC_Koeln.svg",
    "Köln": "https://en.wikipedia.org/wiki/Special:FilePath/Wappen_1_FC_Koeln.svg",
    "07 Elversberg": "https://en.wikipedia.org/wiki/Special:FilePath/SV_Elversberg_logo.svg",
    "SV Elversberg": "https://en.wikipedia.org/wiki/Special:FilePath/SV_Elversberg_logo.svg",
    "Elversberg": "https://en.wikipedia.org/wiki/Special:FilePath/SV_Elversberg_logo.svg",
    "Hertha": "https://en.wikipedia.org/wiki/Special:FilePath/Hertha_BSC_Logo.svg",
    "Hertha BSC": "https://en.wikipedia.org/wiki/Special:FilePath/Hertha_BSC_Logo.svg",
    "Darmstadt": "https://en.wikipedia.org/wiki/Special:FilePath/SV_Darmstadt_98_logo.svg",
    "SV Darmstadt 98": "https://en.wikipedia.org/wiki/Special:FilePath/SV_Darmstadt_98_logo.svg",
    "Schalke 04": "https://en.wikipedia.org/wiki/Special:FilePath/FC_Schalke_04_Logo.svg",
    "FC Schalke 04": "https://en.wikipedia.org/wiki/Special:FilePath/FC_Schalke_04_Logo.svg",
    "Düsseldorf": "https://en.wikipedia.org/wiki/Special:FilePath/Fortuna_Düsseldorf_logo.svg",
    "Fortuna Düsseldorf": "https://en.wikipedia.org/wiki/Special:FilePath/Fortuna_Düsseldorf_logo.svg",
    "Hannover": "https://en.wikipedia.org/wiki/Special:FilePath/Hannover_96_Logo.svg",
    "Hannover 96": "https://en.wikipedia.org/wiki/Special:FilePath/Hannover_96_Logo.svg",
    "Karlsruhe": "https://en.wikipedia.org/wiki/Special:FilePath/Karlsruher_SC_logo.svg",
    "Karlsruher SC": "https://en.wikipedia.org/wiki/Special:FilePath/Karlsruher_SC_logo.svg",
    "Nürnberg": "https://en.wikipedia.org/wiki/Special:FilePath/1._FC_Nürnberg_logo.svg",
    "1. FC Nürnberg": "https://en.wikipedia.org/wiki/Special:FilePath/1._FC_Nürnberg_logo.svg",
    "Nurnberg": "https://en.wikipedia.org/wiki/Special:FilePath/1._FC_Nürnberg_logo.svg",
}

BIG_TEAMS = {"Arsenal", "Chelsea", "Liverpool", "Man City", "Manchester City", "Man United", "Manchester United", "Tottenham", "Aston Villa", "Newcastle", "Real Madrid", "Barcelona", "Ath Madrid", "Club Atlético de Madrid", "Atletico Madrid", "Atlético Madrid", "Bayern Munich", "Bayern München", "FC Bayern München", "Dortmund", "Borussia Dortmund", "Leverkusen", "Bayer 04 Leverkusen", "RB Leipzig", "Juventus", "Inter", "AC Milan", "Paris SG", "PSG"}

def badge(name, crest=None, size=""):
    """แสดงตราสโมสร หรือโชว์ตัวหนังสือ (Fallback) ถ้าโหลดภาพไม่ขึ้น"""
    cls = f"fb-bdg {size}".strip()
    c = crest if (crest and str(crest).startswith("https://")) else TEAM_CRESTS.get(str(name))
    hue = int(hashlib.md5(str(name).encode("utf-8")).hexdigest()[:4], 16) % 360
    initials = _e(_initials(name))
    
    if c:
        # ระบบกันภาพแตก: ถ้าโหลดรูปไม่ขึ้น ให้ซ่อนรูป แล้วแสดงตัวย่อแทน พร้อมปรับพื้นหลัง
        err_handler = f"this.style.display='none'; this.nextElementSibling.style.display='block'; this.parentElement.classList.remove('has');"
        return f"""<span class="{cls} has" style="--h:{hue}"><img src="{_e(str(c), quote=True)}" alt="" loading="lazy" onerror="{err_handler}"><span style="display:none">{initials}</span></span>"""
    
    return f"""<span class="{cls}" style="--h:{hue}">{initials}</span>"""


def crest_map(df):
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


def app_bar(subtitle, warn=""):
    w = f'<div class="fb-sub-warn">{_e(warn)}</div>' if warn else ""
    return (f'<div class="fb-bar-wrap"><div class="fb-bar"><div class="fb-logo">{icon("ball", 24)}</div>'
            f'<div><div class="fb-ttl"><span class="ai">AI</span> Football Predictor</div><div class="fb-sub">{_e(subtitle)}</div></div></div>{w}</div>')


def section(icon_name, title, aside=""):
    side = f'<span class="fb-aside">{_e(aside)}</span>' if aside else ""
    return f'<div class="fb-sec">{icon(icon_name, 20)}<span>{_e(title)}</span>{side}</div>'


def note(text):
    return f'<div class="fb-note">{_e(text)}</div>'


def empty(icon_name, text):
    return f'<div class="fb-empty">{icon(icon_name, 28)}{_e(text)}</div>'


def hero(m, tag="แมตช์ถัดไป"):
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
    
    # วิเคราะห์ความมั่นใจของ AI (Smart Match Tags)
    p_max = max(m["p"])
    p_min = min(m["p"])
    is_confident = p_max >= 60.0  # โอกาสชนะสูงกว่า 60%
    is_tight = (p_max - p_min) <= 15.0  # เปอร์เซ็นต์สูงสุด-ต่ำสุด ห่างกันไม่เกิน 15% (สูสีมาก)
    
    smart_tag = ''
    if is_confident:
        smart_tag = f'<span class="fb-tag-confident">{icon("target", 12)} AI มั่นใจมาก</span>'
    elif is_tight:
        smart_tag = f'<span class="fb-tag-tight">{icon("alert", 12)} ระวังพลิกล็อก</span>'
    
    # ตรวจสอบว่าเป็นบิ๊กแมตช์หรือไม่
    is_bm = m["home"] in BIG_TEAMS and m["away"] in BIG_TEAMS
    bm_tag = f'<span class="fb-bm-tag">{icon("zap", 12)} บิ๊กแมตช์</span>' if is_bm else ''
    bm_cls = ' big-match' if is_bm else ''
    
    # รวมป้ายเตือนต่างๆ
    all_tags = f"{bm_tag} {smart_tag}".strip()
    
    top = f'{all_tags}<span class="fb-chip">{icon("calendar", 14)}{d}</span><span class="fb-chip">{icon("clock", 14)}{t}</span>'
    top = f'<div style="display:flex;gap:.8rem;align-items:center;flex-wrap:wrap;">{top}</div>{_status_chip(m.get("status"))}'
    tm = lambda n, c, s: f'<div class="fb-tm">{badge(n, c)}<span class="nm">{_e(n)}</span><span class="sc">{s}</span></div>'
    return (f'<div class="fb-mc{bm_cls}"><div class="fb-mc-top">{top}</div>{tm(m["home"], m.get("home_crest"), sh)}{tm(m["away"], m.get("away_crest"), sa)}'
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
    out = []
    for label, pct, sub in rows:
        tone = bar_tone(pct)
        out.append(f'<div><div class="fb-ab-h"><span>{_e(label)}<small>{_e(sub)}</small></span><b class="{tone}">{pct:.0f}%</b></div>'
                   f'<div class="fb-ab-t"><i class="{tone}" style="width:{max(0, min(100, pct)):.0f}%"></i></div></div>')
    return '<div class="fb-bars">' + "".join(out) + "</div>"


def result_row(r):
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

def league_table(df, crests={}):
    rows_html = []
    for idx, r in df.iterrows():
        rank = r.get("อันดับ", idx + 1)
        team = r["ทีม"]
        crest = crests.get(team)
        p = r["แข่ง"]
        w = r["ชนะ"]
        d = r["เสมอ"]
        l = r["แพ้"]
        gf = r["ได้"]
        ga = r["เสีย"]
        gd = r["ลูกได้เสีย"]
        pts = r["แต้ม"]
        
        gd_str = f"+{gd}" if gd > 0 else str(gd)
        gd_cls = "c-lime" if gd > 0 else ("c-red" if gd < 0 else "")
        
        highlight_class = "top-4" if rank <= 4 else ("relegation" if rank >= len(df) - 2 else "")
        
        rows_html.append(f'<tr class="{highlight_class}"><td style="text-align:center; font-weight:700; width: 45px;">{rank}</td><td style="font-weight:600;"><div style="display:flex; align-items:center; gap:0.6rem;">{badge(team, crest, "sm")}<span>{_e(team)}</span></div></td><td style="text-align:center">{p}</td><td style="text-align:center">{w}</td><td style="text-align:center">{d}</td><td style="text-align:center">{l}</td><td style="text-align:center">{gf}</td><td style="text-align:center">{ga}</td><td style="text-align:center; font-weight:600;" class="{gd_cls}">{gd_str}</td><td style="text-align:center; font-weight:700; color:var(--acc); font-size:1.05rem;">{pts}</td></tr>')
    
    table_head = '<thead><tr style="border-bottom: 2px solid var(--line); color: var(--mut); font-size: 0.82rem; text-transform: uppercase;"><th style="text-align:center; padding: 0.75rem 0.5rem;"></th><th style="padding: 0.75rem 0.5rem;">ทีมสโมสร</th><th style="text-align:center; padding: 0.75rem 0.5rem;">แข่ง</th><th style="text-align:center; padding: 0.75rem 0.5rem;">ชนะ</th><th style="text-align:center; padding: 0.75rem 0.5rem;">เสมอ</th><th style="text-align:center; padding: 0.75rem 0.5rem;">แพ้</th><th style="text-align:center; padding: 0.75rem 0.5rem;">ได้</th><th style="text-align:center; padding: 0.75rem 0.5rem;">เสีย</th><th style="text-align:center; padding: 0.75rem 0.5rem;">ต่าง</th><th style="text-align:center; padding: 0.75rem 0.5rem; color: var(--tx);">แต้ม</th></tr></thead>'
    
    body = "".join(rows_html)
    return f'<div class="fb-mc" style="padding: 0.5rem; overflow-x: auto;"><table style="width: 100%; border-collapse: collapse; font-size: 0.9rem;">{table_head}<tbody>{body}</tbody></table></div>'

def spinning_ball_loader(text="กำลังโหลดข้อมูลการแข่งขัน..."):
    return f'<div class="fb-loader-box"><div class="fb-spin-ball">⚽</div><div>{_e(text)}</div></div>'

def model_info_html():
    return f'''<div class="fb-mc" style="margin-top: 1rem;">
        <div style="font-weight: 600; font-size: 1rem; margin-bottom: 0.75rem; display: flex; align-items: center; gap: 0.5rem;">
            {icon("cpu", 18)} <span>รายละเอียดโมเดลและแหล่งข้อมูลอ้างอิง (Model Specs & Data Sources)</span>
        </div>
        <div style="font-size: 0.85rem; color: var(--mut); display: grid; gap: 0.5rem; line-height: 1.5;">
            <div><b>ฟีเจอร์ที่ใช้ (17 ตัวชี้วัด):</b> คะแนน Elo, วันพักผ่อนนักเตะ, ฟอร์มย้อนหลัง และสถิติเชิงลึกจาก FBref</div>
            <div><b>ชุดข้อมูลฝึกสอน (Training Data):</b> วิเคราะห์และเทรนจากแมตช์การแข่งขันจริง 1,190 นัด (11/08/2023 – 20/09/2026) ครอบคลุม 100%</div>
            <div><b>อัลกอริทึม (Algorithm):</b> Random Forest (300 Estimators, Max Depth: 5, Min Samples Leaf: 15 ผ่านการจูนไฮเปอร์พารามิเตอร์)</div>
            <div style="margin-top: 0.5rem; padding-top: 0.5rem; border-top: 1px solid var(--line);"><b>🌐 แหล่งข้อมูลและเว็บไซต์ที่อ้างอิง:</b></div>
            <div style="padding-left: 1rem; display: grid; gap: 0.25rem;">
                <div>• <b>FBref (Football Reference)</b> (fbref.com) - สถิติการแข่งขันเชิงลึก</div>
                <div>• <b>Wikipedia & Wikimedia Commons</b> - แหล่งอ้างอิงตราสโมสรและโลโก้ทีมอย่างเป็นทางการ</div>
                <div>• <b>Football Data APIs</b> - โปรแกรมการแข่งขัน ตารางคะแนน และผลสกอร์ปัจจุบัน</div>
            </div>
        </div>
    </div>'''