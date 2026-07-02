import sqlite3

DB_PATH = "data/yala_gazetteer.sqlite"

KEYWORDS = [
    "คณะ",
    "ราษฎร",
    "บำรุง",
    "คณะราษฎร",
    "Kanarat",
    "Kanaras",
    "Bamrung",
]

conn = sqlite3.connect(DB_PATH)

for keyword in KEYWORDS:
    print("=" * 80)
    print(f"keyword: {keyword}")

    rows = conn.execute(
        """
        SELECT name, source_type, lat, lon
        FROM gazetteer
        WHERE name LIKE ?
        ORDER BY name
        LIMIT 50
        """,
        (f"%{keyword}%",),
    ).fetchall()

    if not rows:
        print("not found")
        continue

    for row in rows:
        print(row)

conn.close()
