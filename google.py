import requests
import os
from models import IndustryEnum

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

def infer_company_industry(company_name: str) -> str:
    """
    Uses Google Search to infer a company's industry based on search results.
    Returns the industry as a string for backward compatibility.
    The caller should convert to enum integer using IndustryEnum.from_str().
    """
    query = f"{company_name} industry sector"
    data = google_search(query)
    
    items = data.get("items", [])
    if not items:
        return "Tech"  # Default to Tech
    
    # Limit industry categories to the four required ones
    industry_keywords = {
        "tech": ["tech", "technology", "software", "hardware", "it ", "information technology", 
                "digital", "computing", "electronics", "saas", "cloud", "telecommunications",
                "internet", "app", "platform", "development", "coding", "artificial intelligence", "AI"],
        "finance": ["finance", "financial", "banking", "investment", "insurance", "wealth management", 
                   "fintech", "capital", "broker", "trading", "bank", "asset management", "private equity",
                   "venture capital", "mortgage", "credit"],
        "consulting": ["consulting", "consultant", "advisory", "professional services", 
                     "business consulting", "management consulting", "strategy consulting", 
                     "solutions provider", "business solutions", "advisory services"],
        "healthcare": ["healthcare", "health", "medical", "pharmaceutical", "biotech", "life sciences", 
                     "hospital", "wellness", "medicine", "clinical", "therapeutics", "patient care",
                     "health services", "pharma", "health tech"]
    }
    
    # Count matches for each industry category
    industry_matches = {industry: 0 for industry in industry_keywords}
    
    # Analyze snippets and titles from search results
    for item in items:
        snippet = item.get("snippet", "").lower()
        title = item.get("title", "").lower()
        combined_text = snippet + " " + title
        
        for industry, keywords in industry_keywords.items():
            for keyword in keywords:
                if keyword in combined_text:
                    industry_matches[industry] += 1
    
    # Find the industry with the most matches
    best_match = max(industry_matches.items(), key=lambda x: x[1])
    
    # If we have matches, return the best one
    if best_match[1] > 0:
        return best_match[0].title()  # Capitalize the industry name
    else:
        return "Tech"  # Default to Tech
