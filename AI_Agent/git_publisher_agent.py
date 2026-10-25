import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional


class GitPublisherAgent:
    """Publish only a selected PDF from a clean copy of the remote branch.

    The user's local commits, index and working files are never merged or pushed.
    """
    def __init__(self, repo_dir: Optional[str] = None):
        self.repo_dir = Path(repo_dir).resolve() if repo_dir else Path(__file__).resolve().parent.parent

    def _run_git_command(self, args, cwd=None):
        result = subprocess.run(['git'] + list(args), cwd=str(cwd or self.repo_dir),
                                capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=180)
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip())
        return result

    def publish_handbook(self, pdf_path: Path, custom_message: Optional[str] = None) -> bool:
        try:
            source = Path(pdf_path).resolve(strict=True)
            relative = source.relative_to(self.repo_dir)
            if relative.parts[0] != 'handbooks' or source.suffix.lower() != '.pdf':
                raise ValueError('Only PDF files inside this project\'s handbooks directory may be published.')
            remote = self._run_git_command(['remote', 'get-url', 'origin']).stdout.strip()
            branch = 'main'
            self._run_git_command(['ls-remote', '--exit-code', remote, 'refs/heads/' + branch])
            name = self._run_git_command(['config', 'user.name']).stdout.strip()
            email = self._run_git_command(['config', 'user.email']).stdout.strip()
            if not name or not email:
                raise ValueError('Configure git user.name and user.email before publishing.')
            # TemporaryDirectory owns a newly created directory under the OS temp root.
            with tempfile.TemporaryDirectory(prefix='aibs-handbook-publish-') as tmp:
                checkout = Path(tmp) / 'repo'
                print('[GitPublisherAgent] Fetching current remote main in an isolated checkout...')
                self._run_git_command(['clone', '--depth', '1', '--single-branch', '--branch', branch, remote, str(checkout)])
                target = checkout / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists() and target.read_bytes() == source.read_bytes():
                    print('[GitPublisherAgent] This PDF is already published; no changes needed.')
                    return True
                if target.exists():
                    raise ValueError('A different PDF already exists under this name. Use a new filename.')
                shutil.copy2(source, target)
                rel = relative.as_posix()
                self._run_git_command(['add', '--', rel], checkout)
                staged = self._run_git_command(['diff', '--cached', '--name-only'], checkout).stdout.splitlines()
                if staged != [rel]:
                    raise RuntimeError('Unexpected files staged; publication stopped.')
                self._run_git_command(['-c', 'user.name=' + name, '-c', 'user.email=' + email,
                                       'commit', '-m', custom_message or f'docs(handbook): publish {source.name}', '--', rel], checkout)
                self._run_git_command(['push', 'origin', 'HEAD:refs/heads/' + branch], checkout)
                print('[GitPublisherAgent] Successfully published only ' + rel)
                return True
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
            print('[GitPublisherAgent] Publication failed: ' + str(exc))
            print('[GitPublisherAgent] Local PDF is retained. Check origin, GitHub authentication and branch permissions, then retry.')
            return False


if __name__ == '__main__':
    root = Path(__file__).resolve().parent.parent
    files = list((root / 'handbooks').glob('*.pdf'))
    if not files:
        print('No PDF files found in handbooks.')
    else:
        raise SystemExit(0 if GitPublisherAgent().publish_handbook(max(files, key=os.path.getmtime)) else 1)
