from pathlib import Path
import sqlite3
import pandas as pd
import osmium

PBF_PATH = Path("data/thailand-260701.osm.pbf")
DB_PATH = Path("data/yala_gazetteer.sqlite")

# bbox คร่าว ๆ จังหวัดยะลา
MIN_LON = 100.90
MIN_LAT = 5.70
MAX_LON = 101.75
MAX_LAT = 6.75


MANUAL_ALIASES = {
    "Kanarasdornbumroong Yala school": [
        "โรงเรียนคณะราษฎรบำรุง",
        "คณะราษฎรบำรุง",
        "โรงเรียนคณะราษฎร์บำรุง",
        "คณะราษฎร์บำรุง",
        "โรงเรียนคณะราษฎรบำรุงยะลา",
        "คณะราษฎรบำรุงยะลา",
        "Kanarat Bamrung Yala School",
        "Kanarasdornbumroong Yala school",
    ],
}


def clean_name(value):
    if value is None:
        return None

    text = str(value).strip()
    text = text.replace(" ", "")
    text = text.replace("ถนน", "")
    text = text.replace("ถ.", "")
    text = text.replace("ซอย", "")
    text = text.replace("ซ.", "")

    return text


def in_yala_bbox(lat, lon):
    if lat is None or lon is None:
        return False

    return MIN_LAT <= lat <= MAX_LAT and MIN_LON <= lon <= MAX_LON


def get_source_type(tags):
    if "highway" in tags:
        return "road"

    if tags.get("amenity") == "school":
        return "school"

    if tags.get("amenity") == "hospital":
        return "hospital"

    if tags.get("amenity") == "place_of_worship":
        return "place_of_worship"

    poi_keys = [
        "amenity",
        "shop",
        "tourism",
        "leisure",
        "office",
        "building",
        "religion",
        "place",
        "name",
        "name:th",
        "name:en",
    ]

    for key in poi_keys:
        if key in tags:
            return "poi"

    return "named_place"


def get_names_from_tags(tags):
    names = []

    for key in [
        "name",
        "name:th",
        "name:en",
        "official_name",
        "alt_name",
        "old_name",
        "short_name",
    ]:
        value = tags.get(key)
        if value:
            names.append((key, value))

    return names


def expand_aliases(name):
    aliases = [name]

    if name in MANUAL_ALIASES:
        aliases.extend(MANUAL_ALIASES[name])

    seen = set()
    unique_aliases = []

    for alias in aliases:
        if not alias:
            continue

        if alias in seen:
            continue

        seen.add(alias)
        unique_aliases.append(alias)

    return unique_aliases


class YalaGazetteerHandler(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.total_named_nodes_in_yala = 0

    def node(self, n):
        names = get_names_from_tags(n.tags)

        if not names:
            return

        try:
            if not n.location.valid():
                return

            lat = n.location.lat
            lon = n.location.lon
        except Exception:
            return

        if not in_yala_bbox(lat, lon):
            return

        self.total_named_nodes_in_yala += 1
        source_type = get_source_type(n.tags)

        for name_key, name in names:
            for alias_name in expand_aliases(name):
                name_clean = clean_name(alias_name)

                if not name_clean:
                    continue

                self.rows.append({
                    "name": alias_name,
                    "name_clean": name_clean,
                    "source_type": source_type,
                    "lat": lat,
                    "lon": lon,
                    "name_key": name_key,
                    "osm_type": "node",
                    "osm_id": int(n.id),
                })

    def way(self, w):
        # ตั้งใจไม่อ่าน way ในเวอร์ชันนี้
        # เพราะถ้ายังไม่มี centroid filter จะหลุดทั้งประเทศ
        return

    def relation(self, r):
        # ตั้งใจไม่อ่าน relation ในเวอร์ชันนี้
        return


def save_to_sqlite(gazetteer: pd.DataFrame):
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        gazetteer.to_sql("gazetteer", conn, if_exists="replace", index=False)

        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_gazetteer_name ON gazetteer(name_clean)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_gazetteer_type ON gazetteer(source_type)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_gazetteer_osm ON gazetteer(osm_type, osm_id)"
        )


def main():
    if not PBF_PATH.exists():
        raise FileNotFoundError(f"ไม่พบไฟล์ {PBF_PATH}")

    handler = YalaGazetteerHandler()

    print(f"Reading {PBF_PATH} ...")
    print("Mode: YALA NODE ONLY")
    print(f"BBOX: lon {MIN_LON}-{MAX_LON}, lat {MIN_LAT}-{MAX_LAT}")

    handler.apply_file(str(PBF_PATH), locations=True)

    if not handler.rows:
        raise RuntimeError(
            "ไม่พบ node ที่มี name/name:th/name:en ใน bbox ยะลา"
        )

    gazetteer = pd.DataFrame(handler.rows)

    gazetteer = gazetteer.dropna(subset=["name_clean"])
    gazetteer = gazetteer.drop_duplicates(
        subset=["name_clean", "source_type", "lat", "lon"]
    )

    save_to_sqlite(gazetteer)

    print(f"Named nodes in Yala bbox: {handler.total_named_nodes_in_yala}")
    print(f"Saved rows with aliases: {len(gazetteer)}")
    print(f"Saved to: {DB_PATH}")

    print("\nSample:")
    print(gazetteer.head(30).to_string(index=False))

    print("\nCheck Kanaras / คณะราษฎร:")
    mask = (
        gazetteer["name"].str.contains("คณะ", na=False)
        | gazetteer["name"].str.contains("ราษฎร", na=False)
        | gazetteer["name"].str.contains("Kanaras", case=False, na=False)
        | gazetteer["name"].str.contains("Kanarat", case=False, na=False)
        | gazetteer["name"].str.contains("Bamrung", case=False, na=False)
    )

    matched = gazetteer[mask]

    if matched.empty:
        print("not found")
    else:
        print(matched.to_string(index=False))


if __name__ == "__main__":
    main()
