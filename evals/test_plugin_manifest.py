"""Regressions for PWA's local plugin metadata gate; no model or network."""

import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

EVALS = Path(__file__).resolve().parent
sys.path.insert(0, str(EVALS))
import check


class PluginManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / ".codex-plugin").mkdir()
        (self.root / "skills").mkdir()
        (self.root / "assets").mkdir()
        (self.root / "assets/icon.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"/>'
        )
        self.manifest = {
            "skills": "./skills/",
            "interface": {
                "displayName": "Personal Work Agent",
                "shortDescription": "Personal work, verified",
                "longDescription": "Route personal code and knowledge work.",
                "developerName": "Yinqi Chen",
                "category": "Productivity",
                "capabilities": [],
                "defaultPrompt": "Use $personal-work-agent to complete this task.",
                "composerIcon": "./assets/icon.svg",
                "logo": "./assets/icon.svg",
            },
        }

    def validate(self):
        (self.root / ".codex-plugin/plugin.json").write_text(json.dumps(self.manifest))
        validator = getattr(check, "validate_plugin_manifest", None)
        self.assertTrue(callable(validator), "plugin manifest validation is missing")
        return validator(self.root)

    def assert_error(self, fragment):
        errors = self.validate()
        self.assertTrue(any(fragment in error for error in errors), errors)

    def test_rejects_default_prompt_ignored_by_codex(self):
        self.manifest["interface"]["defaultPrompt"] = "x" * 133
        self.assert_error("defaultPrompt")

    def test_prompt_boundaries_and_types(self):
        for value in ("x" * 128, ["First", "Second", "Third"]):
            with self.subTest(value=value):
                self.manifest["interface"]["defaultPrompt"] = value
                self.assertEqual(self.validate(), [])
        for value in ("x" * 129, "", "\n", "first\nsecond", None, 5,
                      [], ["a"] * 4, ["same", "same"], ["ok", {}]):
            with self.subTest(value=value):
                self.manifest["interface"]["defaultPrompt"] = value
                self.assert_error("defaultPrompt")
        self.manifest["interface"].pop("defaultPrompt")
        self.assertEqual(self.validate(), [])

    def test_directory_text_limits_and_required_fields(self):
        for field, limit in (("displayName", 30), ("shortDescription", 30),
                             ("longDescription", 4000), ("developerName", 80)):
            original = self.manifest["interface"][field]
            for value in (None, "", " " * 2, "x" * (limit + 1)):
                with self.subTest(field=field, value=value):
                    self.manifest["interface"][field] = value
                    self.assert_error(field)
            self.manifest["interface"][field] = "x" * limit
            self.assertEqual(self.validate(), [])
            self.manifest["interface"][field] = original
        self.manifest["interface"].pop("category")
        self.assert_error("category")

    def test_capabilities_and_interface_types(self):
        for value in (None, "Read", ["x"] * 21, [1], ["x" * 121]):
            with self.subTest(value=value):
                self.manifest["interface"]["capabilities"] = value
                self.assert_error("capabilities")
        self.manifest["interface"] = []
        self.assert_error("interface")

    def test_required_icons_and_local_paths(self):
        for field in ("composerIcon", "logo"):
            for value in (None, "assets/icon.svg", "https://example.com/icon.svg",
                          "./assets/missing.svg", "./../outside.svg"):
                with self.subTest(field=field, value=value):
                    self.manifest["interface"][field] = value
                    self.assert_error(field)
            self.manifest["interface"][field] = "./assets/icon.svg"
        outside = self.root.parent / (self.root.name + "-icon.svg")
        outside.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"/>')
        self.addCleanup(outside.unlink)
        (self.root / "assets/link.svg").symlink_to(outside)
        self.manifest["interface"]["logo"] = "./assets/link.svg"
        self.assert_error("logo")

    def test_svg_geometry_size_and_parse_errors(self):
        icon = self.root / "assets/icon.svg"
        for content in ('<svg', '<html/>',
                        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 32"/>',
                        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 47 47"/>',
                        '<svg xmlns="http://www.w3.org/2000/svg"/>',
                        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 NaN NaN"/>',
                        ' ' * (5 * 1024 * 1024 + 1)):
            with self.subTest(content=content[:100]):
                icon.write_text(content)
                self.assert_error("composerIcon")
        for dimensions in ('viewBox="0 0 48 48"', 'width="64" height="64"'):
            icon.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" {dimensions}/>')
            self.assertEqual(self.validate(), [])

    def test_skill_path_must_resolve_inside_package(self):
        for value in (None, "skills", "./missing", "./../"):
            with self.subTest(value=value):
                self.manifest["skills"] = value
                self.assert_error("skills")

    def test_cli_manifest_gate_is_explicit_and_rejects_defect(self):
        self.manifest["interface"]["shortDescription"] = "x" * 57
        self.validate()
        output = io.StringIO()
        try:
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                status = check.main(["--manifest-only", "--package-root", str(self.root)])
        except SystemExit as error:
            status = error.code
        self.assertEqual(status, 1, output.getvalue())
        self.assertIn("shortDescription", output.getvalue())

    def test_current_source_manifest_is_compatible(self):
        self.assertEqual(check.validate_plugin_manifest(EVALS.parent), [])

    def test_cli_accepts_valid_package_and_reports_malformed_manifest(self):
        self.assertEqual(self.validate(), [])
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = check.main(["--manifest-only", "--package-root", str(self.root)])
        self.assertEqual(status, 0, output.getvalue())
        (self.root / ".codex-plugin/plugin.json").write_text("{broken")
        errors = check.validate_plugin_manifest(self.root)
        self.assertTrue(any("JSON-compatible" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
