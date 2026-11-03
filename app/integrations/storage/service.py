"""Private streaming storage seam; authorization belongs to application services."""
from typing import BinaryIO, Protocol


class StorageWriter(Protocol):
    def write(self, data: bytes) -> int:
        """Write a chunk to an unpublished private object."""
        ...

    def complete(self) -> None:
        """Publish the fully written object."""
        ...

    def abort(self) -> None:
        """Discard an unpublished object. Safe to call more than once."""
        ...


class StorageService(Protocol):
    def create(self, key: str) -> StorageWriter:
        """Create a new private object exclusively; never overwrite an existing key."""
        ...

    def open(self, key: str) -> BinaryIO:
        """Open an object for bounded reads. Caller owns closing the stream."""
        ...

    def delete(self, key: str) -> None:
        """Idempotently remove an object. Missing objects count as success."""
        ...
