from app.services.git_service import GitService
from pathlib import Path
from tempfile import TemporaryDirectory
from app.services.diff_parser import parse_diff


git = GitService()

with TemporaryDirectory() as temp_dir:
    repo=Path(temp_dir) / "DA_repo"

    git.clone_repository("https://github.com/PyCQA/bandit",repo)

    diff=git.get_diff(repo,base="HEAD~5",head="HEAD")


    parsed_diff=parse_diff(diff)

    print(f"{len(parsed_diff)} files changed\n")

    for file in parsed_diff[:10]:
        print(f"{file.path}  ({len(file.added_lines)} added lines)")
        print(f" lines: {sorted(file.added_lines)[:10]}")