from pathlib import Path
import osmium

PBF_PATH = Path("data/thailand-260701.osm.pbf")

# bbox คร่าว ๆ ยะลา
MIN_LON = 100.90
MIN_LAT = 5.70
MAX_LON = 101.75
MAX_LAT = 6.75

KEYWORDS = [
    "คณะราษฎร",
    "คณะราษฎรบำรุง",
    "ราษฎรบำรุง",
    "Kanarat",
    "Kanaras",
    "Kanarasadorn",
    "Bamrung",
    "Yala School",
]


def in_yala_bbox(lat: float | None, lon: float | None) -> bool:
    if lat is None or lon is None:
        return False

    return MIN_LAT <= lat <= MAX_LAT and MIN_LON <= lon <= MAX_LON


class FindYalaNameHandler(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.count = 0

    def node(self, n):
        lat = None
        lon = None

        try:
            if n.location.valid():
                lat = n.location.lat
                lon = n.location.lon
        except Exception:
            pass

        if not in_yala_bbox(lat, lon):
            return

        self.check("node", n.id, n.tags, lat, lon)

    def way(self, w):
        # way ไม่มี centroid ง่าย ๆ ใน SimpleHandler รอบนี้
        # แต่ยังเช็ก tag ได้ ถ้าชื่อ match จะ print ออกมา
        self.check("way", w.id, w.tags, None, None)

    def relation(self, r):
        self.check("relation", r.id, r.tags, None, None)

    def check(self, osm_type, osm_id, tags, lat, lon):
        name_values = []

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
                name_values.append((key, value))

        if not name_values:
            return

        joined = " ".join(value for _, value in name_values)

        if not any(keyword.lower() in joined.lower() for keyword in KEYWORDS):
            return

        self.count += 1

        print("=" * 80)
        print(f"{osm_type} {osm_id}")

        if lat is not None and lon is not None:
            print(f"lat={lat}, lon={lon}")

        for key, value in tags:
            print(f"{key}: {value}")


def main():
    if not PBF_PATH.exists():
        raise FileNotFoundError(PBF_PATH)

    handler = FindYalaNameHandler()
    handler.apply_file(str(PBF_PATH), locations=True)

    print("=" * 80)
    print(f"FOUND: {handler.count}")


if __name__ == "__main__":
    main()