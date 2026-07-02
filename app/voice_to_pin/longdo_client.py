import os
import requests
from dotenv import load_dotenv

load_dotenv()

LONGDO_API_KEY = os.getenv("LONGDO_API_KEY")


def longdo_extract_address(text: str) -> dict:
    if not LONGDO_API_KEY:
        return {
            "error": "LONGDO_API_KEY is not set",
            "provider": "longdo",
        }

    url = "https://search.longdo.com/smartsearch/json/extract_address/v2"

    params = {
        "key": LONGDO_API_KEY,
        "text": text,
    }

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()

    data = response.json()
    data["provider"] = "longdo"

    return data