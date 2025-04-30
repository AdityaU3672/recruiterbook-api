from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
import sys

# Load environment variables
load_dotenv()

# Get database URL from environment variable
DATABASE_URL = os.getenv("DATABASE_URL")

# Safety check: Ensure we're targeting production
if not DATABASE_URL or "localhost" in DATABASE_URL:
    print("ERROR: This script is intended for production databases only.")
    print("Current DATABASE_URL appears to be a local environment.")
    sys.exit(1)

# Convert postgres:// to postgresql:// if needed
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Fix Railway internal hostname for external access
if "postgres.railway.internal" in DATABASE_URL:
    # Replace internal hostname with external hostname
    DATABASE_URL = DATABASE_URL.replace("postgres.railway.internal:5432", "interchange.proxy.rlwy.net:46586")
    print(f"Converted internal URL to external URL: {DATABASE_URL}")

# Confirm with the user
print(f"WARNING: This will DELETE ALL DATA from the database at:")
print(f"{DATABASE_URL}")
confirmation = input("Type 'DELETE ALL DATA' to confirm: ")

if confirmation != "DELETE ALL DATA":
    print("Operation canceled.")
    sys.exit(0)

# Set up database connection
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
session = SessionLocal()

try:
    # Start transaction
    print("Starting database cleanup...")
    
    # Delete data in reverse order of dependencies
    print("Deleting review votes...")
    session.execute(text("TRUNCATE TABLE review_votes CASCADE;"))
    
    print("Deleting reviews...")
    session.execute(text("TRUNCATE TABLE reviews CASCADE;"))
    
    print("Deleting recruiters...")
    session.execute(text("TRUNCATE TABLE recruiters CASCADE;"))
    
    print("Deleting companies...")
    session.execute(text("TRUNCATE TABLE companies CASCADE;"))
    
    print("Deleting users...")
    session.execute(text("TRUNCATE TABLE users CASCADE;"))
    
    # Commit the transaction
    session.commit()
    print("All production data has been successfully deleted.")
    
except Exception as e:
    # Rollback in case of error
    session.rollback()
    print(f"An error occurred: {e}")
    sys.exit(1)
    
finally:
    # Close the session
    session.close() 