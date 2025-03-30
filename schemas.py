from pydantic import BaseModel, field_validator
from typing import Optional, Union, Any
from datetime import datetime

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
    user_id: Optional[str] = None
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
    created_at: Optional[Any] = None
    updated_at: Optional[Any] = None
    
    @field_validator('created_at', 'updated_at')
    @classmethod
    def validate_timestamp(cls, v):
        if v is None:
            return None
        if isinstance(v, datetime):
            return int(v.timestamp())
        if isinstance(v, int):
            return v
        # For any other type, try to convert to int or return None
        try:
            return int(v)
        except (ValueError, TypeError):
            return None
        
    class Config:
        from_attributes = True
        arbitrary_types_allowed = True

class ReviewVoteResponse(BaseModel):
    id: int
    review_id: int
    vote: int  # 1 for upvote, -1 for downvote

class HelpfulnessScore(BaseModel):
    total_upvotes: int
    total_downvotes: int
    helpfulness_score: int

class ReviewUpdate(BaseModel):
    professionalism: Optional[int] = None
    responsiveness: Optional[int] = None
    helpfulness: Optional[int] = None
    text: Optional[str] = None
    final_stage: Optional[int] = None

