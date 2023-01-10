"""Interact with github pages."""
from __future__ import annotations
from pathlib import Path
from queue import Queue
import shutil
from tempfile import TemporaryDirectory
import threading
import time

import appdirs
from github import Github
from git import Repo, GitCommandError
from .utils import DBSettings, background


class GHPages:
    """Create a git hub page to display statistics on a static public
    web pages."""

    def __init__(self, db_settings: DBSettings):

        self._settings = db_settings.db_settings
        self._gh = None
        self._gh_repo = None
        self._gh_user_name = None
        self._gh_user_email = None
        self._lock = threading.Lock()
        self._item_queue = Queue(maxsize=1)

        if self.use_gh_pages:
            self._init_gh_repo()

    @property
    def repo_dir(self):
        return Path(appdirs.user_cache_dir()) / self._settings.get(
            "db_name", "baby_measure"
        )

    def _init_gh_repo(self):
        self._gh = Github(self._settings["gh_token"])
        gh_user = self._gh.get_user()
        self._gh_user_name = gh_user.login or ""
        self._gh_user_email = gh_user.email or ""
        repos = [r.name for r in gh_user.get_repos()]
        if self._settings["gh_repo"] not in repos:
            print(f"Creating user repository {self._settings['gh_repo']}")
            gh_user.create_repo(self._settings["gh_repo"])
        self._gh_repo = gh_user.get_repo(self._settings["gh_repo"])

    def _commit(self, repo_dir: Path) -> None:
        favicon = Path(__file__).parent / "assets" / "favicon.ico"
        print("Commiting file to repo")
        Repo.clone_from(self._gh_repo.ssh_url, repo_dir)
        repo = Repo(repo_dir)
        for file in self.repo_dir.rglob("*.html"):
            shutil.copy(file, repo_dir / file.name)
        if not (repo_dir / "favicon.ico").exists():
            shutil.copy(favicon, repo_dir / "favicon.ico")
        repo.git.execute(["git", "config", "user.email", self._gh_user_email])
        repo.git.execute(["git", "config", "user.name", self._gh_user_name])
        repo.git.execute(["git", "checkout", "--orphan", "latest_branch"])
        repo.git.execute(["git", "add", "-A"])
        repo.git.execute(["git", "commit", "-am", "Add files"])
        try:
            repo.git.execute(["git", "branch", "-D", "main"])
        except GitCommandError:
            pass
        repo.git.execute(["git", "branch", "-m", "main"])
        repo.git.execute(["git", "checkout", "main"])
        repo.git.execute(["git", "push", "-f", "origin", "main"])
        time.sleep(15)

    @background
    def commit(self):
        if self.use_gh_pages and self._item_queue.empty():
            with self._lock:
                self._item_queue.put("block")
                with TemporaryDirectory() as repo_dir:
                    self._commit(Path(repo_dir))
                _ = self._item_queue.get()

    @property
    def use_gh_pages(self) -> bool:
        """Check if git hub pages should be used."""
        if self._settings.get("gh_repo", ""):
            return True
        return False
