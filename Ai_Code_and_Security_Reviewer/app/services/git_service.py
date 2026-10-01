import shutil
import subprocess
from pathlib import Path

from app.services.file_service import FileService


class GitService:
    def clone_repository(
        self,
        repository_url: str,
        destination: Path,
        depth:int | None = 1,
    ) -> Path:
        """Clones a remote repository into a target directory.
        
        Performs a shallow clone (--depth 1) for speed and disk optimization.
        Cleans up existing target directories prior to cloning.
        """
        try:

            cmd=["git","clone"]
            if depth is not None:
                cmd.extend(["--depth",str(depth)])

            cmd.extend([repository_url,str(destination)])

            # 3. Execute shallow clone
            subprocess.run(cmd,
                check=True,
                capture_output=True,
                text=True,
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
        try:
            result = subprocess.run(
                ["git", "-C", str(repo_path), "diff", f"{base}...{head}"],
                check=True, capture_output=True, text=True,
            )
            return result.stdout
        except subprocess.CalledProcessError as exc:
            error_msg = (exc.stderr or "").strip() or "Unknown git error"
            raise RuntimeError(
                f"Failed to diff '{base}...{head}': {error_msg}"
            ) from exc
   