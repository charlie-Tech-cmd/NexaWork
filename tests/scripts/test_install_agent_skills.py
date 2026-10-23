"""Exercise restoration boundaries without GitHub access or application services."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location(
    "install_agent_skills", Path(__file__).resolve().parents[2] / "scripts/install_agent_skills.py"
)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "repo"
        (self.root / ".agents").mkdir(parents=True)
        self.sources = Path(self.temp.name) / "sources"
        self.lock = {"version": 1, "skills": {}}
        for name in ("rpi-production-engineering", "interface-forge"):
            source = self.sources / name
            source.mkdir(parents=True)
            (source / "SKILL.md").write_bytes(b"skill fixture\n")
            self.lock["skills"][name] = {
                "repository": f"https://github.com/maxchichar/{name}.git",
                "commit": "a" * 40,
                "files": {"SKILL.md": {
                    "sha256": hashlib.sha256(b"skill fixture\n").hexdigest(),
                    "executable": False,
                }},
            }
        self.write_lock()
        old_root = installer.ROOT
        installer.ROOT = self.root
        self.addCleanup(setattr, installer, "ROOT", old_root)

    def write_lock(self):
        (self.root / ".agents/skills.lock.json").write_text(json.dumps(self.lock))

    def run_install(self, check=False):
        with contextlib.redirect_stdout(io.StringIO()):
            installer.install(check, self.sources)

    def test_restore_and_repeat_are_identical(self):
        self.run_install()
        skill = self.root / ".agents/skills/interface-forge/SKILL.md"
        before = skill.stat().st_mtime_ns
        self.run_install()
        self.run_install(check=True)
        self.assertEqual(skill.stat().st_mtime_ns, before)

    def test_check_missing_does_not_create_target(self):
        with self.assertRaises(ValueError):
            self.run_install(check=True)
        self.assertFalse((self.root / ".agents/skills").exists())

    def test_modified_destination_is_preserved(self):
        self.run_install()
        skill = self.root / ".agents/skills/interface-forge/SKILL.md"
        skill.write_text("local edit")
        with self.assertRaises(ValueError):
            self.run_install()
        self.assertEqual(skill.read_text(), "local edit")

    def test_bad_second_source_installs_neither_package(self):
        (self.sources / "interface-forge/SKILL.md").write_text("tampered")
        with self.assertRaises(ValueError):
            self.run_install()
        self.assertFalse((self.root / ".agents/skills").exists())

    def test_symlink_destination_is_rejected(self):
        (self.root / ".agents/skills").symlink_to(self.sources, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.run_install()

    def test_path_traversal_is_rejected(self):
        files = self.lock["skills"]["interface-forge"]["files"]
        files["../outside"] = files["SKILL.md"]
        self.write_lock()
        with self.assertRaises(ValueError):
            self.run_install()
        self.assertFalse((self.root / ".agents/skills").exists())


if __name__ == "__main__":
    unittest.main()
