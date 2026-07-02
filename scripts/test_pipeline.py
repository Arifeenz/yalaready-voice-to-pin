import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.voice_to_pin.pipeline import run_voice_to_pin_pipeline


TEST_CASES = [
    {
        "name": "mosque_center_yala",
        "text": "น้ำท่วมใกล้มัสยิดกลางยะลา ตำบลสะเตง อำเภอเมืองยะลา",
        "expected_provider": "local_osm",
        "expected_name_contains": "มัสยิดกลาง",
        "expected_type": "place_of_worship",
    },
    {
        "name": "siroros_precise_address",
        "text": "บ้านเลขที่ 12 ซอย 3 ถนนสิโรรส จังหวัดยะลา",
        "expected_provider": "longdo",
        "expected_road": "สิโรรส",
        "expected_alley": "3",
        "expected_house_no": "12",
    },
    {
        "name": "kanarasdorn_school",
        "text": "มีคนติดอยู่ใกล้โรงเรียนคณะราษฎรบำรุง จังหวัดยะลา",
        "expected_provider": "local_osm",
        "expected_name_contains": "คณะราษฎรบำรุง",
        "expected_type": "school",
    },
    {
        "name": "yala_hospital",
        "text": "มีผู้ป่วยติดอยู่ใกล้โรงพยาบาลยะลา",
        "expected_provider": "local_osm",
        "expected_name_contains": "โรงพยาบาลยะลา",
    },
    {
        "name": "city_pillar",
        "text": "น้ำท่วมบริเวณศาลหลักเมืองยะลา",
        "expected_provider": "local_osm",
        "expected_name_contains": "ศาลหลักเมืองยะลา",
    },
    {
        "name": "tad_bamrung_road",
        "text": "รถติดอยู่แถวถนนทัดบำรุง จังหวัดยะลา",
        "expected_provider_any": ["local_osm", "longdo"],
        "expected_name_or_road_contains": "ทัดบำรุง",
    },
        {
        "name": "siroros_soi_10_house_50",
        "text": "บ้านเลขที่ 50 ซอยสิโรรส 10 จังหวัดยะลา",
        "expected_provider": "longdo",
        "expected_house_no": "50",
    },
    {
        "name": "witoon_uthit_8_house_9",
        "text": "บ้านเลขที่ 9 ถนนวิฑูรอุทิศ 8 จังหวัดยะลา",
        "expected_provider": "longdo",
        "expected_house_no": "9",
    },
]


def get_nested(data, key, default=None):
    if not isinstance(data, dict):
        return default

    return data.get(key, default)


def check_case(result, test_case):
    final_candidate = result.get("final_candidate") or {}

    errors = []

    provider = final_candidate.get("provider")

    expected_provider = test_case.get("expected_provider")
    if expected_provider and provider != expected_provider:
        errors.append(f"provider expected {expected_provider}, got {provider}")

    expected_provider_any = test_case.get("expected_provider_any")
    if expected_provider_any and provider not in expected_provider_any:
        errors.append(f"provider expected one of {expected_provider_any}, got {provider}")

    expected_name_contains = test_case.get("expected_name_contains")
    if expected_name_contains:
        name = final_candidate.get("name", "")
        if expected_name_contains not in name:
            errors.append(f"name expected contains {expected_name_contains}, got {name}")

    expected_type = test_case.get("expected_type")
    if expected_type:
        candidate_type = final_candidate.get("type")
        if candidate_type != expected_type:
            errors.append(f"type expected {expected_type}, got {candidate_type}")

    expected_road = test_case.get("expected_road")
    if expected_road:
        road = final_candidate.get("road", "")
        if road != expected_road:
            errors.append(f"road expected {expected_road}, got {road}")

    expected_alley = test_case.get("expected_alley")
    if expected_alley:
        alley = final_candidate.get("alley", "")
        if alley != expected_alley:
            errors.append(f"alley expected {expected_alley}, got {alley}")

    expected_house_no = test_case.get("expected_house_no")
    if expected_house_no:
        house_no = final_candidate.get("house_no", "")
        if house_no != expected_house_no:
            errors.append(f"house_no expected {expected_house_no}, got {house_no}")

    expected_name_or_road_contains = test_case.get("expected_name_or_road_contains")
    if expected_name_or_road_contains:
        name = final_candidate.get("name", "")
        road = final_candidate.get("road", "")
        combined = f"{name} {road}"
        if expected_name_or_road_contains not in combined:
            errors.append(
                f"name/road expected contains {expected_name_or_road_contains}, got {combined}"
            )

    return errors


def summarize_candidate(candidate):
    if not candidate:
        return "None"

    provider = candidate.get("provider")

    if provider == "longdo":
        parts = [
            f"provider={provider}",
            f"confidence={candidate.get('confidence')}",
            f"house_no={candidate.get('house_no')}",
            f"alley={candidate.get('alley')}",
            f"road={candidate.get('road')}",
            f"province={candidate.get('province')}",
        ]
        return " | ".join(parts)

    parts = [
        f"provider={provider}",
        f"name={candidate.get('name')}",
        f"type={candidate.get('type')}",
        f"score={candidate.get('score')}",
        f"quality={candidate.get('quality_score')}",
        f"lat={candidate.get('lat')}",
        f"lon={candidate.get('lon')}",
    ]
    return " | ".join(parts)


def main():
    passed = 0
    failed = 0

    for test_case in TEST_CASES:
        print("=" * 100)
        print(f"CASE: {test_case['name']}")
        print(f"TEXT: {test_case['text']}")

        result = run_voice_to_pin_pipeline(test_case["text"])
        errors = check_case(result, test_case)

        final_candidate = result.get("final_candidate")

        print(f"COMPONENTS: {json.dumps(result.get('components'), ensure_ascii=False)}")
        print(f"USE_LONGDO: {result.get('use_longdo')} | reasons={result.get('longdo_reasons')}")
        print(f"FINAL: {summarize_candidate(final_candidate)}")

        if errors:
            failed += 1
            print("STATUS: FAIL")
            for error in errors:
                print(f"  - {error}")
        else:
            passed += 1
            print("STATUS: PASS")

    print("=" * 100)
    print(f"SUMMARY: passed={passed}, failed={failed}, total={passed + failed}")

    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
