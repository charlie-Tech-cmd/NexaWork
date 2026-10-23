"""Offline smoke checks for package structure, CLI and safe inspection."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
from validate_skill import parse_frontmatter, validate  # noqa: E402
from inspect_project import inspect  # noqa: E402


class SkillPackageTests(unittest.TestCase):
    def test_manifest_and_references(self):
        self.assertEqual([], validate(ROOT))
        fields, issues = parse_frontmatter((ROOT / "SKILL.md").read_text())
        self.assertEqual([], issues)
        self.assertEqual("interface-forge", fields["name"])

    def test_missing_manifest_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            issues = validate(Path(tmp))
            self.assertTrue(any("Missing required" in issue for issue in issues))

    def test_inspector_is_path_only_and_skips_secrets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src/components").mkdir(parents=True)
            (root / "src/components/Button.tsx").write_text("export default null")
            (root / ".env.local").write_text("TOP_SECRET_VALUE=hidden")
            (root / "package.json").write_text("{}")
            (root / "node_modules").mkdir()
            (root / "node_modules/private.tsx").write_text("secret")
            report = inspect(root)
            self.assertIn("src/components/Button.tsx", report["sample_paths"]["components"])
            self.assertNotIn("private.tsx", json.dumps(report))
            self.assertNotIn("TOP_SECRET_VALUE", json.dumps(report))
            self.assertEqual(2, report["scanned_files"])  # package.json and the component; excludes .env and dependencies

    def test_invalid_frontmatter_name_is_rejected(self):
        _, issues = parse_frontmatter("---\nname: Interface_Forge\ndescription: Valid\n---\n# Test\n")
        self.assertTrue(any("name must be" in issue for issue in issues))

    def test_installer_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            command = ["bash", str(SCRIPTS / "install.sh"), "--target", tmp]
            first = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(0, first.returncode, first.stderr)
            self.assertTrue((Path(tmp) / "interface-forge" / "SKILL.md").is_file())
            second = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(3, second.returncode)
            self.assertIn("Refusing to overwrite", second.stderr)

    def test_inspector_cli_json(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "inspect_project.py"), str(ROOT), "--json"],
            capture_output=True, text=True, check=True,
        )
        parsed = json.loads(result.stdout)
        self.assertIn("root_config_files", parsed)
        self.assertIn("disclaimer", parsed)


if __name__ == "__main__":
    unittest.main()
