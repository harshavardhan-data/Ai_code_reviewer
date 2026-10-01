from app.schemas.file import FileContext
from app.services.ai_service import AIService


files = [
    FileContext(
        path="example.py",
        language="python",
        content="""
def divide(a, b):
    return a / b
""",
    )
]

# result = AIService().review_code(files)

# print(result.model_dump_json(indent=2))