import shutil
import subprocess
from pathlib import Path

from app.services.file_service import FileService


class GitService:

    def _run_git(self, cmd: list[str]) -> subprocess.CompletedProcess:
        """Execute Git commands with safe UTF-8 output decoding."""
        return subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

    def clone_repository(
        self,
        repository_url: str,
        destination: Path,
        depth:int | None = 1,
        base_ref: str | None = None,
        head_ref: str | None = None,
    ) -> Path:
        """Clones a remote repository into a target directory.
        
        Performs a shallow clone (--depth 1) for speed and disk optimization.
        Cleans up existing target directories prior to cloning.
        """
        try:

            cmd=["git","clone"]
            if depth is not None and not(base_ref and head_ref):
                cmd.extend(["--depth",str(depth)])

            cmd.extend([repository_url,str(destination)])

            # 3. Execute shallow clone
            self._run_git(cmd)

            if base_ref and head_ref:
                self._run_git(
                    ["git","-C",str(destination),"fetch","origin",base_ref,head_ref]
                )
                # ADD THIS: Check out the head_ref so the files on disk update to the new code
                self._run_git(
                                    ["git","-C",str(destination),"checkout",head_ref],
                                )

            return destination

        except FileNotFoundError as exc:
            raise RuntimeError(
                "Git executable not found. Ensure git is installed and available in system PATH."
            ) from exc
        except subprocess.CalledProcessError as exc:
            # Captures git's stderr (e.g., repository not found, invalid credentials, corrupt network connection)
            error_msg = (exc.stderr or "").strip() or "Unknown git error"
            raise RuntimeError(
                f"Failed to clone repository '{repository_url}': {error_msg}"
            ) from exc

    def get_diff(self, repo_path: Path, base: str, head: str = "HEAD") -> str:

        # Use origin/ prefix if comparing remote refs
        base_ref = base if base.startswith("origin/") else f"origin/{base}"
        head_ref = head if head == "HEAD" or head.startswith("origin/") else f"origin/{head}"
      
        try:
            result = self._run_git(
                ["git", "-C", str(repo_path), "diff", f"{base_ref}...{head_ref}"],
            )
            return result.stdout
        except subprocess.CalledProcessError as exc:
            error_msg = (exc.stderr or "").strip() or "Unknown git error"
            raise RuntimeError(
                f"Failed to diff '{base}...{head}': {error_msg}"
            ) from exc


    def get_head_sha(self, repo_path: Path) -> str:
        out = subprocess.run(["git","-C",str(repo_path),"rev-parse","HEAD"], capture_output=True, text=True, check=True)
        return out.stdout.strip()
    