from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from .extract_components import extract_components
from .local_matcher import search_local_gazetteer
from .longdo_client import longdo_extract_address
from .normalize_thai import normalize_for_match, normalize_thai_text


LOG_PATH = Path("logs/diagnostic_runs.jsonl")


BROAD_PLACE_NAMES = {
    "ยะลา",
    "เมืองยะลา",
    "อำเภอเมืองยะลา",
    "จังหวัดยะลา",
}

GENERIC_POI_NAMES = {
    "มัสยิด",
    "โรงเรียน",
    "โรงพยาบาล",
    "ศาลา",
    "ตลาด",
    "สถานี",
    "วัด",
    "ซอย",
    "ถนน",
}


def is_broad_place_name(value: str | None) -> bool:
    if not value:
        return False

    clean = normalize_for_match(value)
    broad_clean = {normalize_for_match(item) for item in BROAD_PLACE_NAMES}

    return clean in broad_clean


def is_generic_poi_name(value: str | None) -> bool:
    if not value:
        return False

    clean = normalize_for_match(value)
    generic_clean = {normalize_for_match(item) for item in GENERIC_POI_NAMES}

    return clean in generic_clean


def has_precise_address_components(components: dict[str, Any]) -> bool:
    return bool(
        components.get("house_no")
        or components.get("soi")
        or components.get("road")
    )


def should_use_longdo(components: dict[str, Any]) -> bool:
    # ใช้ Longdo เพื่อแยก address structure
    # แต่ไม่ให้ Longdo Extract Address ชนะ local pin ถ้า Longdo ไม่มี lat/lon
    if components.get("house_no"):
        return True

    if components.get("soi"):
        return True

    if components.get("road"):
        return True

    if components.get("province") and not components.get("poi"):
        return True

    return False


def get_query_context(components: dict[str, Any]) -> str:
    if components.get("poi"):
        return "poi"

    if components.get("house_no") and components.get("soi"):
        return "house_soi"

    if components.get("house_no") and components.get("road"):
        return "house_road"

    if components.get("soi"):
        return "soi"

    if components.get("road"):
        return "road"

    return "unknown"


def run_longdo_safely(text: str) -> dict[str, Any] | None:
    try:
        return longdo_extract_address(text)
    except Exception as exc:
        return {
            "provider": "longdo",
            "error": str(exc),
        }


def get_nested_value(data: dict[str, Any] | None, key: str) -> Any:
    if not data:
        return None

    if key in data:
        return data.get(key)

    for nested_key in ["data", "address", "result"]:
        nested = data.get(nested_key)

        if isinstance(nested, dict) and key in nested:
            return nested.get(key)

    return None


def get_longdo_confidence(longdo_result: dict[str, Any] | None) -> float:
    if not longdo_result or longdo_result.get("error"):
        return 0.0

    confidence = get_nested_value(longdo_result, "confidence")

    if confidence is not None:
        try:
            return float(confidence)
        except Exception:
            pass

    useful_fields = [
        "house_no",
        "alley",
        "road",
        "subdistrict",
        "district",
        "province",
    ]

    found_count = 0

    for field in useful_fields:
        value = get_nested_value(longdo_result, field)

        if value:
            found_count += 1

    if found_count >= 4:
        return 0.85

    if found_count >= 3:
        return 0.75

    if found_count >= 2:
        return 0.65

    if found_count >= 1:
        return 0.50

    return 0.0


def longdo_has_useful_address(longdo_result: dict[str, Any] | None) -> bool:
    if not longdo_result or longdo_result.get("error"):
        return False

    useful_fields = [
        "house_no",
        "alley",
        "road",
        "subdistrict",
        "district",
        "province",
    ]

    for field in useful_fields:
        value = get_nested_value(longdo_result, field)

        if value:
            return True

    return False


def simplify_longdo_result(longdo_result: dict[str, Any]) -> dict[str, Any]:
    fields = [
        "house_no",
        "alley",
        "road",
        "subdistrict",
        "district",
        "province",
        "postcode",
        "confidence",
    ]

    simplified: dict[str, Any] = {
        "provider": "longdo",
    }

    for field in fields:
        value = get_nested_value(longdo_result, field)

        if value is not None:
            simplified[field] = value

    confidence = get_longdo_confidence(longdo_result)

    if "confidence" not in simplified:
        simplified["confidence"] = confidence

    # เผื่ออนาคตถ้า Longdo response มี lat/lon
    lat = get_nested_value(longdo_result, "lat")
    lon = get_nested_value(longdo_result, "lon")

    if lat is not None and lon is not None:
        try:
            simplified["lat"] = float(lat)
            simplified["lon"] = float(lon)
        except Exception:
            pass

    return simplified


def extract_numbers(value: str | None) -> set[str]:
    if not value:
        return set()

    return set(re.findall(r"\d+", str(value)))


def numeric_tokens_compatible(
    candidate: dict[str, Any],
    components: dict[str, Any],
) -> bool:
    candidate_name = str(candidate.get("name") or "")

    query_numbers: set[str] = set()

    # ใช้เฉพาะเลขจาก soi/road
    # ไม่ใช้ house_no เพราะบ้านเลขที่ไม่จำเป็นต้องอยู่ในชื่อ candidate
    for key in ["soi", "road"]:
        query_numbers.update(extract_numbers(components.get(key)))

    if not query_numbers:
        return True

    candidate_numbers = extract_numbers(candidate_name)

    # ถ้าคำค้นมีเลขซอย/ถนน แต่ candidate ไม่มีเลขเลย ห้ามใช้
    # เช่น "สิโรรส 10" ไม่ควร match แค่ "ถนนสิโรรส"
    if not candidate_numbers:
        return False

    # ต้องมีเลขตรงกันอย่างน้อยหนึ่งตัว
    # เช่น "วิฑูรอุทิศ 8" ไม่ควร match "วิฑูรอุทิศ 10"
    return bool(query_numbers & candidate_numbers)


def exact_address_parts_compatible(
    candidate: dict[str, Any],
    components: dict[str, Any],
) -> bool:
    soi = components.get("soi")
    road = components.get("road")

    clean_soi = normalize_for_match(soi) if soi else ""
    clean_road = normalize_for_match(road) if road else ""

    # ถ้ามีเลขใน soi/road ต้องให้เลขเข้ากันกับ candidate
    if clean_soi and extract_numbers(clean_soi):
        if not numeric_tokens_compatible(candidate, components):
            return False

    if clean_road and extract_numbers(clean_road):
        if not numeric_tokens_compatible(candidate, components):
            return False

    return True


def add_search_job(
    search_jobs: list[dict[str, Any]],
    query: str | None,
    source_type: str | None,
    reason: str,
) -> None:
    if not query:
        return

    query = query.strip()

    if not query:
        return

    search_jobs.append(
        {
            "query": query,
            "source_type": source_type,
            "reason": reason,
        }
    )


def collect_local_candidates(components: dict[str, Any]) -> list[dict[str, Any]]:
    search_jobs: list[dict[str, Any]] = []

    raw_text = components.get("raw_text")

    poi = components.get("poi")
    soi = components.get("soi")
    road = components.get("road")

    if poi and not is_generic_poi_name(poi):
        add_search_job(search_jobs, poi, None, "poi")

    # geo_sois.csv ใช้ source_type = soi
    if soi:
        add_search_job(search_jobs, soi, "soi", "soi_exact_type")
        add_search_job(search_jobs, soi, None, "soi_fallback_any_type")

    # หลายรายการชื่อขึ้นต้นด้วย "ถนน..."
    # แต่ source_type เป็น soi เช่น "ถนนสิโรรส ซอยสามัคคี"
    if road:
        add_search_job(search_jobs, road, "road", "road_exact_type")
        add_search_job(search_jobs, road, "soi", "road_to_soi_fallback")
        add_search_job(search_jobs, road, None, "road_fallback_any_type")

    # fallback ด้วย raw text เฉพาะกรณีไม่มี POI
    if raw_text and not poi:
        add_search_job(search_jobs, raw_text, "soi", "raw_text_soi_fallback")
        add_search_job(search_jobs, raw_text, None, "raw_text_any_fallback")

    candidates: list[dict[str, Any]] = []
    seen = set()

    for job in search_jobs:
        query = job["query"]
        source_type = job["source_type"]
        reason = job["reason"]

        results = search_local_gazetteer(
            query=query,
            source_type=source_type,
            limit=8,
        )

        for item in results:
            candidate = dict(item)
            candidate["search_query"] = query
            candidate["search_source_type"] = source_type
            candidate["search_reason"] = reason

            key = (
                candidate.get("name"),
                candidate.get("type"),
                candidate.get("lat"),
                candidate.get("lon"),
                reason,
            )

            if key in seen:
                continue

            seen.add(key)

            candidate["quality_score"] = candidate_quality_score(
                candidate=candidate,
                components=components,
            )

            candidates.append(candidate)

    candidates = sorted(
        candidates,
        key=lambda item: item.get("quality_score", 0),
        reverse=True,
    )

    return candidates


def candidate_quality_score(
    candidate: dict[str, Any],
    components: dict[str, Any],
) -> float:
    score = float(candidate.get("score", 0))

    candidate_name = str(candidate.get("name") or "")
    candidate_type = str(candidate.get("type") or "")
    search_reason = str(candidate.get("search_reason") or "")
    search_query = str(candidate.get("search_query") or "")

    clean_candidate = normalize_for_match(candidate_name)
    clean_query = normalize_for_match(search_query)

    poi = components.get("poi")
    soi = components.get("soi")
    road = components.get("road")

    clean_poi = normalize_for_match(poi) if poi else ""
    clean_soi = normalize_for_match(soi) if soi else ""
    clean_road = normalize_for_match(road) if road else ""

    # exact / contains bonuses
    if clean_query and clean_query == clean_candidate:
        score += 25

    if clean_query and clean_query in clean_candidate:
        score += 15

    if clean_candidate and clean_candidate in clean_query:
        score += 8

    # POI intent
    if poi:
        if candidate_type in ["school", "hospital", "place_of_worship", "poi"]:
            score += 10

        if clean_poi and clean_poi == clean_candidate:
            score += 20

        if clean_poi and clean_poi in clean_candidate:
            score += 10

    # SOI intent
    if soi:
        if candidate_type == "soi":
            score += 20

        if clean_soi and clean_soi == clean_candidate:
            score += 15

        if clean_soi and clean_soi in clean_candidate:
            score += 10

    # ROAD intent
    if road:
        if candidate_type in ["road", "soi"]:
            score += 15

        if clean_road and clean_road == clean_candidate:
            score += 25

        if clean_road and clean_road in clean_candidate:
            score += 15

    # ถ้า input เป็นถนน/ซอย อย่าให้ landmark มาแย่งง่าย ๆ
    if search_reason in [
        "road_exact_type",
        "road_to_soi_fallback",
        "road_fallback_any_type",
        "soi_exact_type",
        "soi_fallback_any_type",
        "raw_text_soi_fallback",
        "raw_text_any_fallback",
    ]:
        if candidate_type in ["school", "hospital", "place_of_worship"]:
            score -= 30

        if candidate_type in ["road", "soi"]:
            score += 15

    # ถ้าเลขซอย/ถนนไม่เข้ากัน ให้หักแรง
    # แต่ยังไม่ตัดทิ้งตรงนี้ เพื่อให้เห็น candidate ใน diagnostics
    if not numeric_tokens_compatible(candidate, components):
        score -= 80

    # กันชื่อกว้างเกิน
    if is_broad_place_name(candidate_name):
        score -= 50

    if is_generic_poi_name(candidate_name):
        score -= 25

    # มีพิกัดจริง บวกนิดหน่อย
    if candidate.get("lat") is not None and candidate.get("lon") is not None:
        score += 5

    return round(score, 2)


def pick_best_candidate(candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not candidates:
        return None

    candidates = sorted(
        candidates,
        key=lambda item: item.get("quality_score", 0),
        reverse=True,
    )

    return candidates[0]


def pick_final_candidate(
    best_local: dict[str, Any] | None,
    longdo_result: dict[str, Any] | None,
    components: dict[str, Any],
    has_precise_address: bool = False,
) -> dict[str, Any] | None:
    longdo_confidence = get_longdo_confidence(longdo_result)
    has_useful_longdo = longdo_has_useful_address(longdo_result)

    longdo_candidate = None

    if (
        longdo_result is not None
        and not longdo_result.get("error")
        and has_useful_longdo
        and longdo_confidence >= 0.60
    ):
        longdo_candidate = simplify_longdo_result(longdo_result)

    # ถ้า local มี lat/lon และคุณภาพดี ให้ local เป็น pin ก่อน
    # แต่ต้องไม่ผิดเลขซอย/ถนน
    if best_local:
        quality_score = float(best_local.get("quality_score", 0))
        score = float(best_local.get("score", 0))

        if (
            quality_score >= 70
            and score >= 70
            and exact_address_parts_compatible(best_local, components)
        ):
            final = dict(best_local)

            if longdo_candidate:
                final["address_provider"] = "longdo"
                final["address_components"] = longdo_candidate

            return final

    # ถ้า local ไม่ดี หรือเลขไม่ตรง แต่ Longdo แยก address ได้
    # ให้คืน Longdo เป็น metadata แต่จะยังไม่มี lat/lon
    if longdo_candidate:
        return longdo_candidate

    return None


def write_diagnostic_log(payload: dict[str, Any]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    with LOG_PATH.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, ensure_ascii=False) + "\n")


def run_voice_to_pin_pipeline(text: str) -> dict[str, Any]:
    request_id = str(uuid.uuid4())
    normalized_text = normalize_thai_text(text)
    components = extract_components(normalized_text)

    local_candidates = collect_local_candidates(components)
    best_local = pick_best_candidate(local_candidates)

    longdo_result = None

    if should_use_longdo(components):
        longdo_result = run_longdo_safely(normalized_text)

    has_precise_address = has_precise_address_components(components)

    final_candidate = pick_final_candidate(
        best_local=best_local,
        longdo_result=longdo_result,
        components=components,
        has_precise_address=has_precise_address,
    )

    # สำหรับระบบฉุกเฉิน ให้ manual confirm เสมอใน phase นี้
    # แต่ถ้ามี lat/lon แล้ว UI สามารถเปิด pin ตรงจุดนี้ให้ผู้ใช้ตรวจได้
    needs_manual_confirm = True

    result: dict[str, Any] = {
        "request_id": request_id,
        "input_text": text,
        "normalized_text": normalized_text,
        "components": components,
        "query_context": get_query_context(components),
        "local_candidates": local_candidates[:10],
        "best_local_candidate": best_local,
        "longdo_result": longdo_result,
        "final_candidate": final_candidate,
        "needs_manual_confirm": needs_manual_confirm,
        "created_at": datetime.utcnow().isoformat() + "Z",
    }

    write_diagnostic_log(result)

    return result


# alias เผื่อ script เก่าเรียกชื่อ process_voice_to_pin
def process_voice_to_pin(text: str) -> dict[str, Any]:
    return run_voice_to_pin_pipeline(text)