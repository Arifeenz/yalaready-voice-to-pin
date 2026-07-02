import re
from .normalize_thai import normalize_thai_text


STOP_WORDS = [
    "ตำบล",
    "ตําบล",
    "อำเภอ",
    "อําเภอ",
    "จังหวัด",
    "ใกล้",
    "แถว",
    "ตรง",
    "บริเวณ",
    "ข้าง",
    "หน้า",
    "หลัง",
]


def cut_at_stop_words(value: str) -> str:
    if not value:
        return value

    value = value.strip()

    for stop_word in STOP_WORDS:
        index = value.find(stop_word)
        if index > 0:
            value = value[:index].strip()

    return value.strip(" ,.-")


def extract_after_label(text: str, label: str) -> str | None:
    pattern = rf"{label}\s*([ก-๙A-Za-z0-9\/\-\s]+)"
    match = re.search(pattern, text)

    if not match:
        return None

    return cut_at_stop_words(match.group(1))


def remove_address_parts_for_poi(text: str) -> str:
    # กันเคส "วัด" ที่ติดอยู่ในคำว่า "จังหวัด"
    text = re.sub(r"จังหวัด\s*[ก-๙A-Za-z0-9\s]*", "", text)
    text = re.sub(r"อำเภอ\s*[ก-๙A-Za-z0-9\s]*", "", text)
    text = re.sub(r"ตำบล\s*[ก-๙A-Za-z0-9\s]*", "", text)
    return text


def extract_components(text: str) -> dict:
    text = normalize_thai_text(text)

    components = {
        "house_no": None,
        "soi": None,
        "road": None,
        "poi": None,
        "subdistrict": None,
        "district": None,
        "province": None,
        "raw_text": text,
    }

    house_match = re.search(r"(บ้านเลขที่|เลขที่)\s*([0-9]+\/?[0-9]*)", text)
    if house_match:
        components["house_no"] = house_match.group(2)

    components["soi"] = extract_after_label(text, "ซอย")
    components["road"] = extract_after_label(text, "ถนน")
    components["subdistrict"] = extract_after_label(text, "ตำบล")
    components["district"] = extract_after_label(text, "อำเภอ")
    components["province"] = extract_after_label(text, "จังหวัด")

    province_match = re.search(r"จังหวัด\s*([ก-๙A-Za-z]+)", text)
    if province_match:
        components["province"] = province_match.group(1).strip()

    poi_text = remove_address_parts_for_poi(text)

    # เอาคำยาวก่อนคำสั้น โดยเฉพาะ "วัด"
    poi_keywords = [
        "โรงพยาบาล",
        "โรงเรียน",
        "มัสยิด",
        "ศาลหลักเมือง",
        "ศาลากลาง",
        "ศาลา",
        "ตลาด",
        "เทศบาล",
        "สถานี",
        "อบต",
        "ปั๊ม",
        "ปตท",
        "วัด",
    ]

    for keyword in poi_keywords:
        match = re.search(rf"({keyword}[ก-๙A-Za-z0-9\s]*)", poi_text)
        if match:
            poi = cut_at_stop_words(match.group(1))

            if poi and keyword in poi:
                components["poi"] = poi
                break

    return components
