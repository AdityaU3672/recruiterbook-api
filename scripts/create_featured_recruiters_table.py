"""
Script to create the featured_recruiters table in the database.
This will allow us to persistently store which recruiters should be featured.
"""
import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database connection string from environment
DATABASE_URL = os.getenv("DATABASE_URL")

def create_featured_recruiters_table():
    """Create the featured_recruiters table if it doesn't exist"""
    print("Creating featured_recruiters table...")
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if table already exists
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name='featured_recruiters';
        """)
        
        table_exists = cursor.fetchone() is not None
        
        if not table_exists:
            print("featured_recruiters table doesn't exist. Creating it...")
            cursor.execute("""
                CREATE TABLE featured_recruiters (
                    id SERIAL PRIMARY KEY,
                    recruiter_id VARCHAR NOT NULL,
                    display_order INTEGER NOT NULL,
                    FOREIGN KEY (recruiter_id) REFERENCES recruiters (id) ON DELETE CASCADE
                );
            """)
            print("featured_recruiters table created successfully.")
        else:
            print("featured_recruiters table already exists.")
        
        cursor.close()
        conn.close()
        return True
    
    except Exception as e:
        print(f"Error creating featured_recruiters table: {str(e)}")
        return False

if __name__ == "__main__":
    print("Starting featured recruiters table creation...")
    
    if not DATABASE_URL:
        print("Error: DATABASE_URL environment variable not set.")
        sys.exit(1)
        
    if create_featured_recruiters_table():
        print("✅ Featured recruiters table creation completed successfully.")
    else:
        print("❌ Error creating featured recruiters table.") 