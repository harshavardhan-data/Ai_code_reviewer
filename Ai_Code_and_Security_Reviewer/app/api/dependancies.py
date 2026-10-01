from collections.abc import Generator
from fastapi import Depends
from sqlalchemy.orm import Session
from app.db import SessionLocal
from app.services.git_service import GitService
from app.services.ai_service import AIService
from app.services.file_service import FileService
from app.services.context_service import ContextService
from app.services.review_service import ReviewService
from app.services.ast_service import ASTService
from app.services.dependancy_service import DependencyService



def get_db() -> Generator:
    db=SessionLocal()

    try:
        yield db
    finally:
        db.close()


def get_git_service() -> GitService:return GitService()
def get_file_service() -> FileService:return FileService()
def get_ai_service() -> AIService:return AIService()
def get_ast_service() -> ASTService:return ASTService()

def get_dependancy_service(ast_service:ASTService=Depends(get_ast_service)) -> DependencyService:return DependencyService(ast_service)
def get_context_service(ast_service:ASTService=Depends(get_ast_service),
                        dependancy_service:DependencyService=Depends(get_dependancy_service)) -> ContextService:return ContextService(ast_service,dependancy_service)


def get_review_service(
        git_service: GitService = Depends(get_git_service),
        file_service: FileService = Depends(get_file_service),
        ai_service: AIService = Depends(get_ai_service),
        context_service: ContextService = Depends(get_context_service),
) -> ReviewService:
    return ReviewService(git_service,file_service,ai_service,context_service)

