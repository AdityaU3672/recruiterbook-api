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
    
    # Keywords related to recruiting roles
    recruiting_keywords = [
        "recruiter", "talent", "hiring", "recruitment", "sourcing", 
        "hr", "human resources", "people operations", "talent acquisition",
        "staffing", "personnel", "talent partner"
    ]
    
    for item in items:
        snippet = item.get("snippet", "").lower()
        link = item.get("link", "").lower()
        title = item.get("title", "").lower()
        
        # Check for LinkedIn profile which is a strong indicator
        if "linkedin.com/in/" in link:
            # Check if any recruiting keyword is in the snippet or title
            for keyword in recruiting_keywords:
                if keyword in snippet or keyword in title:
                    return True
                    
        # Also check non-LinkedIn results for recruiting keywords
        for keyword in recruiting_keywords:
            if keyword in snippet:
                return True

    return False
