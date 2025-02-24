from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
from crud import get_or_create_user, get_or_create_recruiter, find_recruiters, post_review, get_reviews, get_companies
from schemas import UserCreate, UserResponse, RecruiterCreate, RecruiterResponse, ReviewCreate, ReviewResponse, CompanyResponse
from typing import List

app = FastAPI()

#Fucking CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Change this to allow specific origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

# Initialize DB
Base.metadata.create_all(bind=engine)

# Dependency: Get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# User Authentication
@app.post("/user/", response_model=UserResponse)
def create_or_get_user(user: UserCreate, db: Session = Depends(get_db)):
    return get_or_create_user(db, user)

# Find Recruiter
@app.get("/recruiter/", response_model=List[RecruiterResponse])
def find_recruiter(fullName: str, company: str = None, db: Session = Depends(get_db)):
    return find_recruiters(db, fullName, company)

# Create Recruiter
@app.post("/recruiter/", response_model=RecruiterResponse)
def create_recruiter(recruiter: RecruiterCreate, db: Session = Depends(get_db)):
    return get_or_create_recruiter(db, recruiter)

# Post Review
@app.post("/review/")
def create_review(review: ReviewCreate, db: Session = Depends(get_db)):
    status = post_review(db, review)
    return {"status": status}

# Get Reviews
@app.get("/reviews/", response_model=List[ReviewResponse])
def get_reviews_for_recruiter(recruiter_id: str, db: Session = Depends(get_db)):
    return get_reviews(db, recruiter_id)

# Get All Companies
@app.get("/companies/", response_model=List[CompanyResponse])
def get_all_companies(db: Session = Depends(get_db)):
    return get_companies(db)
