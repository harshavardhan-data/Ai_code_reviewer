import ast
from pathlib import Path

from app.schemas.file import CodeChunk


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

        return chunks

    def extract_imports(self, content: str) -> set[tuple[str,int]]:
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return set()

        imports = set()

        for node in ast.walk(tree):

            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(
                        (alias.name,0)
                        )

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(
                        (node.module or "",node.level,)
                        )

        return imports