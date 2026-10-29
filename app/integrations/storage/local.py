"""Private local adapter. Keys are generated identifiers, never client filenames."""
import os
import re
from pathlib import Path
from typing import BinaryIO


class LocalStorage:
    def __init__(self, root: str):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)

    def path(self, key: str) -> Path:
        if not re.fullmatch(r"[a-f0-9]{32}", key):
            raise ValueError("Invalid storage key")
        return self.root / key

    def create(self, key: str) -> BinaryIO:
        return os.fdopen(
            os.open(self.path(key), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600),
            "wb",
        )

    def open(self, key: str) -> BinaryIO:
        return os.fdopen(os.open(self.path(key), os.O_RDONLY | os.O_NOFOLLOW), "rb")

    def delete(self, key: str) -> None:
        self.path(key).unlink(missing_ok=True)
