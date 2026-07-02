import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.voice_to_pin.pipeline import run_voice_to_pin_pipeline as process_voice_to_pin


TESTS = [
    # ซอย/ถนนที่มีจริงใน geo_sois.csv
    "ถนนสิโรรส ซอยสามัคคี จังหวัดยะลา",
    "บ้านเลขที่ 12 ถนนสิโรรส ซอยสามัคคี จังหวัดยะลา",
    "ถนนสิโรรส ซอยมายอ จังหวัดยะลา",
    "บ้านเลขที่ 50 ถนนสิโรรส ซอยมายอ จังหวัดยะลา",
    "ถนนสิโรรส ซอยสองพี่น้อง จังหวัดยะลา",
    "ถนนสิโรรส ซอยมัสยิด 2 จังหวัดยะลา",
    "ถนนวิฑูรอุทิศ 10 ซอยตูแวอุทิศ จังหวัดยะลา",
    "บ้านเลขที่ 9 ถนนวิฑูรอุทิศ 10 ซอยตูแวอุทิศ จังหวัดยะลา",
    "ถนนวิฑูรอุทิศ 12 ซอย 2 จังหวัดยะลา",

    # เคสที่ยังไม่มีตรง ๆ ใช้ดูว่าระบบควรไม่มั่ว
    "บ้านเลขที่ 50 ซอยสิโรรส 10 จังหวัดยะลา",
    "บ้านเลขที่ 9 ถนนวิฑูรอุทิศ 8 จังหวัดยะลา",

    # เทสว่า landmark เดิมยังไม่พัง
    "มัสยิดกลางจังหวัดยะลา",
    "โรงเรียนคณะราษฎรบำรุง จังหวัดยะลา",
    "โรงพยาบาลยะลา",
    "ศาลหลักเมืองยะลา",
]


def main():
    for text in TESTS:
        print("=" * 120)
        print(f"INPUT: {text}")

        result = process_voice_to_pin(text)

        components = result.get("components", {})
        final = result.get("final_candidate")

        print(f"components: {components}")

        if not final:
            print("FINAL: None")
            print("needs_manual_confirm:", result.get("needs_manual_confirm"))
            continue

        print(
            "FINAL:",
            f"provider={final.get('provider')}",
            f"name={final.get('name')}",
            f"type={final.get('type')}",
            f"score={final.get('score')}",
            f"quality={final.get('quality_score')}",
            f"lat={final.get('lat')}",
            f"lon={final.get('lon')}",
            sep=" | ",
        )

        print("needs_manual_confirm:", result.get("needs_manual_confirm"))


if __name__ == "__main__":
    main()