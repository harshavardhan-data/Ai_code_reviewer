from pydantic import BaseModel,Field
from typing import Literal

class FindingCreate(BaseModel):

    file_path: str
    line_number: int | None = None
    category: Literal[
        "bug",
        "security",
        "performance",
        "maintainability",
    ]

    severity: Literal[
        "low","medium","high","critical",
    ]
    title: str = Field(min_length=1,max_length=200)

    description: str = Field(min_length=1)
    suggestion: str | None = None


class ReviewFindings(BaseModel):
    findings:list[FindingCreate]



