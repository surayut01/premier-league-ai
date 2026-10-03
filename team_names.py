"""จับคู่ชื่อทีมจาก football-data.org (API) ให้ตรงกับชื่อใน football-data.co.uk (CSV)

ลำดับการหา:
1. ชื่อตรงกันเป๊ะ
2. ตาราง NAME_MAP (ชื่อที่ต่างกันมาก เช่น Wolverhampton Wanderers -> Wolves)
3. ชื่อที่ตัดคำนำหน้า/ต่อท้าย (FC, AFC, 1., 04 ...) แล้วเหมือนกัน
4. ชื่อหนึ่งเป็นส่วนต้นของอีกชื่อ (ต้องมีผู้ตรงเพียงรายเดียว)
5. fuzzy match (ความคล้าย >= 0.8)
ถ้าหาไม่เจอจะคืน None เพื่อให้ผู้เรียกแจ้งเตือนได้ (ไม่เงียบเหมือนเดิม)
"""
import difflib
import re
import unicodedata

# ชื่อ (ฝั่ง API หรือชื่อเต็ม) -> ชื่อในไฟล์ CSV
NAME_MAP = {
    # --- Premier League ---
    "Manchester City": "Man City",
    "Manchester United": "Man United",
    "Newcastle United": "Newcastle",
    "Nottingham Forest": "Nott'm Forest",
    "Tottenham Hotspur": "Tottenham",
    "West Ham United": "West Ham",
    "Wolverhampton Wanderers": "Wolves",
    "Brighton & Hove Albion": "Brighton",
    "Leeds United": "Leeds",
    "Leicester City": "Leicester",
    "Ipswich Town": "Ipswich",
    "Luton Town": "Luton",
    "Sheffield United": "Sheffield United",
    "West Bromwich Albion": "West Brom",
    # --- La Liga ---
    "Athletic Club": "Ath Bilbao",
    "Club Atlético de Madrid": "Ath Madrid",
    "Atlético Madrid": "Ath Madrid",
    "RC Celta de Vigo": "Celta",
    "Deportivo Alavés": "Alaves",
    "Rayo Vallecano de Madrid": "Vallecano",
    "RCD Espanyol de Barcelona": "Espanol",
    "Real Betis Balompié": "Betis",
    "Real Sociedad de Fútbol": "Sociedad",
    "Real Valladolid CF": "Valladolid",
    "CD Leganés": "Leganes",
    "Cádiz CF": "Cadiz",
    "UD Almería": "Almeria",
    "Real Oviedo": "Oviedo",
    "Levante UD": "Levante",
    # --- Bundesliga ---
    "FC Bayern München": "Bayern Munich",
    "Borussia Dortmund": "Dortmund",
    "Bayer 04 Leverkusen": "Leverkusen",
    "Eintracht Frankfurt": "Ein Frankfurt",
    "Borussia Mönchengladbach": "M'gladbach",
    "TSG 1899 Hoffenheim": "Hoffenheim",
    "1. FSV Mainz 05": "Mainz",
    "FC St. Pauli 1910": "St Pauli",
    "1. FC Heidenheim 1846": "Heidenheim",
    "1. FC Köln": "FC Koln",
    "Hamburger SV": "Hamburg",
    "VfL Bochum 1848": "Bochum",
    "Hertha BSC": "Hertha",
    "SV Darmstadt 98": "Darmstadt",
}

# คำที่ตัดทิ้งตอนเทียบชื่อ (ไม่ตัดคำว่า real / united / city เพราะใช้แยกทีม)
_NOISE = {
    "fc", "afc", "cf", "sv", "bsc", "ud", "cd", "rc", "rcd", "ca", "sc",
    "vfl", "vfb", "tsg", "fsv", "de", "club", "ac", "ssc", "fk",
}


def _norm(name: str) -> str:
    s = unicodedata.normalize("NFKD", str(name))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    tokens = [t for t in s.split() if t not in _NOISE and not t.isdigit()]
    return " ".join(tokens)


_NAME_MAP_NORM = {_norm(k): v for k, v in NAME_MAP.items()}


def clean_display_name(name: str) -> str:
    """ชื่อสำหรับแสดงผล: ตัด FC/AFC ฯลฯ และช่องว่างซ้ำ"""
    name = re.sub(r"\b(FC|AFC|CF|BSC|SV)\b", "", str(name))
    return " ".join(name.split())


def resolve_team(name, known_teams):
    """คืนชื่อทีมในชุด known_teams ที่ตรงกับ name มากที่สุด หรือ None ถ้าไม่พบ"""
    if not name:
        return None
    known = list(known_teams)
    if name in known:
        return name

    n = _norm(name)

    mapped = _NAME_MAP_NORM.get(n)
    if mapped in known:
        return mapped

    norm_to_known = {}
    for k in known:
        norm_to_known.setdefault(_norm(k), k)

    if n in norm_to_known:
        return norm_to_known[n]

    # ชื่อหนึ่งขึ้นต้นด้วยอีกชื่อ เช่น "brighton and hove albion" vs "brighton"
    hits = [
        k for kn, k in norm_to_known.items()
        if len(kn) >= 4 and len(n) >= 4
        and (n.startswith(kn + " ") or kn.startswith(n + " "))
    ]
    if len(hits) == 1:
        return hits[0]

    close = difflib.get_close_matches(n, list(norm_to_known), n=1, cutoff=0.8)
    if close:
        return norm_to_known[close[0]]

    return None
