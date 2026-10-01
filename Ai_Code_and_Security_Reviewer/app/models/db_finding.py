from sqlalchemy import ForeignKey,String
from sqlalchemy.orm import Mapped,mapped_column,relationship
from app.db import Base

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.db_review import Review

class Finding(Base):

    __tablename__="findings"

    id:Mapped[int] = mapped_column(primary_key=True)

    review_id:Mapped[int] = mapped_column(ForeignKey("reviews.id",ondelete="CASCADE"),
                                          nullable=False)

    file_path:Mapped[str] = mapped_column(String(500))

    line_number: Mapped[int| None]

    category: Mapped[str] = mapped_column(String(50))

    severity: Mapped[str] = mapped_column(String(20))

    title: Mapped[str] = mapped_column(String(200))

    description: Mapped[str]

    suggestion: Mapped[str | None]

    review:Mapped["Review"]= relationship("Review",
        back_populates="findings"
    )

    

