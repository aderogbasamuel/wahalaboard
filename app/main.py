from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator, EmailStr
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from app.db.session import get_db
from app.db.models import Poll, User, PollOption
from pwdlib import PasswordHash


pasword_haser= PasswordHash.recommended()

app= FastAPI(
    title= "Wahala Board Api",
    description="A place to settle everyday debates",
    version= "0.1.0"
)
class UserCreate(BaseModel):
    username: str=Field(min_length=2, max_length=50)
    email: EmailStr
    password: str=Field(min_length=6, max_length=128)


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

@app.post("/api/v1/register", status_code=201)
def register_user(user: UserCreate, db: Session= Depends(get_db)):
    existing_user= db.scalar(
        select(User).where(
            (User.email==user.email)| (User.username== user.username)
        )
    )
    if existing_user:
        raise HTTPException(
            status_code=409,
            details="Email or username is already registered"
        )
    new_user=User(
        username=user.username.strip(),
        email= user.email.strip().lower(),
        password= pasword_haser.hash(user.password), 
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
    
@app.post("/api/v1/polls", status_code= 201)
def create_poll(poll:PollCreate, db: Session= Depends(get_db)):
    new_poll=Poll(question=poll.question)

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