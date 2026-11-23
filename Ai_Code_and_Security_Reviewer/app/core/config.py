import os
from dotenv import load_dotenv

load_dotenv(override=True)

GEMINI_API_KEY=os.getenv('GEMINI_API_KEY')

if not GEMINI_API_KEY:
    raise RuntimeError("Gemini Api Key is not configured")
else:
    print("SUCCESS")

def _initialize_git():
    key=os.environ.get("GITHUB_TOKEN")

    return key

git_key=_initialize_git()