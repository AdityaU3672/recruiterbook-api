import requests
import os

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
SEARCH_ENGINE_ID = os.getenv("SEARCH_ENGINE_ID")

def google_search(query: str):
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": GOOGLE_API_KEY,
        "cx": SEARCH_ENGINE_ID,
        "q": query
    }
    response = requests.get(url, params=params)
    return response.json()  

def verify_recruiter(name: str, company: str) -> bool:
    query = f"{name} {company}"
    data = google_search(query)

    items = data.get("items", [])
    if not items:
        return False
    
    for item in items:
        snippet = item.get("snippet", "").lower()
        link = item.get("link", "").lower()
        if "recruiter" in snippet:
            return True

    return False
