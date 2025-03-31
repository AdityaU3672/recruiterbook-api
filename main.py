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
def create_review(
    review: ReviewCreate, 
    db: Session = Depends(get_db),
    request: Request = None,
    current_user: dict = None
):
    try:
        # Debug logging
        if request:
            print(f"Review creation - Headers: {dict(request.headers)}")
            print(f"Review creation - Cookies: {dict(request.cookies)}")
        
        # Try to get current user from cookie if not provided directly
        if current_user is None:
            try:
                current_user = get_current_user_from_cookie(request, next(get_db()))
                print(f"Retrieved current user from cookie: {current_user}")
            except Exception as e:
                print(f"Failed to get user from cookie: {str(e)}")
        
        # Set the user_id from the authenticated user if it wasn't provided in the request
        review_data = review.dict()
        if not review_data.get("user_id") and current_user:
            print(f"Using user_id from cookie: {current_user.get('id')}")
            review_data["user_id"] = current_user.get("id")
        
        # Ensure we have a user_id
        if not review_data.get("user_id"):
            raise HTTPException(status_code=400, detail="No user_id provided and not authenticated")
            
        review_obj = ReviewCreate(**review_data)
        
        new_review = post_review(db, review_obj)
        return new_review
    except HTTPException as e:
        print(f"Review creation HTTPException: {e.detail}")
        raise e
    except Exception as e:
        print(f"Review creation exception: {str(e)}")
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
def upvote(
    review_id: int, 
    current_user: dict = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)
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
def downvote(
    review_id: int,
    current_user: dict = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)
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
def edit_review(
    review_id: int,
    review_data: ReviewUpdate,
    current_user: dict = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)
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
def remove_review(
    review_id: int,
    current_user: dict = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)
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

