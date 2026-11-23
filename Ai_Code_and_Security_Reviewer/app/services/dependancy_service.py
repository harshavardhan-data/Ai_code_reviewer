from collections import defaultdict
from pathlib import Path

from app.schemas.file import FileContext
from app.services.ast_service import ASTService,ImportRef


class DependencyService:

    def __init__(self,ast_service:ASTService):
        self.ast_service = ast_service

    def _path_to_module_key(self, path: str) -> str:
        # "app/utils.py" -> "app.utils"; "app/__init__.py" -> "app"
        p = Path(path).with_suffix("")
        if p.name == "__init__":
            p = p.parent
        return ".".join(p.parts)

    def resolve_import_target(
        self,
        ref: ImportRef,
        importer_path: str,
        module_index: dict[str, set[str]],
    ) -> set[str]:
        """Resolve an ImportRef from importer_path to upstream file path(s)."""
        if ref.level == 0:
            return module_index.get(ref.module, set())

        base = Path(importer_path).parent
        for _ in range(ref.level - 1):
            base = base.parent

        hits: set[str] = set()

        if ref.module:
            # from ..foo.bar import x  -> base/foo/bar
            rel = (base / ref.module.replace(".", "/")).as_posix()
            hits |= module_index.get(self._path_to_module_key(rel), set())
        else:
            # from . import x  -> x may be a sibling module
            for name in (ref.names or ()):
                rel = (base / name).as_posix()
                hits |= module_index.get(self._path_to_module_key(rel), set())

        return hits

    def _module_candidates(self, file_path: str|Path) -> set[str]:
        path = Path(file_path).with_suffix("")

        parts = list(path.parts)
        if not parts:
            return set()
        if parts[-1] == "__init__":
            parts.pop()

        candidates = set()

        # Full module path + suffix aliases.
        # Example:
        # data_agent_project.core.memory
        # core.memory
        for index in range(len(parts)):
            candidate = ".".join(parts[index:])

            if candidate.count(".") >= 1:
                candidates.add(candidate)

        return candidates

    def build_module_index(
        self,
        file_contexts: list[FileContext],
    ) -> dict[str, set[str]]:

        module_index: dict[str, set[str]] = defaultdict(set)

        for file in file_contexts:
            for module in self._module_candidates(file.path):
                module_index[module].add(file.path)

        return dict(module_index)

    def build_resolution_index(self,file_paths:list[Path],repo_path:str) -> dict[str, set[str]]:
    
        module_index: dict[str, set[str]] = defaultdict(set)
    
        for file_path in file_paths:
            rel_path=(file_path.relative_to(repo_path)).as_posix() if repo_path else file_path.as_posix()
            for module in self._module_candidates(file_path):
                module_index[module].add(rel_path)

        return dict(module_index)

    def build_dependency_scores(
        self,
        changed_file_contexts: list[FileContext],
        all_module_index: dict[str,set[str]],
    ) -> dict[str, int]:

        
        dependency_scores :dict[str,int]=defaultdict(int)

        for file in changed_file_contexts:

            # A file should contribute at most once to a dependency.
            resolved_targets = set()

            for ref in self.ast_service.extract_imports(file.content):

                if ref.level != 0:
                    continue  # Handle relative imports separately later.

                targets = all_module_index.get(
                    ref.module,
                    set(),
                )

                # Only resolve unambiguous local imports.
                if len(targets) != 1:
                    continue

                target = next(iter(targets))

                if target == file.path:
                    continue

                resolved_targets.add(target)

            for target in resolved_targets:
                dependency_scores[target] += 1
        

        return dict(dependency_scores)