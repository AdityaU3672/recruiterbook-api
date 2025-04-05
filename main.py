from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
from crud import downvote_review, get_or_create_user, get_or_create_recruiter, find_recruiters, get_reviews_by_company, post_review, get_reviews, get_companies, get_recruiter_by_id, delete_company_by_name, get_all_reviews, upvote_review, get_reviews_by_user, get_user_helpfulness_score, update_review, delete_review, get_all_recruiters
from schemas import UserCreate, UserResponse, RecruiterCreate, RecruiterResponse, ReviewCreate, ReviewResponse, CompanyResponse, HelpfulnessScore, ReviewUpdate
from models import Review
from typing import List
import uvicorn
import os
from auth import get_current_user_from_cookie, router as auth_router
from starlette.middleware.sessions import SessionMiddleware

# Import slowapi for rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080)

# Disable docs in production by checking environment
is_prod = os.getenv("ENVIRONMENT", "dev").lower() == "production"

# Initialize rate limiter with default key function (IP-based)
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    docs_url=None if is_prod else "/docs",
    redoc_url=None if is_prod else "/redoc",
    openapi_url=None if is_prod else "/openapi.json"
)

# Add rate limiter to the app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://recruiter-rank.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept", "Origin", "X-Requested-With"],
    expose_headers=["Set-Cookie"],
    max_age=86400,  # 24 hours
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

# Function to get user ID for rate limiting (used for authenticated endpoints)
def get_user_id_for_limiter(request: Request):
    try:
        user = get_current_user_from_cookie(request)
        return str(user.get("id"))
    except:
        # Fall back to IP address if user is not authenticated
        return get_remote_address(request)

app.include_router(auth_router, prefix="/auth", tags=["auth"])

# User Authentication (IP-based rate limiting since it's before authentication)
@app.post("/user/", response_model=UserResponse)
@limiter.limit("20/minute")
def create_or_get_user(user: UserCreate, db: Session = Depends(get_db), request: Request = None):
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


# Create Recruiter - Add rate limiting per user
@app.post("/recruiter/", response_model=RecruiterResponse)
@limiter.limit("5/minute", key_func=get_user_id_for_limiter)
def create_recruiter(recruiter: RecruiterCreate, db: Session = Depends(get_db), request: Request = None):
    return get_or_create_recruiter(db, recruiter)

# Post Review
@app.post("/review/", response_model=ReviewResponse)
@limiter.limit("10/minute", key_func=get_user_id_for_limiter)
def create_review(
    review: ReviewCreate, 
    current_user: dict = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db),
    request: Request = None
):
    try:
        # Debug logging for troubleshooting
        if request:
            print(f"Review creation - Headers: {dict(request.headers)}")
            print(f"Review creation - Cookies: {dict(request.cookies)}")
        print(f"Review creation - Current user: {current_user}")
            
        # Set the user_id from the authenticated user
        review_data = review.dict()
        review_data["user_id"] = current_user.get("id")
        review_obj = ReviewCreate(**review_data)
        
        new_review = post_review(db, review_obj)
        return new_review
    except HTTPException as e:
        print(f"Review creation failed with HTTP error: {e.detail}")
        raise e
    except Exception as e:
        print(f"Review creation failed with error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Get Reviews
@app.get("/reviews/", response_model=List[ReviewResponse])
def get_reviews_for_recruiter(recruiter_id: str, db: Session = Depends(get_db)):
    return get_reviews(db, recruiter_id)

# Get All Companies
@app.get("/companies/", response_model=List[CompanyResponse])
def get_all_companies(db: Session = Depends(get_db)):
    return get_companies(db)

@app.get("/recruiters/", response_model=List[RecruiterResponse])
def get_all_recruiters_endpoint(db: Session = Depends(get_db)):
    return get_all_recruiters(db)

@app.delete("/company/{company_name}")
@limiter.limit("10/minute", key_func=get_user_id_for_limiter)
def delete_company(company_name: str, db: Session = Depends(get_db), request: Request = None):
    company = delete_company_by_name(db, company_name)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return {"message": f"Company '{company_name}' has been deleted successfully"}

@app.get("/allReviews/", response_model=List[ReviewResponse])
def get_all_reviews_endpoint(db: Session = Depends(get_db)):
    reviews = get_all_reviews(db)
    return reviews

@app.post("/review/upvote/{review_id}")
@limiter.limit("30/minute", key_func=get_user_id_for_limiter)
def upvote(
    review_id: int, 
    current_user: dict = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db),
    request: Request = None
):
    try:
        original_review = db.query(Review).filter(Review.id == review_id).first()
        if not original_review:
            raise HTTPException(status_code=404, detail="Review not found")
        
        original_upvotes = original_review.upvotes
        
        user_id = current_user.get("id")
        review = upvote_review(db, review_id, user_id)
        
        # Determine if an upvote was added or removed
        if review.upvotes > original_upvotes:
            return {"message": "Upvote added", "upvotes": review.upvotes}
        else:
            return {"message": "Upvote removed", "upvotes": review.upvotes}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/review/downvote/{review_id}")
@limiter.limit("30/minute", key_func=get_user_id_for_limiter)
def downvote(
    review_id: int,
    current_user: dict = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db),
    request: Request = None
):
    try:
        original_review = db.query(Review).filter(Review.id == review_id).first()
        if not original_review:
            raise HTTPException(status_code=404, detail="Review not found")
        
        original_downvotes = original_review.downvotes
        
        user_id = current_user.get("id")
        review = downvote_review(db, review_id, user_id)
        
        # Determine if a downvote was added or removed
        if review.downvotes > original_downvotes:
            return {"message": "Downvote added", "downvotes": review.downvotes}
        else:
            return {"message": "Downvote removed", "downvotes": review.downvotes}
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

@app.put("/review/{review_id}/", response_model=ReviewResponse)
@limiter.limit("15/minute", key_func=get_user_id_for_limiter)
def edit_review(
    review_id: int,
    review_data: ReviewUpdate,
    current_user: dict = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db),
    request: Request = None
):
    """
    Edit a review. Only the review author can edit their own review.
    """
    try:
        user_id = current_user.get("id")
        updated_review = update_review(db, review_id, user_id, review_data)
        return updated_review
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/review/{review_id}/")
@limiter.limit("10/minute", key_func=get_user_id_for_limiter)
def remove_review(
    review_id: int,
    current_user: dict = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db),
    request: Request = None
):
    """
    Delete a review. Only the review author can delete their own review.
    """
    try:
        user_id = current_user.get("id")
        return delete_review(db, review_id, user_id)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

