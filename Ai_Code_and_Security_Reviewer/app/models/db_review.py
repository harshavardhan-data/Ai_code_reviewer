from datetime import datetime
from sqlalchemy.orm import Mapped,mapped_column,relationship
from sqlalchemy import DateTime,String,func
from app.db import Base
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.db_finding import Finding


class Review(Base):

    __tablename__="reviews"

    id:Mapped[int] = mapped_column(primary_key=True)

    repository_url:Mapped[str] = mapped_column(String(500))

    status: Mapped[str] = mapped_column(String(20),default="pending")

    created_at:Mapped[datetime] = mapped_column(DateTime,server_default=func.now())

    findings:Mapped[list["Finding"]]= relationship("Finding",
        back_populates="review",cascade="all, delete-orphan",
    )


    