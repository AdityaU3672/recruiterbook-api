"""
Script to convert the industry column in the companies table from string to integer.
This should be run after the values have been converted to integers in string form.
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

def convert_column_type():
    """Convert industry column type from string to integer"""
    print("Converting industry column type from string to integer...")
    
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
        
        if column_type.lower() == 'integer':
            print("Column is already an integer type. No conversion needed.")
            return True
        
        # Drop any existing constraint
        try:
            cursor.execute("ALTER TABLE companies DROP CONSTRAINT IF EXISTS industry_check")
            conn.commit()
            print("Dropped existing industry_check constraint")
        except Exception as e:
            print(f"Note: Could not drop industry_check constraint: {str(e)}")
        
        # Alter the column type to integer
        # First, create a temporary column
        cursor.execute("ALTER TABLE companies ADD COLUMN industry_int INTEGER")
        print("Added temporary industry_int column")
        
        # Update the temporary column with integer values
        cursor.execute("UPDATE companies SET industry_int = industry::INTEGER")
        print("Populated temporary column with integer values")
        
        # Drop the original column
        cursor.execute("ALTER TABLE companies DROP COLUMN industry")
        print("Dropped original industry column")
        
        # Rename the temporary column to the original name
        cursor.execute("ALTER TABLE companies RENAME COLUMN industry_int TO industry")
        print("Renamed temporary column to industry")
        
        # Add a constraint for valid values
        cursor.execute("""
            ALTER TABLE companies ADD CONSTRAINT industry_check 
            CHECK (industry IN (0, 1, 2, 3) OR industry IS NULL)
        """)
        print("Added new industry_check constraint")
        
        conn.commit()
        
        # Verify the new column type
        cursor.execute("""
            SELECT data_type 
            FROM information_schema.columns 
            WHERE table_name='companies' AND column_name='industry';
        """)
        
        new_column_type = cursor.fetchone()[0]
        print(f"New industry column type: {new_column_type}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error converting column type: {str(e)}")
        return False

if __name__ == "__main__":
    print("Starting conversion of industry column type...")
    
    if not DATABASE_URL:
        print("Error: DATABASE_URL environment variable not set.")
        sys.exit(1)
        
    if convert_column_type():
        print("✅ Industry column type successfully converted to integer.")
    else:
        print("❌ Error converting industry column type.") 