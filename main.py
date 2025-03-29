from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
from crud import downvote_review, get_or_create_user, get_or_create_recruiter, find_recruiters, get_reviews_by_company, post_review, get_reviews, get_companies, get_recruiter_by_id, delete_company_by_name, get_all_reviews, upvote_review, get_reviews_by_user, get_user_helpfulness_score
from schemas import UserCreate, UserResponse, RecruiterCreate, RecruiterResponse, ReviewCreate, ReviewResponse, CompanyResponse, HelpfulnessScore
from typing import List
import uvicorn
from auth import get_current_user_from_cookie, router as auth_router
from starlette.middleware.sessions import SessionMiddleware

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://recruiterbook.0x0.lat"],  # Add your production frontend URL when ready
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SessionMiddleware, secret_key="YOUR_RANDOM_SECRET")

# Initialize DB
Base.metadata.create_all(bind=engine)

# Dependency: Get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app.include_router(auth_router, prefix="/auth", tags=["auth"])

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

@app.get("/reviews/company/{company_name}", response_model=List[ReviewResponse])
def get_reviews_for_company(company_name: str, db: Session = Depends(get_db)):
    reviews = get_reviews_by_company(db, company_name)
    if not reviews:
        raise HTTPException(status_code=404, detail="No reviews found for this company")
    return reviews


# Create Recruiter
@app.post("/recruiter/", response_model=RecruiterResponse)
def create_recruiter(recruiter: RecruiterCreate, db: Session = Depends(get_db)):
    return get_or_create_recruiter(db, recruiter)

# Post Review
@app.post("/review/", response_model=ReviewResponse)
def create_review(review: ReviewCreate, db: Session = Depends(get_db)):
    try:
        new_review = post_review(db, review)
        return new_review
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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

@app.get("/allReviews/", response_model=List[ReviewResponse])
def get_all_reviews_endpoint(db: Session = Depends(get_db)):
    reviews = get_all_reviews(db)
    return reviews

@app.post("/review/upvote/{review_id}")
def upvote(review_id: int, user_id: str, db: Session = Depends(get_db)):
    try:
        review = upvote_review(db, review_id, user_id)
        if not review:
            raise HTTPException(status_code=404, detail="Review not found")
        return {"message": "Upvote added", "upvotes": review.upvotes}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/review/downvote/{review_id}")
def downvote(review_id: int, user_id: str, db: Session = Depends(get_db)):
    try:
        review = downvote_review(db, review_id, user_id)
        if not review:
            raise HTTPException(status_code=404, detail="Review not found")
        return {"message": "Downvote added", "downvotes": review.downvotes}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/profile/reviews/", response_model=List[ReviewResponse])
def get_user_reviews(
    current_user: dict = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)
):
    """
    Retrieve all reviews written by the currently authenticated user.
    """
    user_id = current_user.get("id")
    return get_reviews_by_user(db, user_id)

@app.get("/profile/helpfulness/", response_model=HelpfulnessScore)
def get_user_helpfulness(
    current_user: dict = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)
):
    """
    Get the helpfulness score for the currently authenticated user.
    Returns total upvotes, downvotes, and the overall helpfulness score.
    """
    user_id = current_user.get("id")
    return get_user_helpfulness_score(db, user_id)

