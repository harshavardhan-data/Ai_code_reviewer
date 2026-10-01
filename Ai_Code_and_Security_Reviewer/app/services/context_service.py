from pathlib import Path
from app.schemas.file import FileContext,CodeChunk
from app.services.ast_service import ASTService
from app.services.dependancy_service import DependencyService
import tiktoken

class ContextService:

    MAX_TOTAL_TOKENS = 30_000

    DEPENDENCY_WEIGHT = 2
    ENTRYPOINT_WEIGHT = 2
    SECURITY_WEIGHT = 3
    TEST_PENALTY = 2

    def __init__(self,ast_service:ASTService,dependancy_service:DependencyService):
        self.ast_service=ast_service
        self.dependancy_service=dependancy_service
    

    def estimate_tokens(self,text:str) -> int: 
            encoding=tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))

    def score_chunk(
    self,
    chunk: CodeChunk,
    dependency_score: int,
    ) -> int:

        score = dependency_score * self.DEPENDENCY_WEIGHT

        file_name = Path(chunk.file_path).name.lower()
        name = chunk.name.lower()

        if file_name in {"main.py", "app.py"}:
            score += self.ENTRYPOINT_WEIGHT

        if any(
            term in name
            for term in (
                "auth",
                "login",
                "password",
                "token",
                "permission",
                "query",
            )
        ):
            score += self.SECURITY_WEIGHT

        if file_name.startswith("test_"):
            score -= self.TEST_PENALTY

        return score

    def build_chunks(self,file_contexts:list[FileContext]) -> list[CodeChunk]:

        chunks=[]
        for file in file_contexts:
            single_chunk=self.ast_service.extract_chunks(file.path,file.content)
            chunks.extend(single_chunk)

        return chunks


    

    def select_context(self,file_contexts:list[FileContext],changed_paths:set[str] | None =None,) -> list[CodeChunk]:


        chunks=self.build_chunks(file_contexts)

        # PRINT THIS TO SEE THE EXACT MISMATCH:
        sample_chunk_path = chunks[0].file_path if chunks else "NO CHUNKS"
        sample_changed_path = list(changed_paths)[0] if changed_paths else "NO CHANGED PATHS"

        print(f"[DEBUG] Sample Chunk file_path  : '{sample_chunk_path}'")
        print(f"[DEBUG] Sample Changed file_path: '{sample_changed_path}'")
        

        if changed_paths is not None:
            print(f"[DEBUG] Match in set? : {sample_chunk_path in changed_paths}")
            chunks=[c for c in chunks if c.file_path in changed_paths]

        dependancy_scores=self.dependancy_service.build_dependency_scores(file_contexts)

        ranked_chunks=sorted(
            chunks,key=lambda chunk:self.score_chunk(chunk,dependancy_scores.get(chunk.file_path,0),
            ),
            reverse=True,
        )

        selected=[]
        total_tokens=0

        for chunk in ranked_chunks:
            chunk_tokens = self.estimate_tokens(chunk.content)

            if total_tokens + chunk_tokens > self.MAX_TOTAL_TOKENS:
                continue

            selected.append(chunk)
            total_tokens += chunk_tokens

        print(
        f"Selected {len(selected)} chunks "
        f"with ~{total_tokens} tokens"
     )
        return selected

        