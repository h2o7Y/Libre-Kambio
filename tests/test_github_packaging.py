from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class GithubPackagingTests(unittest.TestCase):
    def test_public_repository_files_exist(self):
        required = [
            ".gitignore",
            ".github/workflows/ci.yml",
            ".github/workflows/flatpak.yml",
            "CONTRIBUTING.md",
            "SECURITY.md",
            "DISCLAIMER.md",
            "DISCLAIMER.es.md",
            "README.es.md",
            "docs/GITHUB_SETUP.md",
            "docs/RELEASING.md",
            ".github/pull_request_template.md",
            "scripts/check-release.sh",
        ]
        for relative in required:
            self.assertTrue((ROOT / relative).is_file(), relative)

    def test_readme_points_to_public_repository(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("github.com/h2o7y/Libre-Kambio", readme)
        self.assertIn("GPL-3.0-only", readme)

    def test_metainfo_has_public_project_links_and_developer(self):
        text = (ROOT / "io.github.h2o7y.LibreKambioCurrency.metainfo.xml").read_text(encoding="utf-8")
        self.assertIn('<developer id="io.github.h2o7y">', text)
        self.assertIn("https://github.com/h2o7y/Libre-Kambio", text)
        self.assertIn("GPL-3.0-only", text)

    def test_desktop_default_metadata_is_english_with_spanish_translation(self):
        text = (ROOT / "io.github.h2o7y.LibreKambioCurrency.desktop").read_text(encoding="utf-8")
        self.assertIn("GenericName=Currency converter", text)
        self.assertIn("GenericName[es]=Conversor de divisas", text)
        self.assertIn("Comment[es]=", text)

    def test_ci_runs_release_check_script(self):
        workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        self.assertIn("./scripts/check-release.sh", workflow)
        self.assertIn("actions/checkout@v6", workflow)
        self.assertIn("actions/setup-python@v6", workflow)

    def test_flatpak_workflow_uses_official_flatpak_action(self):
        workflow = (ROOT / ".github/workflows/flatpak.yml").read_text(encoding="utf-8")
        self.assertIn("flatpak/flatpak-github-actions/flatpak-builder@v6", workflow)
        self.assertIn("io.github.h2o7y.LibreKambioCurrency.json", workflow)

    def test_gitignore_excludes_flatpak_build_products(self):
        text = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn(".flatpak-build/", text)
        self.assertIn("*.flatpak", text)
        self.assertIn("__pycache__/", text)

    def test_public_name_disclaimer_and_ai_disclosure(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        disclaimer = (ROOT / "DISCLAIMER.md").read_text(encoding="utf-8")
        notice = (ROOT / "NOTICE.md").read_text(encoding="utf-8")
        self.assertTrue(readme.startswith("# Libre Kambio\n"))
        self.assertIn("Reference information only", readme)
        self.assertIn("AI-assisted development disclosure", readme)
        self.assertIn("to the maximum extent permitted by applicable law", disclaimer)
        self.assertIn("generative-AI assistance", notice)

    def test_in_app_reference_disclaimer_is_bilingual(self):
        main = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn('"reference_disclaimer": "Tipos de referencia únicamente', main)
        self.assertIn('"reference_disclaimer": "Reference rates only', main)
        self.assertIn('self.reference_disclaimer.setText(ui_text(self.language, "reference_disclaimer"))', main)

    def test_release_artifact_uses_short_project_name(self):
        workflow = (ROOT / ".github/workflows/flatpak.yml").read_text(encoding="utf-8")
        bundle_script = (ROOT / "build-bundle-flatpak.sh").read_text(encoding="utf-8")
        self.assertIn("Libre-Kambio-${{ steps.app.outputs.version }}.flatpak", workflow)
        self.assertIn("Libre-Kambio-1.9.32.flatpak", bundle_script)


if __name__ == "__main__":
    unittest.main()
