from fastapi import HTTPException
from sqlalchemy.orm import Session
from models import User, Recruiter, Company, Review, ReviewVote, IndustryEnum
from schemas import UserCreate, RecruiterCreate, ReviewCreate, ReviewUpdate, IndustryEnum as SchemaIndustryEnum
from ai_service import generate_summary
from google import verify_recruiter, infer_company_industry
import uuid
from better_profanity import profanity
from fuzzywuzzy import fuzz, process
from database import SessionLocal
from sqlalchemy import func

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

def is_profane(text):
    """Censor profane words in text with asterisks matching the length of the word."""
    profanity.load_censor_words()  # Load default profanity list
    
    def custom_censor(word):
        return '*' * len(word)
    
    profanity.censor_words = custom_censor
    return profanity.censor(text)  # Returns text with profane words censored

def contains_profanity(text):
    """Checks if the text contains any profanity words.
    
    Args:
        text (str): The text to check for profanity
        
    Returns:
        bool: True if profanity is found, False otherwise
    """
    profanity.load_censor_words()
    return profanity.contains_profanity(text)

# Company creation (ensures no duplicates)
def get_or_create_company(db: Session, company_name: str):
    # Check for profanity in company name
    if contains_profanity(company_name):
        raise HTTPException(status_code=400, detail="Company name contains inappropriate language")
        
    company = db.query(Company).filter(Company.name == company_name).first()
    if not company:
        # Create a new company and infer its industry
        industry_str = infer_company_industry(company_name)
        
        # Convert string industry to enum integer
        industry_int = IndustryEnum.from_str(industry_str)
        
        company = Company(id=str(uuid.uuid4()), name=company_name, industry=industry_int)
        db.add(company)
        db.commit()
        db.refresh(company)
    elif not company.industry or not isinstance(company.industry, int) or company.industry not in [0, 1, 2, 3]:
        # If company exists but doesn't have a valid industry, infer and set it
        industry_str = infer_company_industry(company_name)
        company.industry = IndustryEnum.from_str(industry_str)
        db.commit()
        db.refresh(company)
    return company

# Recruiter creation (ensures no duplicates)
def get_or_create_recruiter(db: Session, recruiter_data: RecruiterCreate):
    # Check for profanity in recruiter name
    if contains_profanity(recruiter_data.fullName):
        raise HTTPException(status_code=400, detail="Recruiter name contains inappropriate language")
        
    # Check for profanity in company name (redundant since get_or_create_company also checks,
    # but keeping for completeness)
    if contains_profanity(recruiter_data.company):
        raise HTTPException(status_code=400, detail="Company name contains inappropriate language")
    
    # Get (or create) the company record.
    company = get_or_create_company(db, recruiter_data.company)
    
    # Look up an existing recruiter by fullName and company.
    recruiter = db.query(Recruiter).filter(
        Recruiter.fullName == recruiter_data.fullName,
        Recruiter.company_id == company.id
    ).first()

    # Set default verified status - will be updated asynchronously
    verified_status = False
    
    # If the recruiter doesn't exist, create a new one with default verification status.
    if not recruiter:
        recruiter = Recruiter(
            id=str(uuid.uuid4()),
            fullName=recruiter_data.fullName,
            company_id=company.id,
            summary="",         # Placeholder for future AI-generated summaries
            verified=verified_status  # Default to False, will be updated asynchronously
        )
        db.add(recruiter)
        db.commit()
        db.refresh(recruiter)
    
    # Schedule verification in a background task (don't wait for it)
    import threading
    def verify_in_background():
        try:
            verified = verify_recruiter(recruiter_data.fullName, recruiter_data.company)
            # Update the recruiter's verified status in a new session
            with SessionLocal() as bg_db:
                db_recruiter = bg_db.query(Recruiter).filter(Recruiter.id == recruiter.id).first()
                if db_recruiter:
                    db_recruiter.verified = verified
                    bg_db.commit()
        except Exception as e:
            print(f"Background verification failed: {str(e)}")
    
    # Start the background task
    thread = threading.Thread(target=verify_in_background)
    thread.daemon = True  # Thread will die when main thread exits
    thread.start()
    
    return recruiter


# Find recruiters by full name and optional company
def find_recruiters(db: Session, fullName: str, company: str = None):
    # Get all recruiters
    query = db.query(Recruiter)
    all_recruiters = query.all()
    
    # If no recruiters at all in DB, return empty list
    if not all_recruiters:
        return []
    
    # Set an absolute minimum similarity threshold to prevent irrelevant matches
    ABSOLUTE_MIN_THRESHOLD = 65
    
    # Prepare a list to store recruiter objects with their similarity scores
    scored_recruiters = []
    
    # Calculate similarity scores for each recruiter's name
    for recruiter in all_recruiters:
        # Calculate different similarity scores
        token_sort_score = fuzz.token_sort_ratio(fullName.lower(), recruiter.fullName.lower())
        partial_score = fuzz.partial_ratio(fullName.lower(), recruiter.fullName.lower())
        ratio_score = fuzz.ratio(fullName.lower(), recruiter.fullName.lower())
        
        # Use the best score among the three methods
        best_score = max(token_sort_score, partial_score, ratio_score)
        
        # Only include recruiters with a minimum similarity score
        if best_score >= ABSOLUTE_MIN_THRESHOLD:
            scored_recruiters.append((recruiter, best_score))
    
    # Sort by similarity score (descending)
    scored_recruiters.sort(key=lambda x: x[1], reverse=True)
    
    # If company is specified, reorganize results to prioritize that company
    if company and scored_recruiters:
        # Split into two lists: company matches and non-company matches
        company_matches = []
        non_company_matches = []
        
        for recruiter, score in scored_recruiters:
            if recruiter.company and recruiter.company.name.lower() == company.lower():
                company_matches.append((recruiter, score))
            else:
                non_company_matches.append((recruiter, score))
                
        # Combine the lists with company matches first
        sorted_recruiters = [r for r, _ in company_matches] + [r for r, _ in non_company_matches]
    else:
        # If no company specified, just use the score-sorted list
        sorted_recruiters = [r for r, _ in scored_recruiters]
    
    # Return at most 10 results
    return sorted_recruiters[:10]

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

    # Censor any profane words in the review text
    censored_text = is_profane(review_data.text)
    
    # Create a new review with censored text
    review_dict = review_data.dict()
    review_dict['text'] = censored_text
    new_review = Review(**review_dict)
    
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
    
    # Update database with average ratings now
    db.commit()
    
    # Generate summary in the background
    import threading
    def generate_summary_in_background():
        try:
            # Get fresh data in a new session
            with SessionLocal() as bg_db:
                bg_reviews = bg_db.query(Review).filter(Review.recruiter_id == review_data.recruiter_id).all()
                if bg_reviews:
                    summary_text = generate_summary(bg_reviews)
                    bg_recruiter = bg_db.query(Recruiter).filter(Recruiter.id == review_data.recruiter_id).first()
                    if bg_recruiter:
                        bg_recruiter.summary = summary_text
                        bg_db.commit()
        except Exception as e:
            print(f"Background summary generation failed: {str(e)}")
    
    # Start the background task
    thread = threading.Thread(target=generate_summary_in_background)
    thread.daemon = True
    thread.start()

    return new_review


def get_reviews(db: Session, recruiter_id: str):
    return db.query(Review).filter(Review.recruiter_id == recruiter_id).all()

def get_all_reviews(db: Session):
    return db.query(Review).all()

def get_companies(db: Session):
    return db.query(Company).all()

def delete_company_by_name(db: Session, company_name: str):
    # Check for profanity in company name
    if contains_profanity(company_name):
        raise HTTPException(status_code=400, detail="Company name contains inappropriate language")
        
    company = db.query(Company).filter(Company.name == company_name).first()
    if not company:
        return None  # Company not found
    db.delete(company)
    db.commit()
    return company

def get_reviews_by_company(db: Session, company_name: str):
    """Retrieve all reviews associated with a specific company."""
    # Check for profanity in company name
    if contains_profanity(company_name):
        raise HTTPException(status_code=400, detail="Company name contains inappropriate language")
        
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
                # Already upvoted - clear the vote
                db.delete(vote_record)
                review.upvotes = max(review.upvotes - 1, 0)
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
                # Already downvoted - clear the vote
                db.delete(vote_record)
                review.downvotes = max(review.downvotes - 1, 0)
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

def update_review(db: Session, review_id: int, user_id: str, review_data: ReviewUpdate):
    """Update a review by its ID and user ID."""
    review = db.query(Review).filter(
        Review.id == review_id,
        Review.user_id == user_id
    ).first()
    
    if not review:
        raise HTTPException(status_code=404, detail="Review not found or unauthorized")
    
    # Update only the fields that were provided
    update_data = review_data.dict(exclude_unset=True)
    if "text" in update_data:
        update_data["text"] = is_profane(update_data["text"])
    
    for field, value in update_data.items():
        setattr(review, field, value)
    
    db.commit()
    db.refresh(review)
    
    # Update recruiter's average ratings
    recruiter = review.recruiter
    reviews = db.query(Review).filter(Review.recruiter_id == recruiter.id).all()
    
    recruiter.avg_resp = sum(r.responsiveness for r in reviews) // len(reviews)
    recruiter.avg_prof = sum(r.professionalism for r in reviews) // len(reviews)
    recruiter.avg_help = sum(r.helpfulness for r in reviews) // len(reviews)
    recruiter.avg_final_stage = sum(r.final_stage for r in reviews) // len(reviews)
    recruiter.summary = generate_summary(reviews)
    
    db.commit()
    return review

def delete_review(db: Session, review_id: int, user_id: str):
    """Delete a review by its ID and user ID."""
    review = db.query(Review).filter(
        Review.id == review_id,
        Review.user_id == user_id
    ).first()
    
    if not review:
        raise HTTPException(status_code=404, detail="Review not found or unauthorized")
    
    recruiter_id = review.recruiter_id
    
    # First delete all associated votes to avoid foreign key constraint violations
    db.query(ReviewVote).filter(ReviewVote.review_id == review_id).delete()
    
    # Then delete the review
    db.delete(review)
    db.commit()
    
    # Update recruiter's average ratings
    recruiter = db.query(Recruiter).filter(Recruiter.id == recruiter_id).first()
    if recruiter:
        reviews = db.query(Review).filter(Review.recruiter_id == recruiter_id).all()
        if reviews:
            recruiter.avg_resp = sum(r.responsiveness for r in reviews) // len(reviews)
            recruiter.avg_prof = sum(r.professionalism for r in reviews) // len(reviews)
            recruiter.avg_help = sum(r.helpfulness for r in reviews) // len(reviews)
            recruiter.avg_final_stage = sum(r.final_stage for r in reviews) // len(reviews)
            recruiter.summary = generate_summary(reviews)
        else:
            # If no reviews left, reset averages to 0
            recruiter.avg_resp = 0
            recruiter.avg_prof = 0
            recruiter.avg_help = 0
            recruiter.avg_final_stage = 0
            recruiter.summary = "No reviews available."
        
        db.commit()
    
    return {"message": "Review deleted successfully"}

def get_all_recruiters(db: Session):
    """
    Returns all recruiters in the database.
    """
    return db.query(Recruiter).all()

def get_reviews_by_industry(db: Session, industry_id: int):
    """Retrieve all reviews for recruiters at companies in a specific industry."""
    try:
        # Validate the industry ID
        industry_id = int(industry_id)
        if industry_id not in [0, 1, 2, 3]:
            return []
            
        # Get all companies in the specified industry
        companies = db.query(Company).filter(Company.industry == industry_id).all()
        
        if not companies:
            return []
            
        company_ids = [company.id for company in companies]
        
        # Get all recruiters from these companies
        recruiters = db.query(Recruiter).filter(Recruiter.company_id.in_(company_ids)).all()
        
        if not recruiters:
            return []
            
        recruiter_ids = [recruiter.id for recruiter in recruiters]
        
        # Get all reviews for these recruiters
        reviews = db.query(Review).filter(Review.recruiter_id.in_(recruiter_ids)).all()
        
        return reviews
    except (ValueError, TypeError):
        # Handle case where industry_id can't be converted to int
        return []

def update_all_company_industries(db: Session, force_update=False):
    """
    Updates industry information for all companies in the database.
    If force_update is True, all companies will be updated regardless of whether they already have an industry set.
    If force_update is False, only companies without an industry set will be updated.
    Ensures all companies are categorized using the industry enum integers.
    """
    import threading
    from google import infer_company_industry
    
    # Query companies based on force_update flag
    if force_update:
        companies = db.query(Company).all()
    else:
        # Only update companies without industry or with industries not as integers
        companies = db.query(Company).filter(
            (Company.industry.is_(None)) | 
            (~Company.industry.in_([0, 1, 2, 3]))
        ).all()
    
    if not companies:
        return {"message": "No companies to update"}
    
    def update_company_industry(company_id):
        """Thread worker function to update a single company's industry"""
        with SessionLocal() as thread_db:
            company = thread_db.query(Company).filter(Company.id == company_id).first()
            if company:
                industry_str = infer_company_industry(company.name)
                company.industry = IndustryEnum.from_str(industry_str)
                thread_db.commit()
    
    # Create and start threads for each company update
    threads = []
    for company in companies:
        thread = threading.Thread(target=update_company_industry, args=(company.id,))
        thread.daemon = True
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete (with a reasonable timeout)
    for thread in threads:
        thread.join(timeout=60)
    
    return {"message": f"Started industry update for {len(companies)} companies"}

def get_all_industries(db: Session):
    """
    Returns a list of all industry IDs and their corresponding names.
    """
    from schemas import IndustryResponse
    return IndustryResponse.get_all()

def get_companies_by_industry(db: Session, industry_id: int):
    """
    Retrieve all companies belonging to a specific industry.
    """
    try:
        # Validate the industry ID
        industry_id = int(industry_id)
        if industry_id not in [0, 1, 2, 3]:
            return []
            
        # Get all companies in the specified industry
        companies = db.query(Company).filter(Company.industry == industry_id).all()
        return companies
    except (ValueError, TypeError):
        # Handle case where industry_id can't be converted to int
        return []

def get_featured_recruiters(db: Session):
    """
    Returns recruiters added by specific users: Aditya Uchil or Rishi Papani.
    """
    # Get the user IDs for Aditya and Rishi
    aditya = db.query(User).filter(User.fullName == "Aditya Uchil").first()
    rishi = db.query(User).filter(User.fullName == "Rishi Papani").first()
    
    featured_recruiters = []
    user_ids = []
    
    # Add their user IDs if found
    if aditya:
        user_ids.append(aditya.id)
    if rishi:
        user_ids.append(rishi.id)
    
    if not user_ids:
        # If neither user is found, return empty list
        return []
    
    # Get all reviews written by either user
    reviews = db.query(Review).filter(Review.user_id.in_(user_ids)).all()
    
    if not reviews:
        return []
    
    # Get unique recruiter IDs from the reviews
    recruiter_ids = list(set(review.recruiter_id for review in reviews))
    
    # Get the recruiters
    recruiters = db.query(Recruiter).filter(Recruiter.id.in_(recruiter_ids)).all()
    
    return recruiters

def get_editors_pick_reviews(db: Session):
    """
    Returns reviews written by specific users: Aditya Uchil or Rishi Papani.
    These are considered editor's picks.
    """
    # Get the user IDs for Aditya and Rishi
    aditya = db.query(User).filter(User.fullName == "Aditya Uchil").first()
    rishi = db.query(User).filter(User.fullName == "Rishi Papani").first()
    
    user_ids = []
    
    # Add their user IDs if found
    if aditya:
        user_ids.append(aditya.id)
    if rishi:
        user_ids.append(rishi.id)
    
    if not user_ids:
        # If neither user is found, return empty list
        return []
    
    # Get all reviews written by either user
    reviews = db.query(Review).filter(Review.user_id.in_(user_ids)).all()
    
    return reviews



