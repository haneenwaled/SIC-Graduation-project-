from pydantic import BaseModel, Field

class RAGQueryRequest(BaseModel):
    question: str = Field(
        ..., 
        example="What retention actions does the playbook suggest for high-risk customers?"
    )

class RAGQueryResponse(BaseModel):
    question: str
    answer: str