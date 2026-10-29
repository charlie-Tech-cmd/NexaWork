"""Pure file security checks also run with stdlib unittest, without app services."""
import io
import tempfile
import unittest
from pathlib import Path
from app.services.file_validation import FileRejected, safe_filename, validate_content
from app.integrations.storage.local import LocalStorage


class FileSecurityTests(unittest.TestCase):
    def test_filename_paths_controls_and_unsupported_types(self):
        for name in ["../a.txt", "a\\b.txt", "a\r\n.txt", "\x00.txt", ".txt", "a.exe", "x" * 201 + ".txt"]:
            with self.subTest(name=repr(name)), self.assertRaises(FileRejected):
                safe_filename(name)
        self.assertEqual(safe_filename(" résumé.txt "), "résumé.txt")

    def test_utf8_text_validated_incrementally_and_rewound(self):
        f = io.BytesIO(("a" * 65535 + "é\n").encode())
        self.assertEqual(validate_content(f, "report.txt"), "text/plain")
        self.assertEqual(f.tell(), 0)
        for data in [b"\xff", b"hello\x00world", b"\x89PNG\r\n\x1a\n"]:
            with self.assertRaises(FileRejected):
                validate_content(io.BytesIO(data), "fake.txt")

    def test_misleading_media_extensions_rejected(self):
        for name in ["x.pdf", "x.png", "x.jpeg"]:
            with self.assertRaises(FileRejected):
                validate_content(io.BytesIO(b"not the claimed format"), name)

    def test_private_storage_exclusive_create_and_safe_delete(self):
        with tempfile.TemporaryDirectory() as root:
            store = LocalStorage(root)
            key = "a" * 32
            with store.create(key) as f: f.write(b"hello")
            with store.open(key) as f: self.assertEqual(f.read(), b"hello")
            self.assertEqual(Path(root, key).stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError): store.create(key)
            with self.assertRaises(ValueError): store.open("../outside")
            store.delete(key); store.delete(key)

    def test_storage_does_not_follow_object_symlinks(self):
        with tempfile.TemporaryDirectory() as root:
            outside = Path(root, "outside.txt"); outside.write_text("private")
            Path(root, "a" * 32).symlink_to(outside)
            with self.assertRaises(OSError): LocalStorage(root).open("a" * 32)


class ScannerProtocolTests(unittest.TestCase):
    def test_bounded_framing_and_clean_response(self):
        from unittest.mock import patch
        from app.services.file_validation import scan_file
        class Client:
            def __init__(self): self.sent = []
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def settimeout(self, seconds): assert 0 < seconds <= 30
            def sendall(self, value): self.sent.append(value)
            def recv(self, limit): return b"stream: OK\0"
        client = Client()
        with patch("app.services.file_validation.socket.create_connection", return_value=client):
            scan_file(io.BytesIO(b"abc"), "scanner.test", 3310, 30)
        self.assertEqual(client.sent, [b"zINSTREAM\0", b"\0\0\0\x03abc", b"\0\0\0\0"])

    def test_infected_or_incomplete_result_is_rejected(self):
        from unittest.mock import MagicMock, patch
        from app.services.file_validation import scan_file
        for response in [b"stream: Test-Signature FOUND\0", b"", b"stream: ERROR\0"]:
            client = MagicMock(); client.__enter__.return_value = client; client.recv.return_value = response
            with patch("app.services.file_validation.socket.create_connection", return_value=client):
                with self.assertRaises(FileRejected): scan_file(io.BytesIO(b"abc"), "scanner.test", 3310, 30)


if __name__ == "__main__": unittest.main()
