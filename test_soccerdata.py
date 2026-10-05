import soccerdata as sd

def test_fbref_soccerdata():
    print("กำลังเชื่อมต่อ FBref ด้วย soccerdata...")
    
    # กำหนดลีกและฤดูกาล (ENG-Premier League, ฤดูกาล 2023-2024 ใช้ '2324', ถ้าล่าสุดลอง '2425')
    fbref = sd.FBref(leagues="ENG-Premier League", seasons="2425") # ลองเปลี่ยนเป็น 2425
    
    print("กำลังดึงตารางสถิติรวมของทีม (Standard Stats)...")
    # ดึงตาราง Standard Stats (พวกเป้าหมาย xG, การครองบอล)
    team_stats = fbref.read_team_season_stats(stat_type="standard")
    
    print("\n✅ ดึงข้อมูลสำเร็จ! ตัวอย่างข้อมูล 5 ทีมแรก:")
    print(team_stats.head())
    
    print("\nคอลัมน์ที่มีให้ใช้งาน:")
    print(list(team_stats.columns))

if __name__ == "__main__":
    test_fbref_soccerdata()