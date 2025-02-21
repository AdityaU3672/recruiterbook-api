from pydantic import BaseModel
from typing import List

class UserCreate(BaseModel):
    linkedin_token: str

class UserResponse(BaseModel):
    id: str

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
    professionalism: int
    responsiveness: int
    helpfulness: int
    text: str
    final_stage: int
