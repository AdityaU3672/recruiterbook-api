from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, index=True)
    linkedin_token = Column(String, unique=True, index=True)

class Recruiter(Base):
    __tablename__ = "recruiters"
    id = Column(String, primary_key=True, index=True)
    firstname = Column(String, index=True)
    lastname = Column(String, index=True)
    company = Column(String, index=True)

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
