from pathlib import Path
import tempfile

from app.services.git_service import GitService
# Adjust this import to match where build_file_context lives
from app.services.file_service import FileService 
from app.services.context_service import ContextService
from app.services.dependancy_service import DependencyService
from app.services.ast_service import ASTService
import pytest

def test_token_counting():
    ast=ASTService()
    depen=DependencyService(ast)
    git_service = GitService()
    file_service = FileService()  # The class containing build_file_context
    context_service= ContextService(ast,depen)

    repo_url = "https://github.com/PyCQA/bandit"  # Use any real public repo

    # Automatically creates and deletes the temporary directory on exit
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        print(f"Cloning '{repo_url}' to temp location: {temp_path/"cloned_repo"}...")

        # Clone repository
        cloned_path = git_service.clone_repository(
            repository_url=repo_url, destination=temp_path / "cloned_repo"
        )

        # Process file contexts & calculate tokens
        contexts = file_service.build_file_context(cloned_path)

        # dependancy_scores=context_service.build_dependancy_scores(contexts)

        selected_chunks=context_service.select_context(contexts)


        print(f"TOTAL FILES : {len(contexts)}")
        print(f"TOTAL CHUNKS : {len(selected_chunks)}")
        # # Calculate totals
        # total_tokens = sum(file_service.estimate_tokens(c.content) for c in selected_contexts)
       

        # print("\nPer-file breakdown:")
        # for chunk in selected_chunks:
        #     path=chunk.file_path
        #     # tokens = file_service.estimate_tokens(chunk.content)
        #     # score=context_service.score_chunk(chunk,dependancy_scores.get(chunk.file_path))
        #     print(f" - {path}: NAME: {chunk.name} TYPE :{chunk.chunk_type} ")

    print("\nTemp directory successfully deleted.")

