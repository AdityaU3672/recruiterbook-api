from fastapi import FastAPI, Depends, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
from crud import downvote_review, get_or_create_user, get_or_create_recruiter, find_recruiters, get_reviews_by_company, post_review, get_reviews, get_companies, get_recruiter_by_id, delete_company_by_name, get_all_reviews, upvote_review, get_reviews_by_user, get_user_helpfulness_score, update_review, delete_review, get_all_recruiters, get_reviews_by_industry, update_all_company_industries, get_all_industries, get_companies_by_industry, get_featured_recruiters, get_editors_pick_reviews
from schemas import UserCreate, UserResponse, RecruiterCreate, RecruiterResponse, ReviewCreate, ReviewResponse, CompanyResponse, HelpfulnessScore, ReviewUpdate, IndustryResponse
from models import Review, IndustryEnum
from typing import List
import uvicorn
import os
from auth import get_current_user_from_cookie, router as auth_router
from starlette.middleware.sessions import SessionMiddleware
from cache import setup_cache, invalidate_cache_keys, invalidate_all_cache
from fastapi_cache.decorator import cache

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
    allow_origins=["http://localhost:3000", "https://recruiter-rank.com", "https://preview.recruiter-rank.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept", "Origin", "X-Requested-With"],
    expose_headers=["Set-Cookie"],
    max_age=86400,  # 24 hours
)

app.add_middleware(SessionMiddleware, secret_key="YOUR_RANDOM_SECRET")

# Initialize DB
Base.metadata.create_all(bind=engine)

# Setup cache on application startup
@app.on_event("startup")
async def startup_event():
    await setup_cache()

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
def create_or_get_user(user: UserCreate, db: Session = Depends(get_db), request: Request = None, background_tasks: BackgroundTasks = None):
    result = get_or_create_user(db, user)
    # Invalidate any cached user data
    if background_tasks:
        background_tasks.add_task(invalidate_cache_keys, ["*user*"])
    return result

# Find Recruiter
@app.get("/recruiter/", response_model=List[RecruiterResponse])
@cache(expire=600)  # Cache for 10 minutes
def find_recruiter(fullName: str, company: str = None, db: Session = Depends(get_db)):
    return find_recruiters(db, fullName, company)

@app.get("/recruiter/{recruiter_id}", response_model=RecruiterResponse)
@cache(expire=1800)  # Cache for 30 minutes
def get_recruiter(recruiter_id: str, db: Session = Depends(get_db)):
    recruiter = get_recruiter_by_id(db, recruiter_id)
    if not recruiter:
        raise HTTPException(status_code=404, detail="Recruiter not found")
    return recruiter

@app.get("/reviews/company/{company_name}", response_model=List[ReviewResponse])
@cache(expire=1800)  # Cache for 30 minutes
def get_reviews_for_company(company_name: str, db: Session = Depends(get_db)):
    reviews = get_reviews_by_company(db, company_name)
    if not reviews:
        raise HTTPException(status_code=404, detail="No reviews found for this company")
    return reviews

@app.get("/reviews/industry/{industry_id}", response_model=List[ReviewResponse])
@cache(expire=3600)  # Cache for 1 hour
def get_reviews_by_industry_endpoint(industry_id: int, db: Session = Depends(get_db)):
    """
    Retrieve all reviews for recruiters at companies in a specific industry.
    Industry ID is an integer:
    0 = Tech, 1 = Finance, 2 = Consulting, 3 = Healthcare
    """
    reviews = get_reviews_by_industry(db, industry_id)
    return reviews

# Create Recruiter - Add rate limiting per user
@app.post("/recruiter/", response_model=RecruiterResponse)
@limiter.limit("5/minute", key_func=get_user_id_for_limiter)
def create_recruiter(
    recruiter: RecruiterCreate, 
    db: Session = Depends(get_db), 
    request: Request = None,
    background_tasks: BackgroundTasks = None
):
    result = get_or_create_recruiter(db, recruiter)
    # Invalidate related caches
    if background_tasks:
        background_tasks.add_task(invalidate_cache_keys, [
            "*recruiter*", 
            f"*company*{result.company.name}*"
        ])
    return result

# Post Review
@app.post("/review/", response_model=ReviewResponse)
@limiter.limit("10/minute", key_func=get_user_id_for_limiter)
def create_review(
    review: ReviewCreate, 
    current_user: dict = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db),
    request: Request = None,
    background_tasks: BackgroundTasks = None
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
        
        # Invalidate related caches
        if background_tasks:
            background_tasks.add_task(invalidate_cache_keys, [
                f"*recruiter*{new_review.recruiter_id}*",
                f"*reviews*",
                f"*allReviews*"
            ])
        
        return new_review
    except HTTPException as e:
        print(f"Review creation failed with HTTP error: {e.detail}")
        raise e
    except Exception as e:
        print(f"Review creation failed with error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Get Reviews
@app.get("/reviews/", response_model=List[ReviewResponse])
@cache(expire=1800)  # Cache for 30 minutes
def get_reviews_for_recruiter(recruiter_id: str, db: Session = Depends(get_db)):
    return get_reviews(db, recruiter_id)

# Get All Companies
@app.get("/companies/", response_model=List[CompanyResponse])
@cache(expire=3600)  # Cache for 1 hour
def get_all_companies(db: Session = Depends(get_db)):
    return get_companies(db)

@app.get("/recruiters/", response_model=List[RecruiterResponse])
@cache(expire=3600)  # Cache for 1 hour
def get_all_recruiters_endpoint(db: Session = Depends(get_db)):
    return get_all_recruiters(db)

@app.get("/recruiters/featured/", response_model=List[RecruiterResponse])
@cache(expire=7200)  # Cache for 2 hours
def get_featured_recruiters_endpoint(db: Session = Depends(get_db)):
    """
    Returns recruiters that have been added by either Aditya Uchil or Rishi Papani.
    These are considered featured recruiters in the system.
    """
    return get_featured_recruiters(db)

@app.get("/editors-picks/", response_model=List[ReviewResponse])
@cache(expire=7200)  # Cache for 2 hours
def get_editors_pick_reviews_endpoint(db: Session = Depends(get_db)):
    """
    Returns reviews written by Aditya Uchil or Rishi Papani.
    These are considered editor's picks.
    """
    return get_editors_pick_reviews(db)

@app.delete("/company/{company_name}")
@limiter.limit("10/minute", key_func=get_user_id_for_limiter)
def delete_company(
    company_name: str, 
    db: Session = Depends(get_db), 
    request: Request = None,
    background_tasks: BackgroundTasks = None
):
    company = delete_company_by_name(db, company_name)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Invalidate all company-related caches
    if background_tasks:
        background_tasks.add_task(invalidate_cache_keys, [
            "*company*",
            "*recruiter*",
            "*review*"
        ])
    
    return {"message": f"Company '{company_name}' has been deleted successfully"}

@app.get("/allReviews/", response_model=List[ReviewResponse])
@cache(expire=1800)  # Cache for 30 minutes
def get_all_reviews_endpoint(db: Session = Depends(get_db)):
    reviews = get_all_reviews(db)
    return reviews

@app.post("/review/upvote/{review_id}")
@limiter.limit("30/minute", key_func=get_user_id_for_limiter)
def upvote(
    review_id: int, 
    current_user: dict = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db),
    request: Request = None,
    background_tasks: BackgroundTasks = None
):
    try:
        original_review = db.query(Review).filter(Review.id == review_id).first()
        if not original_review:
            raise HTTPException(status_code=404, detail="Review not found")
        
        original_upvotes = original_review.upvotes
        
        user_id = current_user.get("id")
        review = upvote_review(db, review_id, user_id)
        
        # Invalidate specific review cache
        if background_tasks:
            background_tasks.add_task(invalidate_cache_keys, [
                f"*review*{review_id}*",
                f"*reviews*",
                f"*allReviews*"
            ])
        
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
    request: Request = None,
    background_tasks: BackgroundTasks = None
):
    try:
        original_review = db.query(Review).filter(Review.id == review_id).first()
        if not original_review:
            raise HTTPException(status_code=404, detail="Review not found")
        
        original_downvotes = original_review.downvotes
        
        user_id = current_user.get("id")
        review = downvote_review(db, review_id, user_id)
        
        # Invalidate specific review cache
        if background_tasks:
            background_tasks.add_task(invalidate_cache_keys, [
                f"*review*{review_id}*",
                f"*reviews*",
                f"*allReviews*"
            ])
        
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
    request: Request = None,
    background_tasks: BackgroundTasks = None
):
    # Get the current review
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    # Verify the user owns this review
    if review.user_id != current_user.get("id"):
        raise HTTPException(status_code=403, detail="Not authorized to edit this review")
    
    # Update the review
    updated_review = update_review(db, review_id, review_data)
    
    # Invalidate related caches
    if background_tasks:
        background_tasks.add_task(invalidate_cache_keys, [
            f"*review*{review_id}*",
            f"*recruiter*{review.recruiter_id}*",
            f"*reviews*",
            f"*allReviews*"
        ])
    
    return updated_review

@app.delete("/review/{review_id}/")
@limiter.limit("10/minute", key_func=get_user_id_for_limiter)
def remove_review(
    review_id: int,
    current_user: dict = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db),
    request: Request = None,
    background_tasks: BackgroundTasks = None
):
    # Get the current review
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    # Verify the user owns this review
    if review.user_id != current_user.get("id"):
        raise HTTPException(status_code=403, detail="Not authorized to delete this review")
    
    recruiter_id = review.recruiter_id
    
    # Delete the review
    success = delete_review(db, review_id)
    
    # Invalidate related caches
    if background_tasks and success:
        background_tasks.add_task(invalidate_cache_keys, [
            f"*review*{review_id}*",
            f"*recruiter*{recruiter_id}*",
            f"*reviews*", 
            f"*allReviews*"
        ])
    
    if success:
        return {"message": "Review deleted successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to delete review")

@app.post("/admin/update-industries")
@limiter.limit("1/hour")
def update_industries(
    force_update: bool = False,
    db: Session = Depends(get_db),
    request: Request = None,
    background_tasks: BackgroundTasks = None
):
    """
    Admin endpoint to update industries for companies.
    If force_update is True, all companies will be updated regardless of whether they already have an industry set.
    If force_update is False, only companies without an industry set will be updated.
    """
    from google import infer_company_industry
    
    result = update_all_company_industries(db, force_update=force_update)
    
    # Invalidate company and industry-related caches
    if background_tasks:
        background_tasks.add_task(invalidate_cache_keys, [
            "*company*",
            "*industry*",
            "*reviews*industry*"
        ])
    
    return result

@app.post("/admin/update-all-industries")
def update_all_industries_endpoint(
    db: Session = Depends(get_db)
):
    """
    Special endpoint to update all companies in the database to use only
    the four industry categories: 0 = Tech, 1 = Finance, 2 = Consulting, 3 = Healthcare
    """
    result = update_all_company_industries(db, force_update=True)
    return result

@app.get("/industries/", response_model=List[IndustryResponse])
def get_industries(db: Session = Depends(get_db)):
    """
    Returns a list of all industries with their IDs and names.
    """
    return get_all_industries(db)

@app.get("/companies/industry/{industry_id}", response_model=List[CompanyResponse])
def get_companies_by_industry_endpoint(industry_id: int, db: Session = Depends(get_db)):
    """
    Retrieve all companies belonging to a specific industry.
    Industry ID is an integer:
    0 = Tech, 1 = Finance, 2 = Consulting, 3 = Healthcare
    """
    companies = get_companies_by_industry(db, industry_id)
    return companies

