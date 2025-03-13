from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
from crud import get_or_create_user, get_or_create_recruiter, find_recruiters, post_review, get_reviews, get_companies, get_recruiter_by_id, delete_company_by_name, get_all_reviews
from schemas import UserCreate, UserResponse, RecruiterCreate, RecruiterResponse, ReviewCreate, ReviewResponse, CompanyResponse
from typing import List
import uvicorn

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change this to allow specific origins
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

@app.get("/recruiter/{recruiter_id}", response_model=RecruiterResponse)
def get_recruiter(recruiter_id: str, db: Session = Depends(get_db)):
    recruiter = get_recruiter_by_id(db, recruiter_id)
    if not recruiter:
        raise HTTPException(status_code=404, detail="Recruiter not found")
    return recruiter


# Create Recruiter
@app.post("/recruiter/", response_model=RecruiterResponse)
def create_recruiter(recruiter: RecruiterCreate, db: Session = Depends(get_db)):
    return get_or_create_recruiter(db, recruiter)

# Post Review
@app.post("/review/")
def create_review(review: ReviewCreate, db: Session = Depends(get_db)):
    status = post_review(db, review)
    if status == 3:
        raise HTTPException(status_code=403, detail="Profanity detected in review.")
    
    return {"status": status}

# Get Reviews
@app.get("/reviews/", response_model=List[ReviewResponse])
def get_reviews_for_recruiter(recruiter_id: str, db: Session = Depends(get_db)):
    return get_reviews(db, recruiter_id)

# Get All Companies
@app.get("/companies/", response_model=List[CompanyResponse])
def get_all_companies(db: Session = Depends(get_db)):
    return get_companies(db)

@app.delete("/company/{company_name}")
def delete_company(company_name: str, db: Session = Depends(get_db)):
    company = delete_company_by_name(db, company_name)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return {"message": f"Company '{company_name}' has been deleted successfully"}

@app.get("/allReviews", response_model=List[ReviewResponse])
def get_all_reviews_endpoint(db: Session = Depends(get_db)):
    reviews = get_all_reviews(db)
    return reviews
