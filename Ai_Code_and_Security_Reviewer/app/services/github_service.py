import requests
from app.schemas.finding import FindingCreate
import os
from dotenv import load_dotenv




class GitHubService:
    def __init__(self, token: str|None=None):
        raw_token = token if token is not None else os.environ.get("GITHUB_TOKEN")
        self.token = raw_token.strip() if raw_token else ""
        if not self.token:
            raise ValueError("GITHUB_TOKEN is missing or empty")
        self.base = "https://api.github.com"

    def post_review(
        self,
        owner: str,
        repo: str,
        pull_number: int,
        commit_id: str,
        findings: list[FindingCreate],
        summary: str = "Automated review by AI Code Reviewer",
    ) -> dict:
        # findings must already be filtered to added_lines (you do that before calling)
        comments = [
            {
                "path": f.file_path,
                "line": f.line_number,
                "side": "RIGHT",
                "body": self._format_body(f),
            }
            for f in findings
            if f.line_number is not None
        ]
        if not comments:
            return {"skipped": True, "reason": "no findings with line numbers"}

        resp = requests.post(
            f"{self.base}/repos/{owner}/{repo}/pulls/{pull_number}/reviews",
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            json={
                "commit_id": commit_id,
                "event": "COMMENT",
                "body": summary,
                "comments": comments,
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def _format_body(f: FindingCreate) -> str:
        body = f"**[{f.severity.upper()}] {f.title}**\n\n{f.description}"
        if f.suggestion:
            body += f"\n\n**Suggestion:** {f.suggestion}"
        return body