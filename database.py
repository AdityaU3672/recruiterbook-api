from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

# Get database URL from environment variable
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    # Railway provides URLs starting with postgres://, but SQLAlchemy requires postgresql://
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# If no DATABASE_URL is set, use local development database
if not DATABASE_URL:
    DATABASE_URL = "postgresql://adityauchil@localhost:5432/recruiterbook"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def add_created_at_column():
    """Add created_at and updated_at columns to reviews table if they don't exist."""
    with engine.connect() as connection:
        # Check if columns exist
        result = connection.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'reviews' 
            AND column_name IN ('created_at', 'updated_at')
        """))
        
        existing_columns = {row[0] for row in result}
        
        if 'created_at' not in existing_columns:
            # Add created_at column if it doesn't exist
            connection.execute(text("""
                ALTER TABLE reviews 
                ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """))
        
        if 'updated_at' not in existing_columns:
            # Add updated_at column if it doesn't exist
            connection.execute(text("""
                ALTER TABLE reviews 
                ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """))
        
        connection.commit()

# Call this function when the application starts
add_created_at_column()