from typing import Optional
from sqlalchemy.orm import Session
from models import User, Recruiter, Review
from schemas import UserCreate, RecruiterCreate, ReviewCreate
import uuid

# Create or find a user
def get_or_create_user(db: Session, user_data: UserCreate):
    user = db.query(User).filter(User.linkedin_token == user_data.linkedin_token).first()
    if not user:
        user = User(id=str(uuid.uuid4()), linkedin_token=user_data.linkedin_token)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

# Find recruiters by name/company
def find_recruiters(db: Session, firstname: str, lastname: str, company: Optional[str] = None):
    query = db.query(Recruiter).filter(Recruiter.firstname == firstname, Recruiter.lastname == lastname)
    if company:
        query = query.filter(Recruiter.company == company)
    return query.all()

# Create a recruiter
def get_or_create_recruiter(db: Session, recruiter_data: RecruiterCreate):
    recruiter = db.query(Recruiter).filter(
        Recruiter.firstname == recruiter_data.firstname,
        Recruiter.lastname == recruiter_data.lastname,
        Recruiter.company == recruiter_data.company
    ).first()
    
    if not recruiter:
        recruiter = Recruiter(id=str(uuid.uuid4()), **recruiter_data.dict())
        db.add(recruiter)
        db.commit()
        db.refresh(recruiter)
    
    return recruiter

# Post a review
def post_review(db: Session, review_data: ReviewCreate):
    existing_review = db.query(Review).filter(
        Review.user_id == review_data.user_id,
        Review.recruiter_id == review_data.recruiter_id
    ).first()

    if existing_review:
        return 2  # Review already exists

    new_review = Review(**review_data.dict())
    db.add(new_review)
    db.commit()
    db.refresh(new_review)

    return 0  # Success

# Get reviews for a recruiter
def get_reviews(db: Session, recruiter_id: str):
    return db.query(Review).filter(Review.recruiter_id == recruiter_id).all()
