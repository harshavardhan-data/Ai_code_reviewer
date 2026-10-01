from collections import defaultdict
from pathlib import Path

from app.schemas.file import FileContext
from app.services.ast_service import ASTService


class DependencyService:

    def __init__(self,ast_service:ASTService):
        self.ast_service = ast_service

    def _module_candidates(self, file_path: str) -> set[str]:
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

    def build_dependency_scores(
        self,
        file_contexts: list[FileContext],
    ) -> dict[str, int]:

        module_index = self.build_module_index(file_contexts)

        dependency_scores = {
            file.path: 0
            for file in file_contexts
        }

        total_imports = 0
        resolved_imports = 0

        for file in file_contexts:

            imports = self.ast_service.extract_imports(
                file.content
            )

            # A file should contribute at most once to a dependency.
            resolved_targets = set()

            for imported_module, level in imports:

                if level != 0:
                    continue  # Handle relative imports separately later.

                total_imports += 1

                targets = module_index.get(
                    imported_module,
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
                resolved_imports += 1

        resolution_rate = (
            resolved_imports / total_imports
            if total_imports
            else 1.0
        )

        metrics = {
            "total_imports": float(total_imports),
            "resolved_imports": float(resolved_imports),
            "resolution_rate": resolution_rate,
        }
        for key,val in metrics.items():
            print(f"{key} : {val}")

        return dependency_scores