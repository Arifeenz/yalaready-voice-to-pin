import os
import requests
from dotenv import load_dotenv

load_dotenv()

LONGDO_API_KEY = os.getenv("LONGDO_API_KEY")

# จุดกลางเมืองยะลา เอาไว้ bias ผลค้นหา
YALA_CENTER_LAT = 6.5567245
YALA_CENTER_LON = 101.2902517

TEST_QUERIES = [
    "บ้านเลขที่ 50 ซอยสิโรรส 10 จังหวัดยะลา",
    "บ้านเลขที่ 9 ถนนวิฑูรอุทิศ 8 จังหวัดยะลา",
    "ซอยสิโรรส 10 จังหวัดยะลา",
    "ถนนวิฑูรอุทิศ 8 จังหวัดยะลา",
]


def search_longdo(keyword: str):
    if not LONGDO_API_KEY:
        raise RuntimeError("LONGDO_API_KEY is not set")

    url = "https://search.longdo.com/mapsearch/json/search"

    params = {
        "key": LONGDO_API_KEY,
        "keyword": keyword,
        "lat": YALA_CENTER_LAT,
        "lon": YALA_CENTER_LON,
        "span": "10km",
        "limit": 5,
        "locale": "th",
    }

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()

    return response.json()


def main():
    for keyword in TEST_QUERIES:
        print("=" * 100)
        print(f"QUERY: {keyword}")

        data = search_longdo(keyword)
        results = data.get("data", [])

        if not results:
            print("NO RESULTS")
            continue

        for index, item in enumerate(results, start=1):
            print("-" * 100)
            print(f"#{index}")
            print(f"name: {item.get('name')}")
            print(f"lat: {item.get('lat')}")
            print(f"lon: {item.get('lon')}")
            print(f"address: {item.get('address')}")
            print(f"type: {item.get('type')}")
            print(f"tag: {item.get('tag')}")
            print(f"distance: {item.get('distance')}")


if __name__ == "__main__":
    main()
