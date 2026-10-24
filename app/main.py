import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator, EmailStr
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from app.db.session import get_db
from app.db.models import Poll, User, PollOption
from pwdlib import PasswordHash
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jwt.exceptions import InvalidTokenError

password_haser= PasswordHash.recommended()
JWT_SECRET_KEY=  os.getenv("JWT_SECRET_KEY")

if not JWT_SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY is not configured")

JWT_ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=120
# oauth2_scheme=OAuth2PasswordBearer(
#     tokenUrl="/api/v1/auth/login"
# )

bearer_scheme= HTTPBearer()
def create_access_token(user_id: int)-> str:
    now= datetime.now(timezone.utc)

    payload={
        "sub": str(user_id),
        "iat": now,
        "exp": now+timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    }

    return jwt.encode(
        payload, 
        JWT_SECRET_KEY,
        algorithm= JWT_ALGORITHM
    )

def get_current_user(
        credentials: HTTPAuthorizationCredentials=Depends(bearer_scheme),
        db: Session= Depends(get_db),
)-> User: 
    credentials_exception= HTTPException(
        status_code=401,
        detail= "Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try: 
        payload=jwt.decode(
            credentials.credentials, 
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
        )
        user_id=payload.get("sub")

        if user_id is None:
            raise credentials_exception

        user= db.get(User, int(user_id))

    except (InvalidTokenError, ValueError):
        raise credentials_exception

    if user is None: 
        raise credentials_exception

    return user
app= FastAPI(
    title= "Wahala Board Api",
    description="A place to settle everyday debates",
    version= "0.1.0"
)
class UserCreate(BaseModel):
    username: str=Field(min_length=2, max_length=50)
    email: EmailStr
    password: str=Field(min_length=6, max_length=128)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class PollCreate(BaseModel):
    question: str=Field(min_length=5, max_length=200)
    options: list[str]= Field(min_length=2, max_length=4)

    @field_validator("options")
    @classmethod
    def validate_options(cls, options: list[str])-> list[str]:
        cleaned_options= [option.strip() for option in options]

        if any(not option for option in cleaned_options):
            raise ValueError("Options cannot be empty")

        normalized_options=[
            option.casefold() for option in cleaned_options
        ]

        if len(normalized_options)!=len(set(normalized_options)):
            raise ValueError("Every poll option must be unique")

        return cleaned_options

@app.post("/api/v1/auth/register", status_code=201)
def register_user(user: UserCreate, db: Session= Depends(get_db)):
    existing_user= db.scalar(
        select(User).where(
            (User.email==user.email)| (User.username== user.username)
        )
    )
    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="Email or username is already registered"
        )
    new_user=User(
        username=user.username.strip(),
        email= user.email.strip().lower(),
        password= password_haser.hash(user.password), 
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "user":{
            "id": new_user.id,
            "username": new_user.username,
            "email": new_user.email,
        },
        "message": "User created successfully",
    }

@app.post("/api/v1/auth/login")
def login_user(
    credentials: UserLogin, 
    db: Session= Depends(get_db)
):
    user=db.scalar(
        select(User).where(User.email==credentials.email)
    )

    if user is None or not password_haser.verify(
        credentials.password,
        user.password
    ): raise HTTPException(
        status_code=401,
        detail= "INvalid email or password",
        headers={"WWW-Authenticate": "Bearer"},
    )

    access_token= create_access_token(user.id)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }

@app.get("/api/v1/auth/me")
def Get_me( current_user: User= Depends(get_current_user),):
    return{
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
    }
@app.post("/api/v1/polls", status_code= 201)
def create_poll(poll:PollCreate, db: Session= Depends(get_db), current_user: User = Depends(get_current_user),):
    new_poll=Poll(
        question=poll.question,
        userId=current_user.id
    )

    new_poll.options=[
        PollOption(text=option)
        for option in poll.options
    ]
    db.add(new_poll)
    db.commit()
    db.refresh(new_poll)
    return {
        "id": new_poll.id,
        "question": new_poll.question,
        "options": [
            {"id": option.id, "text": option.text}
            for option in new_poll.options
        ],
        "created_by": {
            "id": current_user.id,
            "username": current_user.username,
        },
    }


@app.get("/")
def home():
    return {
        "message": "Welcome to Wahala Board",
        "status": "Running",
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/api/v1/polls")
def get_polls(db: Session= Depends(get_db)):
    statement=(
        select(Poll)
        .options(selectinload(Poll.options))
        .order_by(Poll.id.desc())
    )

    polls=db.scalars(statement).all()

    return {
        "polls": [
            {
                "id": poll.id,
                "question": poll.question,
                "options": [
                    {"id": option.id, "text": option.text}
                    for option in poll.options
                ],
            }
            for poll in polls
        ]
    }