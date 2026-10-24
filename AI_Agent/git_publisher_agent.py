import os
import subprocess
from pathlib import Path
from typing import Optional


class GitPublisherAgent:
    """
    Agent responsible for publishing generated artifacts to GitHub:
    1. Locates the root Git repository (AIBS_AEL).
    2. Stages the generated Handbook PDF file (git add).
    3. Commits the changes with an informative message (git commit).
    4. Pushes the commit to the remote repository (git push).
    """

    def __init__(self, repo_dir: Optional[str] = None):
        if repo_dir:
            self.repo_dir = Path(repo_dir).resolve()
        else:
            self.repo_dir = Path(__file__).resolve().parent.parent

    def _run_git_command(self, args: list) -> subprocess.CompletedProcess:
        """Executes a git command inside the repository directory."""
        result = subprocess.run(
            ["git"] + args,
            cwd=str(self.repo_dir),
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"Git command failed ('git {' '.join(args)}'):\n{result.stderr.strip()}")
        return result

    def publish_handbook(self, pdf_path: Path, custom_message: Optional[str] = None) -> bool:
        """Adds, commits, pulls remote changes, and pushes the generated PDF to GitHub."""
        resolved_path = pdf_path.resolve()

        if not resolved_path.exists():
            raise FileNotFoundError(f"Handbook file not found at: {resolved_path}")

        print(f"\n[GitPublisherAgent] Preparing to publish: {resolved_path.name}")
        print(f"[GitPublisherAgent] Git root detected at: {self.repo_dir}")

        try:
            rel_path = resolved_path.relative_to(self.repo_dir)

            print(f"[GitPublisherAgent] Staging file: {rel_path}...")
            self._run_git_command(["add", str(rel_path)])

            if custom_message:
                commit_msg = custom_message
            else:
                commit_msg = f"docs(handbook): publish {resolved_path.name}"

            print(f"[GitPublisherAgent] Committing changes...")
            self._run_git_command(["commit", "-m", commit_msg])


            print(f"[GitPublisherAgent] Fetching and merging remote updates...")
            self._run_git_command(["pull", "origin", "main", "--no-rebase"])

            print(f"[GitPublisherAgent] Pushing to remote repository...")
            self._run_git_command(["push", "origin", "main"])

            print(f"[GitPublisherAgent] Successfully published to GitHub into 'handbooks/' folder!\n")
            return True

        except subprocess.SubprocessError as e:
            print(f"[GitPublisherAgent] Error during Git operation: {e}")
            return False
        except Exception as e:
            print(f"[GitPublisherAgent] Unexpected error: {e}")
            return False


if __name__ == "__main__":
    root_dir = Path(__file__).resolve().parent.parent
    handbooks_dir = root_dir / "handbooks"

    if handbooks_dir.exists():
        pdf_files = list(handbooks_dir.glob("*.pdf"))
        if pdf_files:
            latest_pdf = max(pdf_files, key=os.path.getmtime)
            publisher = GitPublisherAgent()
            publisher.publish_handbook(latest_pdf)
        else:
            print(f"No PDF files found in {handbooks_dir} to publish.")
    else:
        print(f"Directory {handbooks_dir} does not exist.")