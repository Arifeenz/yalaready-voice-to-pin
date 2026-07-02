import sqlite3
from rapidfuzz import process, fuzz
from .normalize_thai import normalize_for_match

DB_PATH = "data/yala_gazetteer.sqlite"


def length_penalty_score(query: str, candidate: str, raw_score: float) -> float:
    if not query or not candidate:
        return 0.0

    q_len = len(query)
    c_len = len(candidate)

    if c_len >= q_len:
        return raw_score

    ratio = c_len / q_len

    # ถ้า candidate สั้นกว่าคำค้นมาก ให้ลดคะแนนแรง
    if ratio < 0.45:
        return raw_score * 0.55

    if ratio < 0.70:
        return raw_score * 0.75

    return raw_score


def search_local_gazetteer(query: str, source_type: str | None = None, limit: int = 5) -> list[dict]:
    clean_query = normalize_for_match(query)

    if not clean_query:
        return []

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        if source_type:
            rows = conn.execute(
                """
                SELECT name, name_clean, source_type, lat, lon
                FROM gazetteer
                WHERE source_type = ?
                """,
                (source_type,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT name, name_clean, source_type, lat, lon
                FROM gazetteer
                """
            ).fetchall()

    choices = {}
    row_lookup = {}

    for index, row in enumerate(rows):
        key = str(index)
        choices[key] = row["name_clean"]
        row_lookup[key] = row

    matches = process.extract(
        clean_query,
        choices,
        scorer=fuzz.WRatio,
        limit=max(limit * 4, 20),
    )

    results = []

    for matched_text, raw_score, key in matches:
        row = row_lookup[key]
        adjusted_score = length_penalty_score(
            clean_query,
            row["name_clean"],
            float(raw_score),
        )

        results.append({
            "name": row["name"],
            "name_clean": row["name_clean"],
            "matched_text": matched_text,
            "type": row["source_type"],
            "score": adjusted_score,
            "raw_score": float(raw_score),
            "lat": float(row["lat"]),
            "lon": float(row["lon"]),
            "provider": "local_osm",
        })

    results = sorted(results, key=lambda item: item["score"], reverse=True)

    return results[:limit]
