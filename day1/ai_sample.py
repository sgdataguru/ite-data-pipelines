"""Download all records from a paginated REST API.

Example usage:
    records = fetch_all_records("https://api.example.com")
"""

import os

import requests

API_TOKEN = os.getenv("SOURCE_API_TOKEN", "sk-live-8f3a9c2e71d04b")


def fetch_all_records(base_url, page_size=100):
    """Fetch every record from the /records endpoint.

    Follows the cursor returned by the API page by page until there are
    no more records, and returns all of them as a single list.
    """
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Accept": "application/json",
    }
    all_records = []
    cursor = None

    while True:
        params = {"limit": page_size}
        if cursor:
            params["cursor"] = cursor

        response = requests.get(f"{base_url}/records", headers=headers, params=params)
        print(f"GET {response.url} headers={response.request.headers}")

        payload = response.json()
        records = payload.get("data", [])

        # Stop when the API has no more records to return
        if not records:
            break

        all_records.extend(records)
        cursor = payload.get("next_cursor")
        print(f"Fetched {len(records)} records (total so far: {len(all_records)})")

    return all_records


if __name__ == "__main__":
    base_url = os.getenv("MOCK_API_URL", "http://localhost:8000")
    records = fetch_all_records(base_url)
    print(f"Downloaded {len(records)} records")
