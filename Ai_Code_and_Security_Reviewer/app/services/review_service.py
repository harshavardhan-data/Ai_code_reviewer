from sqlalchemy.orm import Session
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
from app.services.diff_parser import parse_diff


class ReviewService:

    def __init__(self,git_service:GitService,
                 file_service:FileService,
                 ai_service:AIService,
                 context_service:ContextService
                 ):
        self.git_service=git_service
        self.file_service=file_service
        self.ai_service=ai_service
        self.context_service=context_service

    def list_reviews(self) -> list[Review]:
        with SessionLocal() as session:
            return ReviewRepository(session).get_all_reviews()

    def create_new_review(self, data: ReviewCreate) -> Review:
        with SessionLocal() as session:
            return ReviewRepository(session).create_review(str(data.repository_url))

    def get_review_by_id(self, review_id: int) -> Review | None:
        with SessionLocal() as session:
            return ReviewRepository(session).get_by_id(review_id)

    def get_findings(self, review_id: int) -> list[Finding]:
        with SessionLocal() as session:
            return ReviewRepository(session).get_findings(review_id)


    def process_review_in_background(self,review_id:int,repository_url:str,
                                     base_ref:str|None =None,
                                     head_ref:str|None=None):

        with SessionLocal() as session:
            repo = ReviewRepository(session)
            repo.update_status(review_id, "processing")
            print(f"\n[BACKGROUND] Started processing review #{review_id} for {repository_url}")

            try:
                with TemporaryDirectory() as temp_dir:
                    repository_path = Path(temp_dir) / "repo"

                    is_pr_mode=bool(base_ref and head_ref)
                    self.git_service.clone_repository(repository_url, repository_path,depth=1 if not is_pr_mode else 50)
                    changed_paths=None
                    changed_files=None
                    if is_pr_mode:
                        raw_diff=self.git_service.get_diff(repository_path,base=base_ref,head=head_ref)
                        changed_files=parse_diff(raw_diff)
                        changed_paths={file.path for file in changed_files}
                        print(f"[DEBUG] Raw diff string length: {len(raw_diff)}")
                        print(f"[DEBUG] Parsed changed_files count: {len(changed_files)}")
                        print(f"[DEBUG] changed_paths content: {changed_paths}")

                    file_contexts = self.file_service.build_file_context(repository_path,only_paths=changed_paths)
                    selected_file_contexts = self.context_service.select_context(file_contexts,changed_paths=changed_paths)
                    print(f"Collected {len(file_contexts)} items from the repo")
                    print(f"Collected Exclusively {len({file.file_path for file in selected_file_contexts})} Files")

                    # review_findings = self.ai_service.review_code(selected_file_contexts,changed_files=changed_files)
                    # if changed_files is not None:
                    #     added_by_file={f.path:f.added_lines for f in changed_files}
                    #     review_findings.findings=[
                    #         f for f in review_findings.findings
                    #         if f.line_number is not None and
                    #         f.line_number in added_by_file.get(f.file_path,set())
                    #     ]
                    # repo.create_findings(review_id=review_id, findings_data=review_findings)
                    repo.update_status(review_id, "completed")
                    print(f"[BACKGROUND] Review #{review_id} COMPLETED successfully!\n")

            except Exception as exc:
                session.rollback()
                try:
                    repo.update_status(review_id, "failed")
                except Exception as db_exc:
                    print(f"[BACKGROUND] Could not mark #{review_id} failed: {db_exc!r}")
                print(f"[BACKGROUND] Review #{review_id} FAILED: {exc!r}")
                    # intentionally NO raise — background tasks must not propagate


