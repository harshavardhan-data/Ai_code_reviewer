from pydantic import BaseModel,HttpUrl

class ReviewCreate(BaseModel):
    repository_url:str
    base_ref:str | None = None  # e.g . "main"
    head_ref:str | None = None  # e.g . "feature-x"

    
