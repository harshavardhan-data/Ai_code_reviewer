from app.db import SessionLocal
from app.repositories.review_repository import ReviewRepository
from app.models.db_review import Review
from app.models.db_finding import Finding
from app.schemas.review import ReviewCreate
from tempfile import TemporaryDirectory
from pathlib import Path
from app.services.git_service import GitService
from app.services.file_service import FileService
from app.services.ai_service import AIService
from app.services.context_service import ContextService
from app.services.dependancy_service import DependencyService
from app.services.diff_parser import parse_diff
from app.services.github_service import GitHubService
import re


class ReviewService:

    def __init__(self,git_service:GitService,
                 file_service:FileService,
                 ai_service:AIService,
                 context_service:ContextService,
                 dependancy_service:DependencyService,
                 github_service:GitHubService|None=None,
                 ):
        self.git_service=git_service
        self.file_service=file_service
        self.ai_service=ai_service
        self.context_service=context_service
        self.dependancy_service=dependancy_service
        self.github_service=github_service
    

    def list_reviews(self) -> list[Review]:
        with SessionLocal() as session:
            return ReviewRepository(session).get_all_reviews()

    def create_new_review(self, data: ReviewCreate) -> Review:
        with SessionLocal() as session:
            return ReviewRepository(session).create_review(str(data.repository_url),data.pr_number)

    def get_review_by_id(self, review_id: int) -> Review | None:
        with SessionLocal() as session:
            return ReviewRepository(session).get_by_id(review_id)

    def get_findings(self, review_id: int) -> list[Finding]:
        with SessionLocal() as session:
            return ReviewRepository(session).get_findings(review_id)

    def _parse_owner_repo(self,url: str) -> tuple[str, str]:
            m = re.match(r"https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$", url)
            if not m:
                raise ValueError(f"Not a GitHub repo URL: {url}")
            return m.group(1), m.group(2)


    def process_review_in_background(self,review_id:int,repository_url:str,
                                     base_ref:str|None =None,
                                     head_ref:str|None=None,
                                     pr_number:str|None=None):

        with SessionLocal() as session:
            repo = ReviewRepository(session)
            repo.update_status(review_id, "processing")
            print(f"\n[BACKGROUND] Started processing review #{review_id} for {repository_url}")

            try:
                with TemporaryDirectory() as temp_dir:
                    repository_path = Path(temp_dir) / "repo"

                    is_pr_mode=bool(base_ref and head_ref)
                    self.git_service.clone_repository(repository_url, repository_path,depth=1 if not is_pr_mode else None,
                                                      base_ref=base_ref,head_ref=head_ref)
                    changed_paths=None
                    changed_files=None
                    if is_pr_mode:
                        raw_diff=self.git_service.get_diff(repository_path,base=base_ref,head=head_ref)
                        changed_files=parse_diff(raw_diff)
                        changed_paths={file.path for file in changed_files}
                        print(f"[DEBUG] Raw diff string length: {len(raw_diff)}")
                        print(f"[DEBUG] Parsed changed_files count: {len(changed_files)}")
                        print(f"[DEBUG] changed_paths content: {changed_paths}")

                        for f in changed_files:
                            print(f"[DEBUG] File: {f.path}, Added Lines: {sorted(list(f.added_lines))}")
                        
                    file_contexts=None

                    if changed_paths:
                        all_file_paths=self.file_service.find_source_files(repository_path=repository_path)
                        all_module_index=self.dependancy_service.build_resolution_index(file_paths=all_file_paths,repo_path=repository_path)
                        changed_file_contexts = self.file_service.build_file_context(repository_path,only_paths=changed_paths)
                        extended_paths=set(changed_paths)

                        upstream_names: dict[str, set[str] | None] = {}
                        dependancy_scores = self.dependancy_service.build_dependency_scores(
                        changed_file_contexts, all_module_index
                        ) 
                        
                        for file in changed_file_contexts:
                            for ref_import in self.context_service.ast_service.extract_imports(file.content):
                                targets=self.dependancy_service.resolve_import_target(ref_import,file.path,all_module_index)
                                for t in targets:
                                    if t == file.path:
                                        continue
                                    extended_paths.add(t)
                                    if t in upstream_names and upstream_names[t] is None:
                                        continue
                                    if ref_import.names is None:
                                        upstream_names[t] = None
                                    else:
                                        upstream_names.setdefault(t, set()).update(ref_import.names)
                        print('Extended Paths ===================')
                        print(extended_paths-changed_paths)
                        extended_file_contexts=self.file_service.build_file_context(repository_path,extended_paths-changed_paths)
                        print(f"Extended Files : {[f.path for f in extended_file_contexts]}")
                        file_contexts=list(changed_file_contexts)+list(extended_file_contexts)
                    else:
                        file_contexts = self.file_service.build_file_context(repository_path)
                    selected_file_contexts = self.context_service.select_context(file_contexts,changed_paths=changed_paths,
                                                                                 upstream_names=upstream_names if changed_paths else None,
                                                                                 dependancy_scores=dependancy_scores if changed_paths else None)
                    
                    
                    print(f"Collected {len(file_contexts)} items from the repo")
                    print(f"Collected Exclusively {len({file.file_path for file in selected_file_contexts})} Files")
    
                    review_findings = self.ai_service.review_code(selected_file_contexts,changed_files=changed_files)
                    if changed_files is not None:
                        added_by_file={f.path:f.added_lines for f in changed_files}
                        review_findings.findings=[
                            f for f in review_findings.findings
                            if f.line_number is not None and
                            f.line_number in added_by_file.get(f.file_path,set())
                        ]
                    repo.create_findings(review_id=review_id, findings_data=review_findings)
                    try:
                        head_sha = self.git_service.get_head_sha(repository_path)
                        repo.update_commit_id(review_id,head_sha)
                    except Exception as exc:
                        print(f"Failed to generate commit_id {exc!r}")
                    repo.update_status(review_id, "completed")
                    print(f"[BACKGROUND] Review #{review_id} COMPLETED successfully!\n")
                    print(review_findings)
        
                  
                   
                    if is_pr_mode and pr_number:  # or pass pr_number through
                        owner, repo_name = self._parse_owner_repo(repository_url)
                        try:
                            gh=self.github_service or GitHubService()
                            gh.post_review(
                                owner, repo_name, pr_number, head_sha, review_findings.findings
                            )
                        except Exception as exc:
                            print(f"[BACKGROUND] GitHub inline comment failed: {exc!r}")
                            # do NOT fail the whole review for a comment failure                   
            except Exception as exc:
                session.rollback()
                try:
                    repo.update_status(review_id, "failed")
                except Exception as db_exc:
                    print(f"[BACKGROUND] Could not mark #{review_id} failed: {db_exc!r}")
                print(f"[BACKGROUND] Review #{review_id} FAILED: {exc!r}")
                    # intentionally NO raise — background tasks must not propagate


