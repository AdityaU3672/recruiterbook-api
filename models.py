from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, index=True)
    fullName = Column(String, index=True)
    google_id = Column(String, unique=True, index=True, nullable=True)

class Company(Base):
    __tablename__ = "companies"
    id = Column(String, primary_key=True, index=True)
    name = Column(String, unique=True, index=True) 

class Recruiter(Base):
    __tablename__ = "recruiters"
    id = Column(String, primary_key=True, index=True)
    fullName = Column(String, index=True)
    company_id = Column(String, ForeignKey("companies.id"))
    avg_resp = Column(Integer, default=0)
    avg_prof = Column(Integer, default=0)
    avg_help = Column(Integer, default=0)
    avg_final_stage = Column(Integer, default=0)
    summary = Column(String, default="")
    company = relationship("Company")

class Review(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"))
    recruiter_id = Column(String, ForeignKey("recruiters.id"))
    professionalism = Column(Integer)
    responsiveness = Column(Integer)
    helpfulness = Column(Integer)
    text = Column(String)
    final_stage = Column(Integer)
    upvotes = Column(Integer, default=0)  
    downvotes = Column(Integer, default=0)  

    user = relationship("User")
    recruiter = relationship("Recruiter")

