from app.db import Base, engine
from app.models import db_review, db_finding  # ensure models are imported
from app.models.db_review import Review
from app.models.db_finding import Finding
from app.api.reviews import router as reviews_router 

Base.metadata.create_all(bind=engine)
print("[INIT] tables ensured")