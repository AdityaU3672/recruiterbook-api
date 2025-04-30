"""
Production-ready script to update PostgreSQL database with industry information.
This script:
1. Alters the companies table to add the industry column if it doesn't exist
2. Updates all existing companies to one of the four categories: Tech, Finance, Consulting, Healthcare
"""
import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from google import infer_company_industry
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database connection string from environment
DATABASE_URL = os.getenv("DATABASE_URL")

def add_industry_column():
    """Add industry column to companies table if it doesn't exist"""
    print("Checking if industry column exists...")
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if industry column exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='companies' AND column_name='industry';
        """)
        
        column_exists = cursor.fetchone() is not None
        
        if not column_exists:
            print("Industry column doesn't exist. Adding it...")
            cursor.execute("""
                ALTER TABLE companies 
                ADD COLUMN industry VARCHAR(50);
            """)
            
            # Add check constraint to ensure only the four industries are allowed
            cursor.execute("""
                ALTER TABLE companies 
                ADD CONSTRAINT industry_check 
                CHECK (industry IN ('Tech', 'Finance', 'Consulting', 'Healthcare', 'Unknown') OR industry IS NULL);
            """)
            print("Industry column added successfully with constraint.")
        else:
            print("Industry column already exists.")
        
        cursor.close()
        conn.close()
        return True
    
    except Exception as e:
        print(f"Error adding industry column: {str(e)}")
        return False

def update_company_industries():
    """Update all companies with industry information"""
    valid_industries = ["Tech", "Finance", "Consulting", "Healthcare"]
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
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Get all companies
        cursor.execute("SELECT id, name, industry FROM companies")
        companies = cursor.fetchall()
        
        if not companies:
            print("No companies found to update.")
            cursor.close()
            conn.close()
            return True
            
        print(f"Found {len(companies)} companies to check/update...")
        
        updated_count = 0
        for company_id, company_name, current_industry in companies:
            if current_industry in valid_industries:
                # Skip if already has a valid industry
                continue
                
            # Determine new industry
            if current_industry in industry_map:
                new_industry = industry_map[current_industry]
            else:
                # Infer industry from Google search
                new_industry = infer_company_industry(company_name)
                # Make sure it's one of our valid categories
                if new_industry not in valid_industries:
                    # Default to Tech if not in our list
                    new_industry = "Tech"
            
            # Update the company with new industry
            cursor.execute(
                "UPDATE companies SET industry = %s WHERE id = %s",
                (new_industry, company_id)
            )
            updated_count += 1
            print(f"Updated {company_name}: {current_industry or 'None'} → {new_industry}")
        
        conn.commit()
        print(f"Successfully updated {updated_count} companies.")
        
        # Verify all companies have industry set
        cursor.execute("SELECT COUNT(*) FROM companies WHERE industry IS NULL")
        null_count = cursor.fetchone()[0]
        
        if null_count > 0:
            print(f"Warning: {null_count} companies still have NULL industry value.")
            # Set default industry for remaining NULL values
            cursor.execute("UPDATE companies SET industry = 'Tech' WHERE industry IS NULL")
            conn.commit()
            print(f"Set default 'Tech' industry for {null_count} companies.")
            
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error updating company industries: {str(e)}")
        return False

if __name__ == "__main__":
    print("Starting production database update for industries...")
    
    if not DATABASE_URL:
        print("Error: DATABASE_URL environment variable not set.")
        sys.exit(1)
        
    # Step 1: Add industry column if needed
    if add_industry_column():
        # Step 2: Update all companies with industry data
        if update_company_industries():
            print("✅ Production database successfully updated with industry information.")
        else:
            print("❌ Error updating company industries.")
    else:
        print("❌ Error adding industry column.") 