from google import genai
from google.genai import types

from app.core.config import GEMINI_API_KEY
from app.schemas.file import FileContext
from app.schemas.finding import ReviewFindings
from app.schemas.file import CodeChunk
from app.services.diff_parser import ChangedFile


class AIService:

    def __init__(self):
        self.client=genai.Client(api_key=GEMINI_API_KEY)
        self.model="gemini-3.1-flash-lite"


    def review_code(self,chunks:list[CodeChunk],changed_files:list[ChangedFile]|None=None) -> ReviewFindings:

        prompt=self._build_prompt(chunks)
        response=self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ReviewFindings,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
            ),
        )

        if not response.text:
            raise RuntimeError("Gemini returned an empty response")

        return ReviewFindings.model_validate_json(response.text)


    def _build_prompt(self,chunks:list[CodeChunk],changed_files:list[ChangedFile]|None=None) -> str:


        # group chunks by file

        chunks_by_file:dict[str,list[CodeChunk]]={}

        for c in chunks:
            chunks_by_file.setdefault(c.file_path,[]).append(c)

        sections=[]

        if changed_files is None:

            for chunk in chunks:
                sections.append(
                    f"CHUNK FROM: {chunk.file_path}\n"
                    f"```"
                    f"TYPE : {chunk.chunk_type}\n"
                    f"NAME : {chunk.name}\n"
                    f"{chunk.content}\n"
                    f"```"
                )

            code_context = "\n\n".join(sections)

            return f"""
                You are an expert Python code reviewer.

                Review the provided source code for real, actionable issues.

                Look for:
                - bugs and incorrect logic
                - security vulnerabilities
                - performance problems
                - maintainability problems

                For every finding:
                - identify the exact file
                - provide the line number when possible
                - classify it
                - assign a severity
                - explain why it is a problem
                - suggest a practical fix

                Do not invent issues.
                Do not report stylistic preferences as bugs.
                If there are no meaningful issues, return an empty findings list.

                SOURCE CODE:

                {code_context}
                """
        # PR mode — include diff per changed file
        changed_by_path={f.path:f for f in changed_files}

        for path,file_chunks in chunks_by_file.items():
            changed=changed_by_path.get(path)
            if changed is None:
                continue

            chunk_sections="\n\n".join(
            f"TYPE : {c.chunk_type}\nNAME : {c.name}\n{c.content}"
            for c in file_chunks
            )

            added_sorted=sorted(changed.added_lines)
            added_str = ", ".join(str(n) for n in added_sorted) or "(none)"


            sections.append(
                f"=== FILE: {path} ===\n"
            f"ADDED LINE NUMBERS (only these are new): {added_str}\n\n"
            f"DIFF:\n```diff\n{changed.diff_text}```\n\n"
            f"FULL CHUNKS FROM THIS FILE:\n```\n{chunk_sections}\n```"
            )

            code_context="\n\n".join(sections)

            return f"""
            You are an expert Python code reviewer reviewing a Pull Request.

            You will see, per file:
            - the git diff (what changed)
            - the list of line numbers that are NEW in this PR
            - the current content of the changed chunks

            RULES:
            - ONLY report issues on lines whose numbers appear in "ADDED LINE NUMBERS".
            - Do NOT report issues on unchanged/context lines, even if they look buggy — they are pre-existing and out of scope for this PR.
            - Line numbers in your findings must refer to the NEW file (the numbers we gave you).

            Look for:
            - bugs and incorrect logic
            - security vulnerabilities
            - performance problems
            - maintainability problems

            For every finding:
            - identify the exact file
            - provide the line number from the NEW file
            - classify it
            - assign a severity
            - explain why it is a problem
            - suggest a practical fix

            Do not invent issues.
            Do not report stylistic preferences as bugs.
            If there are no meaningful issues on the new lines, return an empty findings list.

            CHANGED FILES:

            {code_context}

        """

