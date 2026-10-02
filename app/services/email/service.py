from abc import ABC, abstractmethod


class EmailService(ABC):
    @abstractmethod
    def send(
        self,
        *,
        recipient: str,
        subject: str,
        body: str,
    ) -> None:
        """Send an email message."""
        raise NotImplementedError
