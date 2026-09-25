from typing import Protocol


class StorageService(Protocol):
    def upload(
        self,
        file_data: bytes,
        object_name: str,
        content_type: str,
    ) -> str:
        ...

    def delete(self, object_name: str) -> None:
        ...

    def get_url(self, object_name: str) -> str:
        ...
