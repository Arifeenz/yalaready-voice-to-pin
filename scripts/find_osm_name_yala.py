from pathlib import Path
import osmium

PBF_PATH = Path("data/thailand-260701.osm.pbf")

# bbox คร่าว ๆ จังหวัดยะลา
MIN_LON = 100.90
MIN_LAT = 5.70
MAX_LON = 101.75
MAX_LAT = 6.75

KEYWORDS = [
    "คณะราษฎร",
    "คณะราษฎรบำรุง",
    "ราษฎรบำรุง",
    "ราษฎร์บำรุง",
    "Kanarat",
    "Kanaras",
    "Kanarasdorn",
    "Kanarasdornbumroong",
    "Bamrung",
    "Yala school",
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
        try:
            if not n.location.valid():
                return

            lat = n.location.lat
            lon = n.location.lon
        except Exception:
            return

        if not in_yala_bbox(lat, lon):
            return

        self.check("node", n.id, n.tags, lat, lon)

    def way(self, w):
        # ปิดไว้ก่อน เพราะ way ไม่มี lat/lon ตรง ๆ
        # ถ้าเปิดแบบเดิมจะหลุดทั้งประเทศ
        return

    def relation(self, r):
        # ปิดไว้ก่อน เพื่อไม่ให้หลุดทั้งประเทศ
        return

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
        print(f"lat={lat}, lon={lon}")

        for key, value in tags:
            print(f"{key}: {value}")


def main():
    if not PBF_PATH.exists():
        raise FileNotFoundError(PBF_PATH)

    handler = FindYalaNameHandler()
    handler.apply_file(str(PBF_PATH), locations=True)

    print("=" * 80)
    print(f"FOUND_IN_YALA_NODE_ONLY: {handler.count}")


if __name__ == "__main__":
    main()
