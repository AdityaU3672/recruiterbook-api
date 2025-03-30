from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
from crud import downvote_review, get_or_create_user, get_or_create_recruiter, find_recruiters, get_reviews_by_company, post_review, get_reviews, get_companies, get_recruiter_by_id, delete_company_by_name, get_all_reviews, upvote_review, get_reviews_by_user, get_user_helpfulness_score, update_review, delete_review
from schemas import UserCreate, UserResponse, RecruiterCreate, RecruiterResponse, ReviewCreate, ReviewResponse, CompanyResponse, HelpfulnessScore, ReviewUpdate
from typing import List, Union
import uvicorn
from auth import get_current_user_from_cookie, get_current_user_from_token, router as auth_router
from starlette.middleware.sessions import SessionMiddleware
import os
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
from models import Review
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080)

# Set up HTTP Basic Auth
security = HTTPBasic()

def get_docs_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    # Get credentials from environment variables or use defaults in development
    correct_username = os.getenv("DOCS_USERNAME", "recruiterbook")
    correct_password = os.getenv("DOCS_PASSWORD", "docspassword")
    
    is_correct_username = secrets.compare_digest(credentials.username, correct_username)
    is_correct_password = secrets.compare_digest(credentials.password, correct_password)
    
    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    return credentials.username

# Helper function to get user from either cookie or token
def get_current_user(
    cookie_user = Depends(get_current_user_from_cookie, use_cache=False),
    token_user = Depends(get_current_user_from_token, use_cache=False)
):
    """
    Tries to get the user from either cookie or token.
    Gives priority to token if both are present.
    """
    return token_user or cookie_user

# Initialize FastAPI without docs - we'll add custom protected docs routes below
app = FastAPI(docs_url=None, redoc_url=None)

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

# Add custom protected routes for documentation
@app.get("/docs", include_in_schema=False)
async def get_protected_docs(username: str = Depends(get_docs_credentials)):
    return get_swagger_ui_html(openapi_url="/openapi.json", title="API Documentation")

@app.get("/openapi.json", include_in_schema=False)
async def get_openapi_schema(username: str = Depends(get_docs_credentials)):
    return get_openapi(title="RecruiterBook API", version="1.0.0", routes=app.routes)

@app.get("/redoc", include_in_schema=False)
async def get_protected_redoc(username: str = Depends(get_docs_credentials)):
    return get_redoc_html(openapi_url="/openapi.json", title="API Documentation")

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
def create_review(review: ReviewCreate, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        # Set the user_id from the authenticated user
        review.user_id = current_user.get("id")
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
def upvote(review_id: int, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        original_review = db.query(Review).filter(Review.id == review_id).first()
        if not original_review:
            raise HTTPException(status_code=404, detail="Review not found")
        
        original_upvotes = original_review.upvotes
        
        # Use the user_id from the authenticated user
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
def downvote(review_id: int, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        original_review = db.query(Review).filter(Review.id == review_id).first()
        if not original_review:
            raise HTTPException(status_code=404, detail="Review not found")
        
        original_downvotes = original_review.downvotes
        
        # Use the user_id from the authenticated user
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
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve all reviews written by the currently authenticated user.
    """
    user_id = current_user.get("id")
    return get_reviews_by_user(db, user_id)

@app.get("/profile/helpfulness/", response_model=HelpfulnessScore)
def get_user_helpfulness(
    current_user: dict = Depends(get_current_user),
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
    current_user: dict = Depends(get_current_user),
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
    current_user: dict = Depends(get_current_user),
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

