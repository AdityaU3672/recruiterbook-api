from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, index=True)
    fullName = Column(String, index=True)
    google_id = Column(String, unique=True, index=True, nullable=True)
    votes = relationship("ReviewVote", back_populates="user")

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
    verified = Column(Boolean, default=False)
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
    created_at = Column(Integer, nullable=True, default=lambda: int(datetime.utcnow().timestamp()))
    updated_at = Column(Integer, nullable=True, onupdate=lambda: int(datetime.utcnow().timestamp()))

    user = relationship("User")
    recruiter = relationship("Recruiter")
    votes = relationship("ReviewVote", back_populates="review")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.created_at:
            self.created_at = int(datetime.utcnow().timestamp())
        if not self.updated_at:
            self.updated_at = int(datetime.utcnow().timestamp())

    @property
    def created_at_datetime(self):
        """Convert Unix timestamp to datetime object."""
        if self.created_at:
            return datetime.fromtimestamp(self.created_at)
        return None

    @property
    def updated_at_datetime(self):
        """Convert Unix timestamp to datetime object."""
        if self.updated_at:
            return datetime.fromtimestamp(self.updated_at)
        return None

class ReviewVote(Base):
    __tablename__ = "review_votes"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    review_id = Column(Integer, ForeignKey("reviews.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    vote = Column(Integer, nullable=False)  # +1 for upvote, -1 for downvote

    # Optionally add relationships to the Review and User models
    review = relationship("Review", back_populates="votes")
    user = relationship("User", back_populates="votes")

