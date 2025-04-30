"""
Script to update all existing companies to use one of the four industry categories:
Tech, Finance, Consulting, or Healthcare.

This script should be run once after deploying the new industry changes to ensure
all existing companies are properly categorized.
"""
import sys
import os
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Company
from google import infer_company_industry

def update_company_industries(db: Session, force_update=True):
    """Updates all companies to use one of the four allowed industry categories."""
    valid_industries = ["Tech", "Finance", "Consulting", "Healthcare"]
    
    # Get all companies or only those needing an update
    if force_update:
        companies = db.query(Company).all()
    else:
        companies = db.query(Company).filter(
            (Company.industry.is_(None)) | 
            (~Company.industry.in_(valid_industries))
        ).all()
    
    if not companies:
        print("No companies to update.")
        return
    
    print(f"Found {len(companies)} companies to update...")
    
    # Industry mapping for any invalid values
    industry_map = {
        "Retail": "Tech",
        "Media": "Tech",
        "Education": "Consulting",
        "Manufacturing": "Tech",
        "Real Estate": "Finance",
        "Energy": "Tech",
        "Transportation": "Tech",
        "Unknown": "Tech"
    }
    
    updated_count = 0
    for company in companies:
        current_industry = company.industry
        
        # Determine new industry
        if current_industry in valid_industries:
            # Already valid, skip if not force_update
            if not force_update:
                continue
        elif current_industry in industry_map:
            # Map the existing industry to one of our valid categories
            company.industry = industry_map[current_industry]
        else:
            # Use Google Search to infer the industry
            inferred_industry = infer_company_industry(company.name)
            
            # Ensure it's one of our valid industries
            if inferred_industry in valid_industries:
                company.industry = inferred_industry
            elif inferred_industry in industry_map:
                company.industry = industry_map[inferred_industry]
            else:
                # Default to Tech if no mapping or inference
                company.industry = "Tech"
        
        updated_count += 1
        print(f"Updated {company.name}: {current_industry} → {company.industry}")
    
    # Commit all changes
    if updated_count > 0:
        db.commit()
        print(f"Successfully updated {updated_count} companies.")
    else:
        print("No companies needed updating.")

if __name__ == "__main__":
    try:
        db = SessionLocal()
        force = len(sys.argv) > 1 and sys.argv[1].lower() == "force"
        update_company_industries(db, force_update=force)
        print("Industry update completed successfully.")
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        if 'db' in locals():
            db.close() 