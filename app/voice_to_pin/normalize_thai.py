import re


def normalize_thai_text(text: str) -> str:
    if not text:
        return ""

    text = str(text).strip()
    text = text.replace("ฯ", "")
    text = re.sub(r"\s+", " ", text)

    replacements = {
        "ถ.": "ถนน",
        "ซ.": "ซอย",
        "ต.": "ตำบล",
        "อ.": "อำเภอ",
        "จ.": "จังหวัด",
        "ม.": "หมู่",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text.strip()


def normalize_for_match(text: str) -> str:
    text = normalize_thai_text(text)
    text = text.replace(" ", "")

    remove_words = [
        "ถนน",
        "ซอย",
        "ตำบล",
        "ตําบล",
        "อำเภอ",
        "อําเภอ",
        "จังหวัด",
        "หมู่บ้าน",
        "บ้าน",
        "ใกล้",
        "แถว",
        "ตรง",
        "บริเวณ",
    ]

    for word in remove_words:
        text = text.replace(word, "")

    return text.strip()
