"""คัดฟีเจอร์ด้วย permutation importance ข้ามทุกลีก (รันเมื่อมีข้อมูลใหม่/อยากทบทวนชุดฟีเจอร์)

  python select_features.py

วิธีคิด: เทรนด้วยนัดเก่า สลับค่าของแต่ละกลุ่มฟีเจอร์ในช่วงตรวจ 380 นัด (เว้น 380 นัดล่าสุดไว้ทดสอบจริง)
แล้วดูว่า log-loss แย่ลงเท่าไร • เก็บกลุ่มที่ค่าเฉลี่ย > 0 และเป็นบวกอย่างน้อย 2 จาก 3 ลีก (Elo เก็บเสมอ)
ผลลัพธ์เป็นข้อเสนอ ต้องตรวจซ้ำด้วย walk-forward แล้วค่อยแก้ config.FB_STATS / data_prep.BASE_FEATURES
หมายเหตุ: ฟีเจอร์ที่สัมพันธ์กันจะแบ่งคะแนนกัน และค่ามีความแกว่งสูง (ข้อมูลหลักร้อยนัด)
"""
import pandas as pd

import data_prep
import evaluation as ev
from config import LEAGUES

MIN_LEAGUES = 2


def main():
    per_league = {}
    for lg in LEAGUES:
        master, _ = data_prep.build_league_master(lg)
        # เริ่มจากชุดเต็ม (ทุกสถิติที่มีในข้อมูล) เพื่อให้ประเมินตัวที่ถูกตัดไปแล้วได้ด้วย: ใส่ชื่อใน config.FB_STATS ชั่วคราว
        feats = list(data_prep.feature_sets(master).values())[-1]
        imp, base = ev.permutation_importance(master, feats)
        per_league[lg] = imp.set_index("กลุ่ม")["delta"]
        print(f"{lg}: log-loss ช่วงตรวจ {base:.4f}")
    tab = pd.DataFrame(per_league)
    tab["mean"] = tab.mean(axis=1)
    tab["leagues>0"] = (tab[list(LEAGUES)] > 0).sum(axis=1)
    tab = tab.sort_values("mean", ascending=False)
    print(tab.round(4).to_string())
    keep = tab.index[(tab["mean"] > 0) & (tab["leagues>0"] >= MIN_LEAGUES)].union(["Elo"])
    print("\nเสนอให้เก็บ:", sorted(keep))
    print("เสนอให้ตัด:", sorted(set(tab.index) - set(keep)))


if __name__ == "__main__":
    main()
