from pathlib import Path
from app.services.file_service import FileService
from app.services.ast_service import ASTService
from app.services.dependancy_service import DependencyService
from app.services.context_service import ContextService

REPO = Path(__file__).resolve().parents[1] / "fixtures" / "sample_repo"

def test_context_pipeline():
    fs = FileService()
    ast = ASTService()
    dep = DependencyService(ast)
    ctx = ContextService(ast, dep)

    changed_paths = {"app/foo.py"}
    changed_fcs = fs.build_file_context(REPO, only_paths=changed_paths)

    all_paths = fs.find_source_files(REPO)
    all_index = dep.build_resolution_index(all_paths, REPO)

    extended_paths = set(changed_paths)
    upstream_names: dict[str, set[str] | None] = {}

    scores=dep.build_dependency_scores(changed_fcs,all_index)

    for fc in changed_fcs:
        for ref in ast.extract_imports(fc.content):
            for t in dep.resolve_import_target(ref, fc.path, all_index):
                if t == fc.path:
                    continue
                extended_paths.add(t)
                if t in upstream_names and upstream_names[t] is None:
                    continue
                if ref.names is None:
                    upstream_names[t] = None
                else:
                    upstream_names.setdefault(t, set()).update(ref.names)

    print("extended:", extended_paths - changed_paths)
    print("upstream_names:", upstream_names)
    assert "app/utils.py" in extended_paths
    # assert upstream_names.get("app/utils.py") == {"UserRepository"}

    upstream_fcs = fs.build_file_context(REPO, only_paths=extended_paths - changed_paths)
    all_fcs = changed_fcs + upstream_fcs

    selected = ctx.select_context(all_fcs, changed_paths, upstream_names,scores)

    got = {(c.file_path, c.name) for c in selected}
    # for trip in selected:
    #     print(trip.file_path,trip.name)
    #     print("Content : ")
    #     print(trip.content)
    
    print("selected:", got)

    # changed file: all chunks kept
    assert ("app/foo.py", "login") in got
    assert ("app/foo.py", "unrelated") in got
    # assert ("app/foo2.py", "make_repo") in got

    # upstream file: only imported symbol kept
    assert ("app/utils.py", "hash_password") in got
    assert ("app/utils.py", "delete_file") not in got
    assert ("app/utils.py", "UserRepository") in got