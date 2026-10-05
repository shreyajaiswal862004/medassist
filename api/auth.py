import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from utils.db import get_db

load_dotenv()

# ── CONFIG ───────────────────────────────────────────────────
# these come from your .env file
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", 24))

# ── PASSWORD HASHING ─────────────────────────────────────────
# bcrypt is the algorithm — deliberately slow to prevent brute force
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    # turns "mypassword123" into "$2b$12$abc...gibberish"
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    # checks if typed password matches the stored hash
    # returns True or False
    return pwd_context.verify(plain_password, hashed_password)

# ── JWT TOKEN ────────────────────────────────────────────────
# OAuth2PasswordBearer tells FastAPI where to look for the token
# it looks in the Authorization header: "Bearer <token>"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def create_access_token(data: dict) -> str:
    # copy the data so we don't modify the original
    to_encode = data.copy()

    # add expiry time — token dies after 24 hours
    expire = datetime.utcnow() + timedelta(hours=EXPIRY_HOURS)
    to_encode.update({"exp": expire})

    # encode everything into one signed string using your secret key
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token

def decode_access_token(token: str) -> dict:
    # decode the token back to the original data
    # throws JWTError automatically if token is expired or tampered
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    return payload

# ── PYDANTIC MODELS ──────────────────────────────────────────
# these define the shape of request and response data

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    role: str  # must be: patient, doctor, or admin

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: int
    name: str

# ── GET CURRENT USER ─────────────────────────────────────────
# this runs automatically before any protected route
# FastAPI injects the token from the request header
def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    # this error is shown if anything goes wrong with the token
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token. Please login again.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # decode the token
        payload = decode_access_token(token)

        # extract user info from the token
        user_id: int = payload.get("user_id")
        role: str = payload.get("role")
        name: str = payload.get("name")

        # if any key info is missing, token is invalid
        if user_id is None or role is None:
            raise credentials_exception

        return {"user_id": user_id, "role": role, "name": name}

    except JWTError:
        raise credentials_exception

# ── ROLE CHECKER ─────────────────────────────────────────────
# use this to protect routes by role
# example: only doctors can access the review queue
def require_role(allowed_roles: list):
    def role_checker(current_user: dict = Depends(get_current_user)):
        if current_user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {allowed_roles}"
            )
        return current_user
    return role_checker

# shortcuts for common role checks
require_patient = require_role(["patient"])
require_doctor  = require_role(["doctor"])
require_admin   = require_role(["admin"])
require_doctor_or_admin = require_role(["doctor", "admin"])

# ── REGISTER FUNCTION ────────────────────────────────────────
def register_user(request: RegisterRequest, db: Session) -> dict:
    from sqlalchemy import text

    # check role is valid
    if request.role not in ["patient", "doctor", "admin"]:
        raise HTTPException(
            status_code=400,
            detail="Role must be patient, doctor, or admin"
        )

    # check email not already registered
    existing = db.execute(
        text("SELECT id FROM users WHERE email = :email"),
        {"email": request.email}
    ).fetchone()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    # hash the password — never store plain text
    hashed = hash_password(request.password)

    # insert new user into database
    result = db.execute(
        text("""
            INSERT INTO users (name, email, password_hash, role)
            VALUES (:name, :email, :password_hash, :role)
            RETURNING id
        """),
        {
            "name": request.name,
            "email": request.email,
            "password_hash": hashed,
            "role": request.role
        }
    )
    db.commit()

    new_user_id = result.fetchone()[0]

    # if patient, also create a row in patients table
    if request.role == "patient":
        db.execute(
            text("""
                INSERT INTO patients (user_id)
                VALUES (:user_id)
            """),
            {"user_id": new_user_id}
        )
        db.commit()

    return {
        "message": "Registration successful",
        "user_id": new_user_id,
        "role": request.role
    }

# ── LOGIN FUNCTION ───────────────────────────────────────────
def login_user(request: LoginRequest, db: Session) -> TokenResponse:
    from sqlalchemy import text

    # fetch user from database by email
    user = db.execute(
        text("SELECT id, name, email, password_hash, role FROM users WHERE email = :email"),
        {"email": request.email}
    ).fetchone()

    # if no user found or password wrong — same error message
    # never tell the attacker which one failed
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    # create JWT token with user info inside
    token = create_access_token({
        "user_id": user.id,
        "role": user.role,
        "name": user.name
    })

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        role=user.role,
        user_id=user.id,
        name=user.name
    )


# ── TEST ─────────────────────────────────────────────────────
if __name__ == "__main__":
    from utils.db import SessionLocal

    print("\n--- TEST 1: password hashing ---")
    hashed = hash_password("testpassword123")
    print("Hashed:", hashed[:30] + "...")
    print("Verify correct:", verify_password("testpassword123", hashed))
    print("Verify wrong:", verify_password("wrongpassword", hashed))

    print("\n--- TEST 2: JWT token ---")
    token = create_access_token({"user_id": 1, "role": "patient", "name": "Riya"})
    print("Token:", token[:40] + "...")
    decoded = decode_access_token(token)
    print("Decoded:", decoded)

    print("\n--- TEST 3: register and login ---")
    db = SessionLocal()
    try:
        # register a test patient
        req = RegisterRequest(
            name="Test Patient",
            email="testpatient@example.com",
            password="test123",
            role="patient"
        )
        result = register_user(req, db)
        print("Registered:", result)

        # login with those credentials
        login_req = LoginRequest(
            email="testpatient@example.com",
            password="test123"
        )
        token_response = login_user(login_req, db)
        print("Login token:", token_response.access_token[:40] + "...")
        print("Role:", token_response.role)

    except Exception as e:
        print("Error (maybe already registered):", e)
    finally:
        db.close()

    print("\n✅ auth working")