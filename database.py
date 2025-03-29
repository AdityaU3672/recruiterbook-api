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
        try:
            # Check if columns exist and their current type
            result = connection.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'reviews' 
                AND column_name IN ('created_at', 'updated_at')
            """))
            
            existing_columns = {row[0]: row[1] for row in result}
            
            if 'created_at' not in existing_columns:
                # Add created_at column if it doesn't exist
                connection.execute(text("""
                    ALTER TABLE reviews 
                    ADD COLUMN created_at INTEGER
                """))
                # Set default value for existing records
                connection.execute(text("""
                    UPDATE reviews 
                    SET created_at = EXTRACT(EPOCH FROM CURRENT_TIMESTAMP)::INTEGER 
                    WHERE created_at IS NULL
                """))
                # Add default constraint
                connection.execute(text("""
                    ALTER TABLE reviews 
                    ALTER COLUMN created_at SET DEFAULT EXTRACT(EPOCH FROM CURRENT_TIMESTAMP)::INTEGER
                """))
            elif existing_columns['created_at'] == 'timestamp':
                # Convert existing timestamp to Unix timestamp
                connection.execute(text("""
                    ALTER TABLE reviews 
                    ALTER COLUMN created_at TYPE INTEGER 
                    USING EXTRACT(EPOCH FROM created_at)::INTEGER
                """))
            
            if 'updated_at' not in existing_columns:
                # Add updated_at column if it doesn't exist
                connection.execute(text("""
                    ALTER TABLE reviews 
                    ADD COLUMN updated_at INTEGER
                """))
                # Set default value for existing records
                connection.execute(text("""
                    UPDATE reviews 
                    SET updated_at = EXTRACT(EPOCH FROM CURRENT_TIMESTAMP)::INTEGER 
                    WHERE updated_at IS NULL
                """))
                # Add default constraint
                connection.execute(text("""
                    ALTER TABLE reviews 
                    ALTER COLUMN updated_at SET DEFAULT EXTRACT(EPOCH FROM CURRENT_TIMESTAMP)::INTEGER
                """))
            elif existing_columns['updated_at'] == 'timestamp':
                # Convert existing timestamp to Unix timestamp
                connection.execute(text("""
                    ALTER TABLE reviews 
                    ALTER COLUMN updated_at TYPE INTEGER 
                    USING EXTRACT(EPOCH FROM updated_at)::INTEGER
                """))
            
            connection.commit()
        except Exception as e:
            print(f"Error during migration: {str(e)}")
            connection.rollback()
            raise

# Initialize database and run migrations
def init_db():
    Base.metadata.create_all(bind=engine)
    add_created_at_column()

# Run initialization when module is imported
init_db()