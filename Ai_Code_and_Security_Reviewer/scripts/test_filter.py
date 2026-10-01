from pathlib import Path
from app.services.ast_service import ASTService
from app.services.dependancy_service import DependencyService
from app.services.context_service import ContextService
from app.services.file_service import FileService
from app.services.git_service import GitService
from tempfile import TemporaryDirectory

ast=ASTService()
ctx=ContextService(ast,DependencyService(ast))
fs=FileService()
gt=GitService()

repo_url="https://github.com/harshavardhan-data/agentic-ai-playground/"

with TemporaryDirectory() as temp_dir:

    temp_path=Path(temp_dir)

    cloned_repo=gt.clone_repository(repo_url,destination=temp_path/"cloned_DA")


    contexts = fs.build_file_context(cloned_repo)

    # pick one file to "change"
    # use a real path from your output
    changed= {r"data_agent_project\agents\master_agent.py",
            r"data_agent_project\agents\sql_coder.py",
            r"data_agent_project\agents\sql_critic.py"}

    all_chunks = ctx.select_context(contexts)
    filtered = ctx.select_context(contexts, changed_paths=changed)

    print("no filter :", len(all_chunks), "chunks from",
        len({c.file_path for c in all_chunks}), "files")
    print("filtered  :", len(filtered), "chunks from",
        len({c.file_path for c in filtered}), "files")
    print("files kept:", sorted({c.file_path for c in filtered}))


print("Deleted Temp Successfully")