# Voice to Pin - YalaReady

ฟีเจอร์แปลงข้อความจากเสียงภาษาไทยให้เป็นพิกัดสำหรับปักหมุดบนแผนที่ โดยเน้นพื้นที่เมืองยะลา

ระบบนี้ใช้หลายแหล่งข้อมูลร่วมกัน:

1. Local gazetteer จาก OSM
2. ฐานข้อมูลซอย/ถนนย่อย `geo_sois.csv`
3. Longdo Extract Address สำหรับแยกบ้านเลขที่ ถนน ซอย จังหวัด
4. Manual confirmation สำหรับเคสที่ยังไม่มั่นใจ

## Current status

ระบบสามารถปักหมุดได้ดีในกลุ่มต่อไปนี้:

### Landmark

ตัวอย่างที่ทดสอบผ่าน:

| สถานที่ | พิกัด |
|---|---|
| มัสยิดกลางจังหวัดยะลา | `6.5663147, 101.2940893` |
| โรงเรียนคณะราษฎรบำรุง | `6.5547592, 101.2895504` |
| โรงพยาบาลยะลา | `6.5480818, 101.2767711` |
| ศาลหลักเมืองยะลา | `6.5411746, 101.280404` |

### Soi / Road

ตัวอย่างที่ทดสอบผ่าน:

| ซอย/ถนน | พิกัด |
|---|---|
| ถนนสิโรรส ซอยสามัคคี | `6.556741, 101.287346` |
| ถนนสิโรรส ซอยมายอ | `6.566997, 101.293617` |
| ถนนสิโรรส ซอยสองพี่น้อง | `6.566602, 101.296367` |
| ถนนสิโรรส ซอยมัสยิด 2 | `6.571141, 101.298547` |
| ถนนวิฑูรอุทิศ 10 ซอยตูแวอุทิศ | `6.557904, 101.296055` |
| ถนนวิฑูรอุทิศ 12 ซอย 2 | `6.558317, 101.295786` |

## Important behavior

ถ้าข้อความมีบ้านเลขที่ แต่ซอย/ถนนมีอยู่ในฐาน ระบบจะปักไปที่ซอย/ถนนนั้นก่อน และตั้งค่า `needs_manual_confirm = true`

ตัวอย่าง:

```txt
บ้านเลขที่ 12 ถนนสิโรรส ซอยสามัคคี จังหวัดยะลา

Safety rule

ระบบจะไม่เดาพิกัดถ้าเลขซอย/ถนนไม่ตรงกับฐานข้อมูล

ตัวอย่างที่ระบบจะไม่ปักอัตโนมัติ:

บ้านเลขที่ 50 ซอยสิโรรส 10 จังหวัดยะลา
บ้านเลขที่ 9 ถนนวิฑูรอุทิศ 8 จังหวัดยะลา


****

Setup
1. Install dependencies
pip install -r requirements.txt
2. Create .env
cp .env.example .env

On Windows PowerShell:

Copy-Item .env.example .env

Then add Longdo key:

LONGDO_API_KEY=your_key_here
3. Run tests
python scripts/test_sois.py

Expected result:

Known sois should return provider=local_osm
Known landmarks should return provider=local_osm
Unknown soi numbers should return FINAL: None or require manual confirmation
Main pipeline usage
from app.voice_to_pin.pipeline import run_voice_to_pin_pipeline

result = run_voice_to_pin_pipeline("ถนนสิโรรส ซอยสามัคคี จังหวัดยะลา")

print(result["final_candidate"])

Example final candidate:

{
  "provider": "local_osm",
  "name": "ถนนสิโรรส ซอยสามัคคี",
  "type": "soi",
  "lat": 6.556741,
  "lon": 101.287346,
  "needs_manual_confirm": true
}
Key files
app/voice_to_pin/pipeline.py

Main orchestration:

normalize text
extract address components
search local gazetteer
call Longdo when needed
choose final candidate
write diagnostic logs
app/voice_to_pin/extract_components.py

Extracts:

house_no
soi
road
poi
province
app/voice_to_pin/local_matcher.py

Searches SQLite gazetteer using fuzzy matching

app/voice_to_pin/longdo_client.py

Calls Longdo Extract Address API

scripts/import_geo_sois.py

Imports data/geo_sois.csv into data/yala_gazetteer.sqlite

scripts/check_roads.py

Debug script for checking roads/sois in gazetteer

scripts/test_sois.py

Regression test for known sois, roads, and landmarks

Rebuild gazetteer

If using fresh OSM PBF:

python scripts/build_gazetteer.py
python scripts/import_geo_sois.py

Required file:

data/thailand-260701.osm.pbf

The PBF file is not committed to git because it is large.

Output contract

Pipeline returns:

{
    "request_id": "...",
    "input_text": "...",
    "normalized_text": "...",
    "components": {...},
    "query_context": "...",
    "local_candidates": [...],
    "best_local_candidate": {...},
    "longdo_result": {...},
    "final_candidate": {...},
    "needs_manual_confirm": True,
    "created_at": "..."
}
UI recommendation

For emergency use, always show a map confirmation step.

Recommended flow:

User speaks location
Pipeline returns suggested pin
UI opens map at suggested pin
User confirms or drags marker
Submit final lat/lon
