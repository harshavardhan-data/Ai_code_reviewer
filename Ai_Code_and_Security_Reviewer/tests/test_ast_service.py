from pathlib import Path
import tempfile

from app.services.git_service import GitService
# Adjust this import to match where build_file_context lives
from app.services.file_service import FileService 
from app.services.context_service import ContextService
from app.services.ast_service import ASTService
from app.schemas.file import CodeChunk


def check_ast_working():
    git_service=GitService()
    file_service=FileService()
    context_service=ContextService()
    ast_service=ASTService()

    repo_url="https://github.com/harshavardhan-data/agentic-ai-playground"

    with tempfile.TemporaryDirectory()  as temp_dir:
        temp_path=Path(temp_dir)

        print(f"Cloning '{repo_url}' to temp location: {temp_path}...")
        
                # Clone repository
        cloned_path = git_service.clone_repository(
                    repository_url=repo_url, destination=temp_path / "cloned_repo"
                )

        # Process file contexts & calculate tokens
        contexts = file_service.build_file_context(cloned_path)
        
        selected_contexts=context_service.select_files(contexts)

        # 3. Extract AST code chunks cleanly (flattened)
        all_chunks: list[CodeChunk] = []
        for context in selected_contexts:
            chunks = ast_service.extract_chunks(
                file_path=Path(context.path),
                content=context.content
            )
            all_chunks.extend(chunks)  # Use extend() instead of append() to keep list flat!

        # 4. Calculate total tokens across all AST chunks
        total_tokens = sum(file_service.estimate_tokens(chunk.content) for chunk in all_chunks)

        print("\n================ TOKEN COUNT RESULTS ================")
        print(f"Total AST Chunks Processed: {len(all_chunks)}")
        print(f"Total Estimated Tokens: {total_tokens}")

        print("\nPer-chunk breakdown:")
        for chunk in all_chunks:
            print(chunk.model_dump(exclude='content'))
            # tokens = file_service.estimate_tokens(chunk.content)
            # score = context_service.score_file(Path(chunk.file_path))
            # print(f" - [{chunk.chunk_type.upper()}: {chunk.name}] {chunk.file_path}: {tokens} tokens -- Score => {score}")

    print("\nTemp directory successfully deleted.")


if __name__ == "__main__":
    check_ast_working()

    