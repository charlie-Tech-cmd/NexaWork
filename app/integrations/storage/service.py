"""Private streaming storage seam; authorization belongs to application services."""
from typing import BinaryIO, Protocol


class StorageService(Protocol):
    def create(self, key: str) -> BinaryIO:
        """Create a new private object exclusively; never overwrite an existing key."""
        ...

    def open(self, key: str) -> BinaryIO:
        """Open an object for bounded reads. Caller owns closing the stream."""
        ...

    def delete(self, key: str) -> None:
        """Idempotently remove an object. Missing objects count as success."""
        ...
