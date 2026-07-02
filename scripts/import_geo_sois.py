import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd


CSV_PATH = Path("data/geo_sois.csv")
DB_PATH = Path("data/yala_gazetteer.sqlite")


def clean_name(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""

    text = str(value).strip()

    text = text.replace(" ", "")
    text = text.replace("ถนน", "")
    text = text.replace("ถ.", "")
    text = text.replace("ซอย", "")
    text = text.replace("ซ.", "")

    return text.strip()


def safe_text(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""

    return str(value).strip()


def make_aliases(row: pd.Series) -> list[str]:
    aliases: list[str] = []

    name = safe_text(row.get("name"))
    parent_road = safe_text(row.get("parent_road"))
    name_en = safe_text(row.get("name_en"))

    if name:
        aliases.append(name)

    if parent_road:
        aliases.append(parent_road)

        if name and parent_road not in name:
            aliases.append(f"{parent_road} {name}")

    if name_en:
        aliases.append(name_en)

    # เพิ่ม alias แบบตัดคำว่า "ถนน" เพื่อ match กับคำพูด เช่น "สิโรรส 10"
    more_aliases: list[str] = []

    for alias in aliases:
        stripped = alias.replace("ถนน", "").replace("ซอย", "").strip()

        if stripped and stripped != alias:
            more_aliases.append(stripped)

    aliases.extend(more_aliases)

    seen = set()
    unique_aliases: list[str] = []

    for alias in aliases:
        alias = alias.strip()

        if not alias:
            continue

        if alias in seen:
            continue

        seen.add(alias)
        unique_aliases.append(alias)

    return unique_aliases


def get_source_type(name: str, highway: str) -> str:
    if "ซอย" in name:
        return "soi"

    if "ถนน" in name:
        return "road"

    if highway:
        return "road"

    return "road"


def load_existing_gazetteer(conn: sqlite3.Connection) -> pd.DataFrame:
    try:
        return pd.read_sql_query("SELECT * FROM gazetteer", conn)
    except Exception:
        return pd.DataFrame(
            columns=[
                "name",
                "name_clean",
                "source_type",
                "lat",
                "lon",
                "name_key",
                "osm_type",
                "osm_id",
            ]
        )


def main() -> None:
    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"ไม่พบไฟล์ {CSV_PATH} ให้เอา geo_sois.csv ไปวางไว้ในโฟลเดอร์ data ก่อน"
        )

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"ไม่พบไฟล์ {DB_PATH} ให้รัน python scripts/build_gazetteer.py ก่อน"
        )

    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")

    required_columns = {"name", "lat", "lng"}
    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        raise RuntimeError(f"geo_sois.csv ขาดคอลัมน์: {sorted(missing_columns)}")

    rows: list[dict[str, Any]] = []

    for index, (_, row) in enumerate(df.iterrows()):
        name = safe_text(row.get("name"))
        highway = safe_text(row.get("highway"))

        lat_value = row.get("lat")
        lon_value = row.get("lng")

        if pd.isna(lat_value) or pd.isna(lon_value):
            continue

        try:
            lat = float(str(lat_value))
            lon = float(str(lon_value))
        except ValueError:
            continue

        source_type = get_source_type(name=name, highway=highway)

        for alias in make_aliases(row):
            name_clean = clean_name(alias)

            if not name_clean:
                continue

            rows.append(
                {
                    "name": alias,
                    "name_clean": name_clean,
                    "source_type": source_type,
                    "lat": lat,
                    "lon": lon,
                    "name_key": "geo_sois",
                    "osm_type": "geo_sois_csv",
                    "osm_id": index,
                }
            )

    if not rows:
        raise RuntimeError("ไม่พบข้อมูลที่ import ได้จาก geo_sois.csv")

    imported = pd.DataFrame(rows)

    with sqlite3.connect(DB_PATH) as conn:
        existing = load_existing_gazetteer(conn)

        merged = pd.concat([existing, imported], ignore_index=True)

        merged = merged.dropna(subset=["name_clean"])
        merged = merged.drop_duplicates(
            subset=["name_clean", "source_type", "lat", "lon"]
        )

        merged.to_sql("gazetteer", conn, if_exists="replace", index=False)

        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_gazetteer_name ON gazetteer(name_clean)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_gazetteer_type ON gazetteer(source_type)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_gazetteer_osm ON gazetteer(osm_type, osm_id)"
        )

    print(f"Imported geo_sois alias rows: {len(imported)}")
    print(f"Total gazetteer rows: {len(merged)}")
    print(f"Saved to: {DB_PATH}")

    print("\nCheck สิโรรส / วิฑูร / ทัดบำรุง:")

    mask = (
        merged["name"].str.contains("สิโรรส", na=False)
        | merged["name"].str.contains("วิฑูร", na=False)
        | merged["name"].str.contains("วิทูร", na=False)
        | merged["name"].str.contains("ทัดบำรุง", na=False)
        | merged["name"].str.contains("Wit", case=False, na=False)
        | merged["name"].str.contains("Vitoon", case=False, na=False)
        | merged["name"].str.contains("Siroros", case=False, na=False)
    )

    matched = merged[mask][
        ["name", "source_type", "lat", "lon", "osm_type", "osm_id"]
    ]

    if matched.empty:
        print("not found")
    else:
        print(matched.to_string(index=False))


if __name__ == "__main__":
    main()