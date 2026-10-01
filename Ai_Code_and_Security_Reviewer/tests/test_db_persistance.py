from app.db import SessionLocal
from app.schemas.file import FileContext
from app.repositories.review_repository import ReviewRepository
from app.services.ai_service import AIService

# 1. Create mock FileContext objects with 2 sample .py files
file_1 = FileContext(
    path="app/utils/auth.py",
    language="python",
    content="""
import hashlib

def hash_password(password: str) -> str:
    
    return hashlib.md5(password.encode()).hexdigest()

def check_access(user_role: str):
    if user_role == "admin":
        return True
    return False
""",
)

file_2 = FileContext(
    path="app/db/connection.py",
    language="python",
    content="""
import sqlite3

def get_user_by_name(username: str):
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    
    query = f"SELECT * FROM users WHERE name = '{username}'"
    cursor.execute(query)
    return cursor.fetchall()
""",
)

file_contexts = [file_1, file_2]

def run_test():
    db=SessionLocal()
    repo=ReviewRepository(db)
    ai_service=AIService()

    print("1. Creating dummy Review record in DB...")
    review = repo.create_review(repository_url="https://github.com/mock/repo")
    print(f"   Created Review ID: {review.id} with status: '{review.status}'")

    print("\n2. Updating status to 'processing'...")
    repo.update_status(review.id, "processing")

    print("\n3. Sending FileContexts to Gemini AI...")
    review_findings = ai_service.review_code(file_contexts)
    print(f"   AI returned {len(review_findings.findings)} findings.")

    print("\n4. Bulk persisting findings into SQLite...")
    repo.create_findings(review.id, review_findings)


    print("\n5. Updating status to 'completed'....")
    repo.update_status(review.id,"completed")

    # 5. Verify database contents
    updated_review = repo.get_by_id(review.id)
    print(f"\n--- SUCCESS ---")
    print(f"Final Review #{updated_review.id} Status: '{updated_review.status}'")
    print(f"\nPersisted Findings in DB:")


    db.close()


if __name__ == "__main__":
    run_test()

# line 14 # Insecure MD5 hashing without salt
# line 33 # SQL Injection risk



