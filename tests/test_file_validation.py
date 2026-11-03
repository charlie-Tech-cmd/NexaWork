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
            writer = store.create(key)
            writer.write(b"hello")
            writer.complete()
            with store.open(key) as f: self.assertEqual(f.read(), b"hello")
            self.assertEqual(Path(root, key).stat().st_mode & 0o777, 0o600)
            duplicate = store.create(key)
            with self.assertRaises(FileExistsError):
                duplicate.complete()
            with self.assertRaises(ValueError): store.open("../outside")
            store.delete(key); store.delete(key)

    def test_storage_rejects_group_or_world_accessible_roots(self):
        with tempfile.TemporaryDirectory() as root:
            Path(root).chmod(0o755)
            with self.assertRaises(PermissionError):
                LocalStorage(root)

    def test_delete_removes_abandoned_staging_objects_for_the_key(self):
        with tempfile.TemporaryDirectory() as root:
            store = LocalStorage(root)
            key = "1" * 32
            orphan = Path(root, f".staging-{key}-orphan")
            orphan.write_bytes(b"partial upload")

            store.delete(key)

            self.assertFalse(orphan.exists())

    def test_staging_writer_publishes_only_after_complete(self):
        with tempfile.TemporaryDirectory() as root:
            store = LocalStorage(root)
            key = "b" * 32
            writer = store.create(key)

            writer.write(b"partial")
            self.assertFalse(store.path(key).exists())
            self.assertTrue(list(Path(root).glob(".staging-*")))

            writer.complete()

            with store.open(key) as stream:
                self.assertEqual(stream.read(), b"partial")
            self.assertFalse(list(Path(root).glob(".staging-*")))

    def test_staging_writer_abort_discards_incomplete_object(self):
        with tempfile.TemporaryDirectory() as root:
            store = LocalStorage(root)
            key = "c" * 32
            writer = store.create(key)

            writer.write(b"partial")
            writer.abort()
            writer.abort()

            self.assertFalse(store.path(key).exists())
            self.assertFalse(list(Path(root).glob(".staging-*")))
            with self.assertRaises(ValueError):
                writer.write(b"later")

    def test_staging_writer_never_overwrites_existing_object(self):
        with tempfile.TemporaryDirectory() as root:
            store = LocalStorage(root)
            key = "d" * 32

            first = store.create(key)
            first.write(b"original")
            first.complete()

            second = store.create(key)
            second.write(b"replacement")
            with self.assertRaises(FileExistsError):
                second.complete()

            with store.open(key) as stream:
                self.assertEqual(stream.read(), b"original")
            self.assertFalse(list(Path(root).glob(".staging-*")))

    def test_staging_cleanup_can_be_retried_after_publication(self):
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as root:
            store = LocalStorage(root)
            key = "e" * 32
            writer = store.create(key)
            writer.write(b"published")

            original_unlink = Path.unlink
            failed_once = False

            def fail_first_staging_unlink(instance, *args, **kwargs):
                nonlocal failed_once
                if instance.name.startswith(".staging-") and not failed_once:
                    failed_once = True
                    raise OSError("Simulated staging cleanup failure")
                return original_unlink(instance, *args, **kwargs)

            with patch.object(Path, "unlink", fail_first_staging_unlink):
                with self.assertRaises(OSError):
                    writer.complete()

                # Publication succeeded despite the staging cleanup failure.
                self.assertTrue(store.path(key).exists())
                self.assertTrue(list(Path(root).glob(".staging-*")))

                writer.abort()

            with store.open(key) as stream:
                self.assertEqual(stream.read(), b"published")
            self.assertFalse(list(Path(root).glob(".staging-*")))

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

    def test_staging_writer_abort_can_retry_failed_unlink(self):
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as root:
            store = LocalStorage(root)
            key = "f" * 32
            writer = store.create(key)
            writer.write(b"partial")

            original_unlink = Path.unlink
            failed_once = False

            def fail_first_staging_unlink(instance, *args, **kwargs):
                nonlocal failed_once
                if instance.name.startswith(".staging-") and not failed_once:
                    failed_once = True
                    raise OSError("Simulated staging cleanup failure")
                return original_unlink(instance, *args, **kwargs)

            with patch.object(Path, "unlink", fail_first_staging_unlink):
                with self.assertRaises(OSError):
                    writer.abort()

                writer.abort()

            self.assertFalse(store.path(key).exists())
            self.assertFalse(list(Path(root).glob(".staging-*")))


if __name__ == "__main__": unittest.main()
