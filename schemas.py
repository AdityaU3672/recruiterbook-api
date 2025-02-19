from pydantic import BaseModel
from typing import List, Optional

class UserCreate(BaseModel):
    linkedin_token: str

class UserResponse(BaseModel):
    id: str

class RecruiterCreate(BaseModel):
    firstname: str
    lastname: str
    company: str

class RecruiterResponse(BaseModel):
    id: str
    firstname: str
    lastname: str
    company: str

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
    professionalism: int
    responsiveness: int
    helpfulness: int
    text: str
    final_stage: int
