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

# Configure the engine with optimized connection pooling settings
engine = create_engine(
    DATABASE_URL, 
    pool_size=20,               # Maximum number of connections in the pool
    max_overflow=10,            # Allow 10 connections beyond pool_size when needed
    pool_timeout=30,            # Timeout waiting for a connection from pool (seconds)
    pool_recycle=1800,          # Recycle connections after 30 minutes to avoid stale connections
    pool_pre_ping=True          # Verify connection is valid before using it (prevents using broken connections)
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Initialize database
def init_db():
    Base.metadata.create_all(bind=engine)

# Run initialization when module is imported
init_db()