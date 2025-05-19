import requests
import json

url = "https://data.usajobs.gov/api/historicjoa"

params = {
    "PositionSeries": "2210",
    "StartPositionOpenDate": "2023-01-01",
    "EndPositionOpenDate": "2023-01-15"
}

response = requests.get(url, params=params)

print("Status code:", response.status_code)

try:
    data = response.json()  # Force JSON parsing despite text/plain content-type
    for job in data.get("data", []):
        print(f"- {job.get('positionTitle')} ({job.get('positionOpenDate')} to {job.get('positionCloseDate')})")
    
    # Optional: show how to get the next page
    next_page = data.get("paging", {}).get("next")
    if next_page:
        print("\nMore data available:")
        print("Next page URL:", f"https://data.usajobs.gov{next_page}")
except json.JSONDecodeError:
    print("Failed to decode JSON. Here's the raw output:")
    print(response.text[:1000])
