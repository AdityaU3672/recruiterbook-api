from sqlalchemy.orm import Session
from models import User, Recruiter, Company, Review
from schemas import UserCreate, RecruiterCreate, ReviewCreate
from ai_service import generate_summary
import uuid

# User creation/login
def get_or_create_user(db: Session, user_data: UserCreate):
    user = db.query(User).filter(User.linkedin_token == user_data.linkedin_token).first()
    if not user:
        user = User(id=str(uuid.uuid4()), linkedin_token=user_data.linkedin_token)
        db.add(user)
        db.commit()
        db.refresh(user)
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
    company = get_or_create_company(db, recruiter_data.company)
    recruiter = db.query(Recruiter).filter(
        Recruiter.fullName == recruiter_data.fullName,
        Recruiter.company_id == company.id
    ).first()

    if not recruiter:
        recruiter = Recruiter(
            id=str(uuid.uuid4()),
            fullName=recruiter_data.fullName,
            company_id=company.id,
            summary=""  # Placeholder for future AI-generated summaries
        )
        db.add(recruiter)
        db.commit()
        db.refresh(recruiter)

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
        return 2  # Review already exists

    new_review = Review(**review_data.dict())
    db.add(new_review)
    db.commit()
    db.refresh(new_review)

    # Update recruiter's average ratings
    recruiter = db.query(Recruiter).filter(Recruiter.id == review_data.recruiter_id).first()
    reviews = db.query(Review).filter(Review.recruiter_id == review_data.recruiter_id).all()

    recruiter.avg_resp = sum(r.responsiveness for r in reviews) // len(reviews)
    recruiter.avg_prof = sum(r.professionalism for r in reviews) // len(reviews)
    recruiter.avg_help = sum(r.helpfulness for r in reviews) // len(reviews)
    recruiter.avg_final_stage = sum(r.final_stage for r in reviews) // len(reviews)  # New calculation
    recruiter.summary = generate_summary(reviews)


    db.commit()

    return 0  # Success

def get_reviews(db: Session, recruiter_id: str):
    return db.query(Review).filter(Review.recruiter_id == recruiter_id).all()

def get_companies(db: Session):
    return db.query(Company).all()
