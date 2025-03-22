import os
from datetime import datetime, timedelta
import uuid
import json
import jwt
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from authlib.integrations.starlette_client import OAuth, OAuthError
from dotenv import load_dotenv

from database import SessionLocal
from crud import get_or_create_user
from schemas import UserCreate, UserResponse

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

def create_jwt_token(user_id: str) -> str:
    expires_delta = timedelta(minutes=JWT_EXPIRES_MINUTES)
    expiration = datetime.utcnow() + expires_delta
    payload = {
        "sub": user_id,
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


@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    try:
        token = await oauth.google.authorize_access_token(request)
    except OAuthError as error:
        raise HTTPException(status_code=401, detail=str(error))
    
    resp = await oauth.google.userinfo(token=token)
    profile = dict(resp)
    
    google_sub = profile.get("sub")
    full_name = profile.get("name", "Unknown")
    if not google_sub:
        raise HTTPException(status_code=400, detail="No 'sub' found in Google profile")
    
    user_data = UserCreate(fullName=full_name, google_id=google_sub)
    user = get_or_create_user(db, user_data)
    jwt_token = create_jwt_token(user.id)
    
    # Retrieve the "next" URL from the session; default to homepage if not set.
    next_url = request.session.pop("next", "https://your-frontend.com/home")
    
    # Prepare the auth data for the frontend (including the google_id)
    auth_data = {
        "access_token": jwt_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "fullName": user.fullName,
            "google_id": user.google_id
        }
    }
    
    # Return an HTML page that stores the auth data in localStorage and then redirects.
    html_content = f"""
    <html>
      <head>
        <script type="text/javascript">
            const authData = {json.dumps(json.dumps(auth_data))};
            console.log("Auth Data:", authData);
            window.localStorage.setItem("authData", authData);
            window.location.href = "{next_url}";
        </script>
      </head>
      <body>
        <p>Logging you in, please wait...</p>
      </body>
    </html>
    """
    return HTMLResponse(content=html_content)

