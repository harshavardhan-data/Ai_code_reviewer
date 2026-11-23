import ast
from pathlib import Path

from app.schemas.file import CodeChunk
from dataclasses import dataclass

@dataclass(frozen=True)
class ImportRef:
    module:str
    level:int
    names:frozenset[str] | None 


class ASTService:

    def extract_chunks(
        self,
        file_path: str|Path,
        content: str,
    ) -> list[CodeChunk]:

        if not content.strip():
            return []

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return []

        chunks = []

        for node in tree.body:

            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                source = ast.get_source_segment(content, node)

                if source:
                    chunks.append(
                        CodeChunk(
                            file_path=str(file_path),
                            chunk_type="function",
                            name=node.name,
                            content=source,
                            line_start=node.lineno,
                            line_end=node.end_lineno or node.lineno,
                        )
                    )

            elif isinstance(node, ast.ClassDef):
                source = ast.get_source_segment(content, node)

                if source:
                    chunks.append(
                        CodeChunk(
                            file_path=str(file_path),
                            chunk_type="class",
                            name=node.name,
                            content=source,
                            line_start=node.lineno,
                            line_end=node.end_lineno or node.lineno,
                        )
                    )
        
        print(f"[DEBUG] File '{file_path}' extracted {len(chunks)} chunks: {[c.name for c in chunks]}")

        return chunks

    def extract_imports(self, content: str) -> set[ImportRef]:
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return set()

        imports:set[ImportRef] = set()
        for node in ast.walk(tree):

            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(
                        ImportRef(alias.name,0,None)
                        )

            elif isinstance(node, ast.ImportFrom):
                names = frozenset(a.name for a in node.names)
                if "*" in names:
                    names = None        
                imports.add(
                    ImportRef(node.module or "",node.level,names)
                    )

        return imports  