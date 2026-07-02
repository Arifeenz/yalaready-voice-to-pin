import sqlite3
from pathlib import Path


DB_PATH = Path("data/yala_gazetteer.sqlite")


KEYWORDS = [
    "สิโรรส",
    "ซอยสิโรรส",
    "ถนนสิโรรส",
    "สิโรรส 10",
    "วิฑูร",
    "วิทูร",
    "วิฑูรอุทิศ",
    "วิทูรอุทิศ",
    "วิฑูรอุทิศ 8",
    "วิทูรอุทิศ 8",
    "ทัดบำรุง",
    "ถนนทัดบำรุง",
    "Siroros",
    "Witoon",
    "Witun",
    "Vitoon",
]


def print_rows(keyword: str, rows: list[tuple]) -> None:
    print("=" * 100)
    print(f"keyword: {keyword}")

    if not rows:
        print("not found")
        return

    for row in rows:
        name, source_type, lat, lon, name_key, osm_type, osm_id = row

        print(
            f"name={name} | "
            f"type={source_type} | "
            f"lat={lat} | "
            f"lon={lon} | "
            f"name_key={name_key} | "
            f"osm_type={osm_type} | "
            f"osm_id={osm_id}"
        )


def search_keyword(conn: sqlite3.Connection, keyword: str) -> list[tuple]:
    return conn.execute(
        """
        SELECT name, source_type, lat, lon, name_key, osm_type, osm_id
        FROM gazetteer
        WHERE name LIKE ?
           OR name_clean LIKE ?
        ORDER BY
            CASE
                WHEN name = ? THEN 0
                WHEN name LIKE ? THEN 1
                ELSE 2
            END,
            source_type,
            name
        LIMIT 100
        """,
        (
            f"%{keyword}%",
            f"%{keyword.replace(' ', '')}%",
            keyword,
            f"{keyword}%",
        ),
    ).fetchall()


def print_source_summary(conn: sqlite3.Connection) -> None:
    print("=" * 100)
    print("SOURCE SUMMARY")

    rows = conn.execute(
        """
        SELECT source_type, osm_type, COUNT(*) AS count
        FROM gazetteer
        GROUP BY source_type, osm_type
        ORDER BY source_type, osm_type
        """
    ).fetchall()

    for source_type, osm_type, count in rows:
        print(f"type={source_type} | osm_type={osm_type} | count={count}")


def print_geo_sois_sample(conn: sqlite3.Connection) -> None:
    print("=" * 100)
    print("GEO_SOIS SAMPLE")

    rows = conn.execute(
        """
        SELECT name, source_type, lat, lon, osm_id
        FROM gazetteer
        WHERE osm_type = 'geo_sois_csv'
        ORDER BY osm_id, name
        LIMIT 30
        """
    ).fetchall()

    if not rows:
        print("not found")
        return

    for name, source_type, lat, lon, osm_id in rows:
        print(
            f"name={name} | "
            f"type={source_type} | "
            f"lat={lat} | "
            f"lon={lon} | "
            f"osm_id={osm_id}"
        )


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"ไม่พบไฟล์ {DB_PATH} ให้รัน python scripts/build_gazetteer.py ก่อน"
        )

    with sqlite3.connect(DB_PATH) as conn:
        print_source_summary(conn)
        print_geo_sois_sample(conn)

        for keyword in KEYWORDS:
            rows = search_keyword(conn, keyword)
            print_rows(keyword, rows)


if __name__ == "__main__":
    main()