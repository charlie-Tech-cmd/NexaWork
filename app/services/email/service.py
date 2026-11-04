from abc import ABC, abstractmethod


class EmailDeliveryUnavailable(RuntimeError):
    pass


class EmailService(ABC):
    @abstractmethod
    def ensure_available(self) -> None:
        pass

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
