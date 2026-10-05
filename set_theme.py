"""เปลี่ยนธีมของแอป:  python set_theme.py cream | slate | contrast
เขียน theme.txt (ui.py อ่าน) และ .streamlit/config.toml (ธีมของ widget ของ Streamlit เอง) ให้ตรงกัน แล้วรันแอปใหม่"""
import os
import sys

import ui

here = os.path.dirname(os.path.abspath(__file__))
if len(sys.argv) != 2 or sys.argv[1] not in ui.THEMES:
    print("ใช้: python set_theme.py <ชื่อธีม>   ธีมที่มี:", ", ".join(ui.THEMES))
    print("ธีมปัจจุบัน:", ui.THEME)
    sys.exit(1)
name = sys.argv[1]
with open(os.path.join(here, "theme.txt"), "w", encoding="utf-8") as f:
    f.write(name + "\n")
os.makedirs(os.path.join(here, ".streamlit"), exist_ok=True)
with open(os.path.join(here, ".streamlit", "config.toml"), "w", encoding="utf-8") as f:
    f.write(ui.config_toml(name))
print("ตั้งธีมเป็น", name, "แล้ว (รัน streamlit run app.py ใหม่)")
