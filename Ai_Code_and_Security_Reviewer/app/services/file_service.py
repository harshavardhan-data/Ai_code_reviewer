from pathlib import Path
from app.schemas.file import FileContext
import tiktoken

class FileService:

    MAX_FILE_TOKENS = 10_000
    MAX_TOTAL_TOKENS = 30_000

    SUPPORTED_EXTENSIONS = {
        ".py",
        ".js",
        ".ts",
        ".jsx",
        ".tsx",
    }
    LANGUAGE_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".cpp": "cpp",
    ".c": "c",
    ".html": "html",
    ".css": "css",
    ".sql": "sql",
}

    IGNORED_DIRECTORIES = {
        ".git",
        "node_modules",
        ".venv",
        "venv",
        "__pycache__",
        "dist",
        "build",
    }

    def find_source_files(self, repository_path: Path,only_paths:set[str] | None =None) -> list[Path]:
        files = []

        # OPTION A: Targeted Lookup (Fast - O(K) where K = changed files)
        if only_paths is not None:
            for rel_path_str in only_paths:
                file_path=repository_path/rel_path_str

                if not file_path.is_file():
                    continue

                if any(part in self.IGNORED_DIRECTORIES for part in file_path.parts):
                    continue

                if file_path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
                    continue
        

                files.append(file_path)

            return files

        # OPTION B: Full Repo Scan (O(N) - used only when building full codebase context)
        for path in repository_path.rglob("*"):
            if not path.is_file():
                continue

            if any(part in self.IGNORED_DIRECTORIES for part in path.parts):
                continue

            if path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
                continue

            files.append(path)

        return files

    def read_file(self,file_path:Path) ->str:
        """Reads and returns the text content of a file safely.
        
        Uses errors='replace' to prevent unhandled UnicodeDecodeErrors
        if a binary file or non-UTF-8 encoding is encountered.
        """
        try:
            return file_path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            raise RuntimeError(f"Failed to read file '{file_path}': {str(exc)}") from exc


    def build_file_context(self,repository_path:Path,only_paths:set[str] |None =None) -> list[FileContext]:

        total_tokens=0
        contexts=[]

        for file_path in self.find_source_files(repository_path,only_paths):

            # file_size=file_path.stat().st_size
            content = self.read_file(file_path)
            file_tokens = self.estimate_tokens(content)

            if file_tokens > self.MAX_FILE_TOKENS:
                continue


            contexts.append(FileContext(path=file_path.relative_to(repository_path).as_posix(),
                                       content=content,language=self.get_language(file_path),
                                       )
                                    )
            total_tokens+=file_tokens
            
        return contexts

    def estimate_tokens(self,text:str) -> int: 
        encoding=tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))

    def get_language(self,file_path:Path):
        return self.LANGUAGE_MAP.get(file_path.suffix.lower(), "text")