from fastapi import HTTPException
from sqlalchemy.orm import Session
from models import User, Recruiter, Company, Review, ReviewVote
from schemas import UserCreate, RecruiterCreate, ReviewCreate
from ai_service import generate_summary
from google import verify_recruiter
import uuid
from better_profanity import profanity

# User creation/login
def get_or_create_user(db: Session, user_data: UserCreate):
    """
    Searches for a user by google_id. If not found, creates a new user.
    Ignores fullName/email checks for uniqueness.
    """
    # 1. Attempt to find a user by google_id
    user = None
    if user_data.google_id:  # Make sure we actually have a google_id
        user = db.query(User).filter(User.google_id == user_data.google_id).first()

    # 2. If no user found, create a new one
    if not user:
        user = User(
            id=str(uuid.uuid4()),
            fullName=user_data.fullName,
            google_id=user_data.google_id
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # 3. Return the user (existing or newly created)
    return user




# Company creation (ensures no duplicates)
def get_or_create_company(db: Session, company_name: str):
    company = db.query(Company).filter(Company.name == company_name).first()
    if not company:
        company = Company(id=str(uuid.uuid4()), name=company_name)
        db.add(company)
        db.commit()
        db.refresh(company)
    return company

# Recruiter creation (ensures no duplicates)
def get_or_create_recruiter(db: Session, recruiter_data: RecruiterCreate):
    # Get (or create) the company record.
    company = get_or_create_company(db, recruiter_data.company)
    
    # Look up an existing recruiter by fullName and company.
    recruiter = db.query(Recruiter).filter(
        Recruiter.fullName == recruiter_data.fullName,
        Recruiter.company_id == company.id
    ).first()

    # Determine verification status (True if verified, False otherwise)
    verified_status = verify_recruiter(recruiter_data.fullName, recruiter_data.company)
    
    # If the recruiter doesn't exist, create a new one with the verification status.
    if not recruiter:
        recruiter = Recruiter(
            id=str(uuid.uuid4()),
            fullName=recruiter_data.fullName,
            company_id=company.id,
            summary="",         # Placeholder for future AI-generated summaries
            verified=verified_status  # Set verified property based on verification result
        )
        db.add(recruiter)
        db.commit()
        db.refresh(recruiter)
    else:
        # If recruiter exists, update the verified property
        recruiter.verified = verified_status
        db.commit()
    
    return recruiter


# Find recruiters by full name and optional company
def find_recruiters(db: Session, fullName: str, company: str = None):
    query = db.query(Recruiter).filter(Recruiter.fullName == fullName)
    if company:
        query = query.join(Company).filter(Company.name == company)
    return query.all()

def get_recruiter_by_id(db: Session, recruiter_id: str):
    return db.query(Recruiter).filter(Recruiter.id == recruiter_id).first()

# Post a review
def post_review(db: Session, review_data: ReviewCreate):
    existing_review = db.query(Review).filter(
        Review.user_id == review_data.user_id,
        Review.recruiter_id == review_data.recruiter_id
    ).first()

    if existing_review:
        raise HTTPException(status_code=400, detail="Review already exists for this recruiter")

    if is_profane(review_data.text):
        raise HTTPException(status_code=400, detail="Profanity detected in review")

    new_review = Review(**review_data.dict())
    db.add(new_review)
    db.commit()
    db.refresh(new_review)

    # Update recruiter's average ratings
    recruiter = db.query(Recruiter).filter(Recruiter.id == review_data.recruiter_id).first()
    if not recruiter:
        raise HTTPException(status_code=404, detail="Recruiter not found")

    reviews = db.query(Review).filter(Review.recruiter_id == review_data.recruiter_id).all()

    recruiter.avg_resp = sum(r.responsiveness for r in reviews) // len(reviews)
    recruiter.avg_prof = sum(r.professionalism for r in reviews) // len(reviews)
    recruiter.avg_help = sum(r.helpfulness for r in reviews) // len(reviews)
    recruiter.avg_final_stage = sum(r.final_stage for r in reviews) // len(reviews)
    recruiter.summary = generate_summary(reviews)

    db.commit()

    return new_review


def get_reviews(db: Session, recruiter_id: str):
    return db.query(Review).filter(Review.recruiter_id == recruiter_id).all()

def get_all_reviews(db: Session):
    return db.query(Review).all()

def get_companies(db: Session):
    return db.query(Company).all()

def delete_company_by_name(db: Session, company_name: str):
    company = db.query(Company).filter(Company.name == company_name).first()
    if not company:
        return None  # Company not found
    db.delete(company)
    db.commit()
    return company

def is_profane(text):
    """Check if a text contains profanity."""
    profanity.load_censor_words()  # Load default profanity list
    return profanity.contains_profanity(text)  # Returns True if text contains bad words

def get_reviews_by_company(db: Session, company_name: str):
    """Retrieve all reviews associated with a specific company."""
    recruiters = db.query(Recruiter).filter(Recruiter.company.has(name=company_name)).all()
    
    if not recruiters:
        return []

    recruiter_ids = [recruiter.id for recruiter in recruiters]
    reviews = db.query(Review).filter(Review.recruiter_id.in_(recruiter_ids)).all()
    
    return reviews

def upvote_review(db: Session, review_id: int, user_id: str):
    """Record an upvote for a review by a given user and update aggregated counts."""
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    # Check if the user already voted on this review
    vote_record = db.query(ReviewVote).filter(
        ReviewVote.review_id == review_id,
        ReviewVote.user_id == user_id
    ).first()
    
    try:
        if vote_record:
            if vote_record.vote == 1:
                # Already upvoted
                return review
            else:
                # Changing vote from downvote (-1) to upvote (+1)
                vote_record.vote = 1
                review.downvotes = max(review.downvotes - 1, 0)
                review.upvotes += 1
        else:
            # No vote record exists, create a new upvote record
            vote_record = ReviewVote(
                review_id=review_id,
                user_id=user_id,
                vote=1
            )
            db.add(vote_record)
            review.upvotes += 1

        db.commit()
        db.refresh(review)
        return review
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to process upvote: {str(e)}")

def downvote_review(db: Session, review_id: int, user_id: str):
    """Record a downvote for a review by a given user and update aggregated counts."""
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    # Check if the user already voted on this review
    vote_record = db.query(ReviewVote).filter(
        ReviewVote.review_id == review_id,
        ReviewVote.user_id == user_id
    ).first()
    
    try:
        if vote_record:
            if vote_record.vote == -1:
                # Already downvoted
                return review
            else:
                # Changing vote from upvote (+1) to downvote (-1)
                vote_record.vote = -1
                review.upvotes = max(review.upvotes - 1, 0)
                review.downvotes += 1
        else:
            # No vote record exists, create a new downvote record
            vote_record = ReviewVote(
                review_id=review_id,
                user_id=user_id,
                vote=-1
            )
            db.add(vote_record)
            review.downvotes += 1

        db.commit()
        db.refresh(review)
        return review
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to process downvote: {str(e)}")

def get_reviews_by_user(db: Session, user_id: str):
    """Retrieve all reviews written by a specific user."""
    return db.query(Review).filter(Review.user_id == user_id).all()

def get_user_helpfulness_score(db: Session, user_id: str):
    """Calculate a user's helpfulness score based on received upvotes and downvotes."""
    # Get all reviews by the user
    user_reviews = db.query(Review).filter(Review.user_id == user_id).all()
    
    # Calculate total upvotes and downvotes
    total_upvotes = sum(review.upvotes for review in user_reviews)
    total_downvotes = sum(review.downvotes for review in user_reviews)
    
    return {
        "total_upvotes": total_upvotes,
        "total_downvotes": total_downvotes,
        "helpfulness_score": total_upvotes - total_downvotes
    }



