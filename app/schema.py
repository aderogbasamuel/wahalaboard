from pydantic import BaseModel, ConfigDict, Field, field_validator

class PollCreate(BaseModel):
    question: str=Field(min_length=5, max_length=200)
    options: list[str]= Field(min_length=2, max_length=4)

    @field_validator("question")
    @classmethod
    def validate_question(cls, question: str)-> str:
        question= question.strip()

        if len(question)< 5:
            raise ValueError()