"""
Script to convert existing string industry values to integer enum values in the database.
This should be run once after deploying the industry enum changes.
"""
import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv
from models import IndustryEnum

# Load environment variables
load_dotenv()

# Get database connection string from environment
DATABASE_URL = os.getenv("DATABASE_URL")

def convert_industries_to_enum():
    """Convert string industry values to integer enum values"""
    print("Converting industry string values to enum integers...")
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # First, check the column type
        cursor.execute("""
            SELECT data_type 
            FROM information_schema.columns 
            WHERE table_name='companies' AND column_name='industry';
        """)
        
        column_type = cursor.fetchone()[0]
        print(f"Current industry column type: {column_type}")
        
        # Drop any constraints that might restrict the column to string values
        try:
            cursor.execute("ALTER TABLE companies DROP CONSTRAINT IF EXISTS industry_check")
            conn.commit()
            print("Dropped existing industry_check constraint")
        except Exception as e:
            print(f"Note: Could not drop industry_check constraint: {str(e)}")
        
        # Get all companies and their current industry values
        cursor.execute("SELECT id, name, industry FROM companies")
        companies = cursor.fetchall()
        
        if not companies:
            print("No companies found to update.")
            cursor.close()
            conn.close()
            return True
            
        print(f"Found {len(companies)} companies to update...")
        
        # Mapping from string values to enum integers
        industry_mapping = {
            "Tech": IndustryEnum.TECH,
            "Finance": IndustryEnum.FINANCE, 
            "Consulting": IndustryEnum.CONSULTING,
            "Healthcare": IndustryEnum.HEALTHCARE,
            "None": IndustryEnum.TECH,  # Default for NULL or None
            "Unknown": IndustryEnum.TECH  # Default for Unknown
        }
        
        # Map for mismatched case
        case_insensitive_mapping = {
            "tech": IndustryEnum.TECH,
            "finance": IndustryEnum.FINANCE,
            "consulting": IndustryEnum.CONSULTING, 
            "healthcare": IndustryEnum.HEALTHCARE
        }
        
        updated_count = 0
        for company_id, company_name, current_industry in companies:
            # Skip if already an integer
            if isinstance(current_industry, int) and current_industry in [0, 1, 2, 3]:
                continue
                
            # Determine new industry enum value
            if current_industry is None:
                new_industry = IndustryEnum.TECH  # Default for None
            elif isinstance(current_industry, str):
                if current_industry in industry_mapping:
                    new_industry = industry_mapping[current_industry]
                elif current_industry.lower() in case_insensitive_mapping:
                    new_industry = case_insensitive_mapping[current_industry.lower()]
                else:
                    # Default to Tech for unknown values
                    new_industry = IndustryEnum.TECH
            else:
                # Unexpected type, default to Tech
                new_industry = IndustryEnum.TECH
            
            # Update the company with new industry enum value
            cursor.execute(
                "UPDATE companies SET industry = %s WHERE id = %s",
                (int(new_industry), company_id)
            )
            updated_count += 1
            print(f"Updated {company_name}: {current_industry} → {int(new_industry)}")
        
        conn.commit()
        print(f"Successfully updated {updated_count} companies to use enum values.")
        
        # Add a new constraint for the enum values
        try:
            cursor.execute("""
                ALTER TABLE companies ADD CONSTRAINT industry_check 
                CHECK (industry IN (0, 1, 2, 3) OR industry IS NULL)
            """)
            conn.commit()
            print("Added new integer-based industry_check constraint")
        except Exception as e:
            print(f"Note: Could not add new industry_check constraint: {str(e)}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error converting industry values: {str(e)}")
        return False

if __name__ == "__main__":
    print("Starting conversion of industry string values to enum integers...")
    
    if not DATABASE_URL:
        print("Error: DATABASE_URL environment variable not set.")
        sys.exit(1)
        
    if convert_industries_to_enum():
        print("✅ Industry values successfully converted to enum integers.")
    else:
        print("❌ Error converting industry values.") 