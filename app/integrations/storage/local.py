"""Private local adapter with atomic publication of completed objects."""
import os
import re
import tempfile
from pathlib import Path
from typing import BinaryIO


class LocalStorageWriter:
    """Write to a private staging file, then publish without overwriting."""

    def __init__(
        self,
        stream: BinaryIO,
        staging_path: str,
        destination: Path,
    ):
        self._staging_path = Path(staging_path)
        self._destination = destination
        self._stream: BinaryIO | None = stream
        self._state = "open"

    def write(self, data: bytes) -> int:
        if self._state != "open" or self._stream is None:
            raise ValueError("Storage writer is no longer open")
        return self._stream.write(data)

    def complete(self) -> None:
        if self._state != "open" or self._stream is None:
            raise ValueError("Storage writer is no longer open")

        stream = self._stream
        try:
            stream.flush()
            os.fsync(stream.fileno())
            stream.close()
            self._stream = None

            # Atomic and exclusive: an existing destination is never overwritten.
            os.link(self._staging_path, self._destination, follow_symlinks=False)
            self._state = "completed"
            self._staging_path.unlink()
        except BaseException as original:
            if self._state != "completed":
                try:
                    self.abort()
                except BaseException as cleanup_error:
                    raise original from cleanup_error
            raise

    def abort(self) -> None:
        if self._state == "aborted":
            return

        # Also remove a leftover staging link if publication already succeeded.
        stream, self._stream = self._stream, None
        try:
            if stream is not None:
                stream.close()
        finally:
            self._staging_path.unlink(missing_ok=True)

        # Mark aborted only after both closing and staging cleanup succeed.
        self._state = "aborted"


class LocalStorage:
    def __init__(self, root: str):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)

    def path(self, key: str) -> Path:
        if not re.fullmatch(r"[a-f0-9]{32}", key):
            raise ValueError("Invalid storage key")
        return self.root / key

    def create(self, key: str) -> LocalStorageWriter:
        destination = self.path(key)

        fd, staging_path = tempfile.mkstemp(
            prefix=".staging-",
            dir=self.root,
        )
        stream = None
        try:
            stream = os.fdopen(fd, "wb")
            return LocalStorageWriter(stream, staging_path, destination)
        except BaseException:
            if stream is not None:
                stream.close()
            else:
                os.close(fd)
            Path(staging_path).unlink(missing_ok=True)
            raise

    def open(self, key: str) -> BinaryIO:
        return os.fdopen(os.open(self.path(key), os.O_RDONLY | os.O_NOFOLLOW), "rb")

    def delete(self, key: str) -> None:
        self.path(key).unlink(missing_ok=True)
