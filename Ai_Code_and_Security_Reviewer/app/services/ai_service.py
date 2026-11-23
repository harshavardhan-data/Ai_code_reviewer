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
        self.model="gemini-3.6-flash"

    

    def review_code(self,chunks:list[CodeChunk],changed_files:list[ChangedFile]|None=None) -> ReviewFindings:

        prompt=self._build_prompt(chunks,changed_files)
        response=self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ReviewFindings,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                thinking_config=types.ThinkingConfig(
                    thinking_level='HIGH'
                )
            ),
        )

        if not response.text:
            raise RuntimeError("Gemini returned an empty response")

        return ReviewFindings.model_validate_json(response.text)
        # return prompt
    

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
                You are an expert software engineer and code reviewer.

                Review the provided source code for real, actionable issues.

                Look for:
                - bugs and incorrect logic
                - security vulnerabilities
                - performance and scalability bottlenecks
                - maintainability and robustness problems

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
        print(f"\n[DEBUG _build_prompt] Keys in changed_by_path: {list(changed_by_path.keys())}")
        print(f"[DEBUG _build_prompt] All chunk_by_file keys (files we have chunks for): {list(chunks_by_file.keys())}\n")
        other_sections=[]
        for path,file_chunks in chunks_by_file.items():
            changed=changed_by_path.get(path)
            
            print(f"[DEBUG _build_prompt] Checking file path: '{path}' | Matched changed file? {changed is not None}")
            # 1. Format chunks with explicit real line numbers
            formatted_chunks = []
            for c in file_chunks:
                lines = c.content.splitlines()
                numbered_lines = "\n".join(
                    f"{c.line_start + i:4d} | {line}" for i, line in enumerate(lines)
                )
                formatted_chunks.append(
                    f"TYPE : {c.chunk_type}\n"
                    f"NAME : {c.name}\n"
                    f"```python\n{numbered_lines}\n```"
                )

            chunk_sections="\n\n".join(formatted_chunks)

            if not changed:
                other_sections.append(
                        f"=== UPSTREAM FILE: {path} (CONTEXT ONLY) ===\n"
                    f"CONTEXT CHUNKS USED IN CHANGED FILES:\n{chunk_sections}"
                )
                continue

            # 2. Extract line numbers for prompt header context
            added_sorted=sorted(changed.added_lines)
            added_str = ", ".join(str(n) for n in added_sorted) or "(none)"


            sections.append(
                f"=== FILE: {path} ===\n"
            f"ADDED LINE NUMBERS IN THIS PR: {added_str}\n\n"
            f"DIFF:\n```diff\n{changed.diff_text.strip()}\n```\n\n"
            f"FULL CHUNKS FROM THIS FILE:\n{chunk_sections}"
            )
        sections.append("\n======================UPSTREAM FILE CHUNKS======================\n")
        all_sections=sections+other_sections
        code_context="\n\n".join(all_sections)
        
        return f"""
           You are an expert software engineer and code reviewer evaluating a Pull Request.

        You will see:
        - CHANGED FILES (PRIMARY — REVIEW THESE): for each changed file, the git diff, 
          the list of line numbers that are new or modified in this PR (`ADDED LINE NUMBERS IN THIS PR`), 
          and the current code chunks from that file with exact line numbers (`FULL CHUNKS FROM THIS FILE`).
        - UPSTREAM FILE CHUNKS (CONTEXT ONLY — DO NOT REVIEW): read-only definitions from dependency files imported by the changed files. 
          These chunks are symbol-filtered — only the specific functions/classes the changed files import are shown. Do not assume the rest of the 
          upstream file is visible, and do not comment on these files.

        REVIEW OBJECTIVES:
        Review only lines in CHANGED FILES that are listed under `ADDED LINE NUMBERS IN THIS PR` (this includes both newly added and modified lines). Evaluate for:
        - Correctness & Logic: edge cases, exception handling, race conditions, incorrect state management,business logic(for example:negative pricing possibility) ,genuine conflicts with upstream behavior.
        - Security: injection, broken access control, insecure data handling, hardcoded credentials/secrets, cryptographic flaws.
        - Performance: resource leaks, redundant or inefficient(n+1 db queries or other bad usage) DB operations, inefficient execution patterns.
        - Maintainability: type-safety violations, brittle abstractions, fragile logic,hardcoded parameters or values.

        USING UPSTREAM CONTEXT (ONLY WHEN GENUINE):
        Do NOT invent upstream conflicts just because upstream chunks are provided. Only flag a conflict when a line you are reviewing genuinely clashes with a visible upstream definition, e.g.:
        - wrong argument count, order, names, or types passed to an upstream callable or constructor
        - wrong assumptions about return type, `None` vs. non-`None` returns, or attributes/keys on returned values
        - an upstream function that raises under conditions the new code does not handle
        - `async`/`await` mismatches, or conflicting side effects/mutations
        When a real conflict exists, name the upstream symbol/file in `description` and explain the fix in `suggestion`. Otherwise move on. Upstream files are reference only — never report an issue on an upstream file, and never report an issue on a line that is not in `ADDED LINE NUMBERS IN THIS PR`.

        CRITICAL LINE NUMBERING RULES:
        1. Every line in `FULL CHUNKS FROM THIS FILE` is prefixed with its exact line number, e.g. `  18 |     open(file_path, "w").write(content)`.
        2. When reporting an issue, use the exact integer shown to the left of `|` on that specific line (in the example: 18).
        3. NEVER calculate line numbers by counting down from the top of a chunk.
        4. ONLY report issues on lines listed under `ADDED LINE NUMBERS IN THIS PR`. Do not report on unchanged/context lines or on deleted lines.
        5. `file_path` must be the exact changed-file path from its header (`=== FILE: ... ===`).

        ONE FINDING PER ISSUE:
        Report each distinct issue once. If the same problem spans multiple added lines, pick the single most representative added line and describe the span in `description`. Do not emit duplicate findings for adjacent lines.

        SEVERITY:
        - `critical`: crash, data loss, or exploitable security flaw (see security rules).
        - `high`: wrong behavior under realistic input, or serious security risk with uncertain exploitability.
        - `medium`: wrong behavior in edge cases.
        - `low`: maintainability/type-safety concern with no immediate runtime impact.

        SECURITY RULES — DO NOT SOFTEN:
        - `eval()`, `exec()`, `os.system()`, `subprocess` with `shell=True`, `pickle.loads()` / `marshal.loads()` on untrusted data -> MUST be `critical`.
        - `yaml.load()` without `SafeLoader` -> `critical`.
        - `__import__` or `compile()` on untrusted input -> `critical`.
        - SQL built by string concatenation or f-strings -> `critical`.
        - `requests` with `verify=False` -> `high`.
        - `hashlib.md5` / `sha1` used for passwords -> `high`.
        - Hardcoded secrets, tokens, passwords -> `high`.
        This list is not exhaustive — apply the same severity to equivalent dangerous patterns. If a genuinely dangerous pattern is 
        present but exploitability is uncertain, report it as `high` and explain why in the description. Do NOT invent patterns that are not 
        actually present in the reviewed lines; every finding must correspond to real code in the diff.

        GUIDELINES:
        - Be objective, technical, concise.
        - Do not report stylistic, formatting, or linting preferences.
        - Do not invent issues or stretch minor details into false positives. Every finding must point to a real, verifiable flaw on a new or modified line.
        - If there are no meaningful issues on the new/modified lines, return an empty findings list.

        OUTPUT (for each finding):
        - `file_path` — exact changed-file path from its header
        - `line_number` — exact integer from the numbered chunk; must appear in `ADDED LINE NUMBERS IN THIS PR`
        - `category` — one of: bug, security, performance, maintainability
        - `severity` — one of: low, medium, high, critical
        - `title` — short and specific
        - `description` — why it is a problem; cite the upstream symbol/behavior if the issue is an upstream conflict
        - `suggestion` — practical fix

        CHANGED FILES AND CONTEXT:

        {code_context}
      
  """

