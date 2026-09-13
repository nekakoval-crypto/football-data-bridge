"""Publish an already committed operational snapshot without overwriting remote work."""
import os
import subprocess
import time


def git(*args, cwd=None, check=True):
    return subprocess.run(["git", *args], cwd=cwd, check=check)


def publish(cwd=None, attempts=3, pause=time.sleep):
    if os.environ.get("GITHUB_REF") != "refs/heads/main":
        raise RuntimeError("Operational publishing requires refs/heads/main")
    for attempt in range(attempts):
        git("fetch", "origin", "main", cwd=cwd)
        result = git("rebase", "origin/main", cwd=cwd, check=False)
        if result.returncode:
            git("rebase", "--abort", cwd=cwd)
            raise RuntimeError("Operational conflict: original commit preserved; inspect run artifact")
        if git("push", "origin", "HEAD:main", cwd=cwd, check=False).returncode == 0:
            return
        if attempt + 1 < attempts:
            pause(2)
    raise RuntimeError("Operational push failed after bounded retries; snapshot preserved")


if __name__ == "__main__":
    publish()
