"""Bounded validation and ClamAV INSTREAM scanning; never execute uploaded content."""
import socket
import struct
import time
import unicodedata
from pathlib import Path
from typing import BinaryIO

TYPES = {
    ".txt": "text/plain",
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


class FileRejected(ValueError):
    pass


def safe_filename(value: str) -> str:
    value = unicodedata.normalize("NFC", value).strip()
    if not value or len(value) > 200 or any(c in value for c in (
        "/",
        "\\",
    )) or any(unicodedata.category(c).startswith("C") for c in value):
        raise FileRejected("Use a filename of 1–200 characters without paths or control characters")
    if Path(value).suffix.lower() not in TYPES or value.startswith("."):
        raise FileRejected("Supported files: TXT, PDF, PNG and JPEG")
    return value


def validate_content(stream: BinaryIO, filename: str) -> str:
    stream.seek(0)
    header = stream.read(1024)
    suffix = Path(filename).suffix.lower()
    if suffix == ".txt":
        import codecs
        decoder = codecs.getincrementaldecoder("utf-8")()
        stream.seek(0)
        try:
            while chunk := stream.read(65536):
                text = decoder.decode(chunk)
                if any(ord(c) < 32 and c not in "\n\r\t" for c in text):
                    raise FileRejected("Text files must contain UTF-8 text")
            decoder.decode(b"", final=True)
        except UnicodeDecodeError as exc:
            raise FileRejected("Text files must contain UTF-8 text") from exc
    else:
        stream.seek(0, 2)
        size = stream.tell()
        stream.seek(max(0, size - 1024))
        tail = stream.read(1024)
        valid = ((suffix == ".pdf" and header.startswith(b"%PDF-") and b"%%EOF" in tail)
                 or (suffix == ".png" and header.startswith(b"\x89PNG\r\n\x1a\n") and b"IEND" in tail)
                 or (suffix in {
                     ".jpg",
                     ".jpeg",
                 } and header.startswith(b"\xff\xd8\xff") and tail.endswith(b"\xff\xd9")))
        if not valid:
            raise FileRejected("File content does not match its extension")
    stream.seek(0)
    return TYPES[suffix]


def scan_file(stream: BinaryIO, host: str, port: int, timeout: int) -> None:
    deadline = time.monotonic() + timeout
    with socket.create_connection((host, port), timeout=timeout) as client:
        def remaining():
            duration = deadline - time.monotonic()
            if duration <= 0:
                raise TimeoutError("Safety scan deadline exceeded")
            client.settimeout(duration)
        remaining()
        client.sendall(b"zINSTREAM\0")
        stream.seek(0)
        while chunk := stream.read(65536):
            remaining()
            client.sendall(struct.pack("!I", len(chunk)) + chunk)
        client.sendall(struct.pack("!I", 0))
        response = b""
        while b"\0" not in response and len(response) < 4096:
            remaining()
            chunk = client.recv(1024)
            if not chunk:
                break
            response += chunk
        if response.rstrip(b"\0\n") != b"stream: OK":
            raise FileRejected("The file could not pass the safety scan")
    stream.seek(0)
