"""
Script to drop the featured_recruiters table from the database since it's no longer needed.
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

def drop_featured_recruiters_table():
    """Drop the featured_recruiters table if it exists"""
    print("Dropping featured_recruiters table...")
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name='featured_recruiters';
        """)
        
        table_exists = cursor.fetchone() is not None
        
        if table_exists:
            print("featured_recruiters table exists. Dropping it...")
            cursor.execute("DROP TABLE featured_recruiters;")
            print("featured_recruiters table dropped successfully.")
        else:
            print("featured_recruiters table doesn't exist. Nothing to drop.")
        
        cursor.close()
        conn.close()
        return True
    
    except Exception as e:
        print(f"Error dropping featured_recruiters table: {str(e)}")
        return False

if __name__ == "__main__":
    print("Starting to drop featured recruiters table...")
    
    if not DATABASE_URL:
        print("Error: DATABASE_URL environment variable not set.")
        sys.exit(1)
        
    if drop_featured_recruiters_table():
        print("✅ Featured recruiters table dropped successfully.")
    else:
        print("❌ Error dropping featured recruiters table.") 