import os
import pytest
from app.services.github_service import GitHubService
from app.schemas.finding import FindingCreate
from app.services.git_service import GitService
from dotenv import load_dotenv

# git_service=GitService()
# git_service.get_head_sha()

# load_dotenv()

OWNER="harshavardhan-data"
REPO="agentic-ai-playground"
PR_NUMBER=1
COMMIT_ID="735355ebbe8046b620e414502c2192b7fd79c076"




@pytest.mark.skipif(not os.getenv("GITHUB_TOKEN"), reason="no token")
def test_post_inline_comment():
    gh=GitHubService(os.environ["GITHUB_TOKEN"])


    findings=[
        FindingCreate(
            file_path="data_agent_project/models/pricing_service.py",          # a file that IS in the PR diff
            line_number=28,                  # a line that IS in added_lines of that file
            category="maintainability",
            severity="low",
            title="Test inline comment /Performance Issue",
            description="N+1 database query when accessing item.category.",
            suggestion=None,
        )
    ]


    result=gh.post_review(OWNER,REPO,PR_NUMBER,COMMIT_ID,findings)
    print(result)
    assert "id" in result