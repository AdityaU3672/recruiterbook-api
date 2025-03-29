from pydantic import BaseModel
from typing import Optional

class UserCreate(BaseModel):
    fullName: str
    google_id: str | None = None

class UserResponse(BaseModel):
    id: str
    fullName: str
    profile_pic: Optional[str] = None

class CompanyCreate(BaseModel):
    name: str

class CompanyResponse(BaseModel):
    id: str
    name: str

class RecruiterCreate(BaseModel):
    fullName: str
    company: str  # Company name as input

class RecruiterResponse(BaseModel):
    id: str
    fullName: str
    company: CompanyResponse
    avg_resp: int
    avg_prof: int
    avg_help: int
    avg_final_stage: int
    verified: bool
    summary: str

class ReviewCreate(BaseModel):
    user_id: str
    recruiter_id: str
    professionalism: int
    responsiveness: int
    helpfulness: int
    text: str
    final_stage: int

class ReviewResponse(BaseModel):
    id: int
    recruiter_id: str
    professionalism: int
    responsiveness: int
    helpfulness: int
    text: str
    final_stage: int
    upvotes: int
    downvotes: int

class ReviewVoteResponse(BaseModel):
    id: int
    review_id: int
    vote: int  # 1 for upvote, -1 for downvote

class HelpfulnessScore(BaseModel):
    total_upvotes: int
    total_downvotes: int
    helpfulness_score: int

