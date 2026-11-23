from app.services.git_service import GitService
from app.services.file_service import FileService
from app.services.context_service import ContextService
from app.services.ast_service import ASTService
from app.services.dependancy_service import DependencyService
from pathlib import Path
from tempfile import TemporaryDirectory
from app.services.diff_parser import parse_diff


git = GitService()
file_service=FileService()
context_service=ContextService(dependancy_service=DependencyService(ASTService()),ast_service=ASTService())

with TemporaryDirectory() as temp_dir:
    repo=Path(temp_dir) / "DA_repo"

    git.clone_repository("https://github.com/harshavardhan-data/agentic-ai-playground",repo,base_ref='main',head_ref='test/my_experiment')

    diff=git.get_diff(repo,base="main",head="test/my_experiment")


    parsed_diff=parse_diff(diff)
    changed_paths={file.path for file in parsed_diff}
    file_contexts=file_service.build_file_context(repository_path=repo,only_paths=changed_paths)
    print(f"Extracted File Contexts {[file.path for file in file_contexts]}  \n len = {len(file_contexts)}")
    selected_context=context_service.select_context(file_contexts,changed_paths=changed_paths)
    # print(parsed_diff)
    # print(f"{len(parsed_diff)} files changed\n")

    # for file in parsed_diff[:10]:
    #     print(f"{file.path}  ({len(file.added_lines)} added lines)")
    #     print(f" lines: {sorted(file.added_lines)[:10]}")