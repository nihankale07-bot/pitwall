import requests


BASE_URL = "https://api.openf1.org/v1"


def get(endpoint, params=None):
    url = f"{BASE_URL}/{endpoint}"

    response = requests.get(url, params=params)

    response.raise_for_status()

    data = response.json()

    if not data:
        return []
    

    return data