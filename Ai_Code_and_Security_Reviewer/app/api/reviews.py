from fastapi import APIRouter,Depends,BackgroundTasks,HTTPException
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from app.schemas.review import ReviewCreate
from app.services.review_service import ReviewService
from app.api.dependancies import get_review_service



# 1. Group endpoints together under a common prefix and tag
router = APIRouter(prefix="/reviews", tags=["reviews"])

@router.post("/")
def create_review_endpoint(data: ReviewCreate,background_tasks:BackgroundTasks,review_service:ReviewService=Depends(get_review_service)):

    # 1. Instantly save 'pending' record to database
    review=review_service.create_new_review(data)


    # 2. Schedule cloning & file reading in background AFTER response is sent
    background_tasks.add_task(
        review_service.process_review_in_background,
        review_id=review.id,
        repository_url=str(data.repository_url),
        base_ref=data.base_ref,
        head_ref=data.head_ref
    )

   
    return {
        "id":review.id,
        "repository_url": review.repository_url,
        "status":review.status,
        "created_at":review.created_at,
    }

@router.get("/{review_id}")
def get_review_status_endpoint(review_id:int,review_service:ReviewService=Depends(get_review_service)):
    
    review=review_service.get_review_by_id(review_id)

    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    return {
        "id": review.id,
        "repository_url": review.repository_url,
        "status": review.status,
        "created_at": review.created_at,
    }

@router.get("/{review_id}/findings")
def get_findings_by_review_id(review_id:int,review_service:ReviewService=Depends(get_review_service),):

    review=review_service.get_review_by_id(review_id)
    # stmt=select(Review).options(selectinload(Review.findings)).where(Review.id == review_id)

    if not review:
        raise HTTPException(status_code=404,detail="No such Review Exists")

    findings = review_service.get_findings(review_id)


    return findings
