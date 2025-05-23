import os
from datetime import datetime, timedelta
from typing import List
import uuid
import json
import jwt
from fastapi import APIRouter, Depends, Request, HTTPException, Response
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from authlib.integrations.starlette_client import OAuth, OAuthError
from dotenv import load_dotenv

from database import SessionLocal
from crud import get_or_create_user
from models import User, ReviewVote
from schemas import ReviewVoteResponse, UserCreate, UserResponse

load_dotenv()

router = APIRouter()
oauth = OAuth()

oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    # Use OIDC discovery to get all necessary endpoints (including userinfo)
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-me")  # Replace in production
JWT_EXPIRES_MINUTES = int(os.getenv("JWT_EXPIRES_MINUTES", 30))

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_jwt_token(user_id: str, profile_pic: str) -> str:
    expires_delta = timedelta(minutes=JWT_EXPIRES_MINUTES)
    expiration = datetime.utcnow() + expires_delta
    payload = {
        "sub": user_id,
        "pfp": profile_pic,
        "exp": expiration
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")

@router.get("/google/login")
async def google_login(request: Request, next: str = None):
    # Save the "next" URL in the session if provided
    if next:
        request.session["next"] = next
    redirect_uri = request.url_for("google_callback")
    return await oauth.google.authorize_redirect(request, str(redirect_uri))


@router.get("/google/callback", response_model=UserResponse)
async def google_callback(request: Request, db: Session = Depends(get_db)):
    try:
        token = await oauth.google.authorize_access_token(request)
    except OAuthError as error:
        raise HTTPException(status_code=401, detail=str(error))
    
    # Retrieve user info from Google
    resp = await oauth.google.userinfo(token=token)
    profile = dict(resp)  # Convert UserInfo object to dict

    google_sub = profile.get("sub")
    full_name = profile.get("name", "Unknown")
    profile_pic = profile.get("picture")
    if not google_sub:
        raise HTTPException(status_code=400, detail="No 'sub' found in Google profile")

    # Look up or create the user
    user_data = UserCreate(fullName=full_name, google_id=google_sub)
    user = get_or_create_user(db, user_data)
    
    # Generate JWT token for the user
    jwt_token = create_jwt_token(user.id, profile_pic)
    
    # Retrieve the "next" URL from the session (or use a default)
    next_url = request.session.pop("next", "http://localhost:3000")
    
    # Log request details for debugging
    print(f"Callback request headers: {dict(request.headers)}")
    print(f"Callback request cookies: {dict(request.cookies)}")
    print(f"Next URL: {next_url}")
    
    # Prepare a redirect response
    response = RedirectResponse(url=next_url)
    
    # Determine if we're in production based on the next_url
    is_production = "recruiterbook.0x0.lat" in next_url
    print(f"Is production: {is_production}")
    
    # Set cookie with domain for production
    cookie_settings = {
        "key": "access_token",
        "value": jwt_token,
        "httponly": True,
        "secure": True,
        "samesite": "none" if is_production else "lax",
        "path": "/",
        "max_age": JWT_EXPIRES_MINUTES * 60
    }
    
    # Add domain in production
    if is_production:
        cookie_settings["domain"] = ".recruiterbook.0x0.lat"  # Note the leading dot for subdomains
    
    print(f"Cookie settings: {cookie_settings}")
    response.set_cookie(**cookie_settings)
    
    return response

def get_current_user_from_cookie(request: Request, db: Session = Depends(get_db)):
    # Log request details for debugging
    print(f"Auth check headers: {dict(request.headers)}")
    print(f"Auth check cookies: {dict(request.cookies)}")
    
    token = request.cookies.get("access_token")
    if not token:
        print("No access_token cookie found")
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing subject")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    user_data = {
        "id": user.id,
        "fullName": user.fullName,
        "google_id": user.google_id,
        "profile_pic": payload.get("pfp")  # "pfp" is included in the JWT token payload
    }

    return user_data

@router.get("/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_user_from_cookie)):
    return current_user

@router.post("/logout")
def logout_user(response: Response, request: Request):
    """
    Endpoint to log the user out by clearing the cookie.
    """
    # Determine if we're in production based on the request origin
    is_production = "recruiterbook.0x0.lat" in request.headers.get("origin", "")
    
    # Remove the cookie by setting max_age=0 (or expires to a date in the past).
    response.set_cookie(
        key="access_token",
        value="",
        httponly=True,
        secure=True,
        samesite="none" if is_production else "lax",  # Use "none" for production, "lax" for development
        path="/",
        max_age=0,         # effectively removes the cookie immediately
        domain=".recruiterbook.0x0.lat" if is_production else None  # Set domain for production
    )
    return {"message": "User has been logged out."}

@router.get("/votes/", response_model=List[ReviewVoteResponse])
def get_user_votes(
    current_user: dict = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)
):
    """
    Retrieve all vote records for the currently authenticated user.
    """
    user_id = current_user.get("id")
    votes = db.query(ReviewVote).filter(ReviewVote.user_id == user_id).all()
    return votes




