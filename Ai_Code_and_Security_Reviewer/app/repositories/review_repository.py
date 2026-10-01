from sqlalchemy import select
from sqlalchemy.orm import Session


from app.models.db_review import Review
from app.schemas.finding import ReviewFindings
from app.models.db_finding import Finding
from app.schemas.finding import FindingCreate



class ReviewRepository:

    def __init__(self,session:Session):
        self.session=session


    def get_by_id(self,review_id:int) -> Review | None:
        return self.session.execute(select(Review).where(Review.id == review_id)).scalar_one_or_none()

    def get_all_reviews(self) -> list[Review]:
        return self.session.execute(select(Review)).scalars().all()


    def create_review(self,repository_url:str) -> Review:
        review=Review(repository_url=repository_url)

        try:
            self.session.add(review)
            self.session.commit()
            self.session.refresh(review)

            return review 
        except Exception:
            self.session.rollback()
            raise

    def update_status(self, review_id: int, status: str) -> Review | None:
        review = self.get_by_id(review_id)
        if review:
            try:
                review.status = status
                self.session.commit()
                self.session.refresh(review)
            except Exception:
                self.session.rollback()
                raise
        return review


    def create_finding(self, review_id: int, data: FindingCreate) -> Finding:
        finding = Finding(
            review_id=review_id,
            file_path=data.file_path,
            line_number=data.line_number,
            category=data.category,
            severity=data.severity,
            title=data.title,
            description=data.description,
            suggestion=data.suggestion,
        )
        try:
            self.session.add(finding)
            self.session.commit()
            self.session.refresh(finding)
            return finding
        except Exception:
            self.session.rollback()
            raise

    def create_findings(
        self, review_id: int, findings_data: ReviewFindings
    ) -> list[Finding]:
        ingestion_list = [
            Finding(
                review_id=review_id,
                file_path=finding.file_path,  
                line_number=finding.line_number,
                category=finding.category,
                severity=finding.severity,
                title=finding.title,
                description=finding.description,
                suggestion=finding.suggestion,
            )
            for finding in findings_data.findings
        ]

        try:

            # Bulk add and commit within the repo
            self.session.add_all(ingestion_list)
            self.session.commit()
            return ingestion_list
        except Exception:
            self.session.rollback()
            raise

    def get_findings(self, review_id: int) -> list[Finding]:
        return self.session.execute(
            select(Finding).where(Finding.review_id == review_id)
        ).scalars().all()




        
