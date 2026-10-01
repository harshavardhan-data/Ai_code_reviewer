from fastapi import FastAPI
from app.db import Base,engine
from app.models.db_review import Review
from app.models.db_finding import Finding
from app.api.reviews import router as reviews_router  # 1. Import router



Base.metadata.create_all(bind=engine)


app=FastAPI(title="AI code reviewer")

app.include_router(reviews_router)

@app.get("/")
def root():
    return {"message":"AI Code Reviewer is running..."}

@app.get("/health")
def health():
    return {"status":"ok"}

