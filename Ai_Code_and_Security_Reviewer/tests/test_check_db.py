from app.db import SessionLocal
from app.models.db_finding import Finding
from app.models.db_review import Review
from sqlalchemy import select




# db = SessionLocal()



# reviews=db.scalars(select(Review)).all()
# for review in reviews:
#     print(f"Review ID : {review.id} , Created At : {review.created_at} , Repository Url :{review.repository_url}")

#     for finding in review.findings:
#         line_info = f" (Line {finding.line_number})" if finding.line_number else ""
#         print(f"    └── [{finding.review_id}] [{finding.category}] {finding.file_path}{line_info}")
#         print(f"        Title:       {finding.title}")
#         print(f"        Description: {finding.description}")

#         print(f"        Suggestion:  {finding.suggestion}")
       

# db.close()