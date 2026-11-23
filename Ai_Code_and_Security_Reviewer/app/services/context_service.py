from pathlib import Path
from app.schemas.file import FileContext,CodeChunk
from app.services.ast_service import ASTService
from app.services.dependancy_service import DependencyService
import tiktoken

class ContextService:

    MAX_TOTAL_TOKENS = 30_000
    MAX_UPSTREAM_TOKENS=10_000

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


    

    def select_context(self,file_contexts:list[FileContext]
                       ,changed_paths:set[str] | None =None,
                       upstream_names:dict[str,set[str]] | None=None,
                       dependancy_scores:dict[str,int] | None= None) -> list[CodeChunk]:


        chunks=self.build_chunks(file_contexts)

        print(f"File Contexts : {[f.path for f in file_contexts]}")
        
        upstream_names=upstream_names or {}
        changed_paths=changed_paths or set()
        dependancy_scores=dependancy_scores or {}

        # symbol filter for upstream files (changed files untouched)
        chunks = [
            c for c in chunks
            if c.file_path not in upstream_names
            or upstream_names[c.file_path] is None
            or c.name in upstream_names[c.file_path]
        ]

       
        print("DEPENDANCY SCORES")
        print(dependancy_scores)

        def _rank_chunk(chunk:CodeChunk) ->tuple[bool,int]:
            is_changed=chunk.file_path in changed_paths
            base=self.score_chunk(chunk,dependancy_scores.get(chunk.file_path,0))
            return (is_changed,base)
        

        ranked_chunks=sorted(
            chunks,key=_rank_chunk,reverse=True,
        )

        print("RANKED CHUNKS")

        rk=[(chunk.file_path,chunk.name) for chunk in ranked_chunks]
        for r in rk:
            print(r)

        selected:list[CodeChunk]=[]
        changed_tokens=0
        upstream_tokens=0

        for chunk in ranked_chunks:
            chunk_tokens = self.estimate_tokens(chunk.content)

            is_upstream = chunk.file_path in upstream_names

            if is_upstream:
                if upstream_tokens + chunk_tokens > self.MAX_UPSTREAM_TOKENS:
                    continue
                upstream_tokens += chunk_tokens
            else:
                if changed_tokens + chunk_tokens > self.MAX_TOTAL_TOKENS:
                    continue
                changed_tokens += chunk_tokens

            selected.append(chunk)
            

        print(
        f"Selected {len(selected)} chunks "
        f"with ~{changed_tokens+upstream_tokens} tokens"
     )
        return selected

        