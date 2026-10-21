"""Maintenance tests for tools/catalog.py (not evaluations of any skill).

Each test builds a throwaway repository in a temporary directory, so no test
fixture can enter the production catalog.
"""

import shutil
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import catalog  # noqa: E402

SKILL_MD = """\
---
name: {name}
description: Audit things.
license: MIT
---

# {name}

Run `scripts/check.py` and see [notes](references/notes.md).
"""

LOCAL_ENTRY = """\
id: {name}
title: {title}
summary: Does a task.
location:
  kind: local
  path: skills/{name}
tags: [correctness]
license:
  id: MIT
  url_or_path: skills/{name}/LICENSE.txt
rationale: Useful for solver developers.
"""

EXTERNAL_ENTRY = """\
id: ext-skill
title: External skill
summary: Does an external task.
location:
  kind: external
  url: https://example.org/skills/ext
tags: [testing]
license:
  id: unknown
  url_or_path: null
rationale: Relevant upstream package.
"""


class CatalogTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "catalog" / "entries").mkdir(parents=True)
        (self.root / "skills").mkdir()
        shutil.copytree(ROOT / "site", self.root / "site")

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rel, text):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(text), encoding="utf-8")

    def add_local(self, name="local-skill", title="Local skill", license_file=True, resources=True):
        self.write(f"skills/{name}/SKILL.md", SKILL_MD.format(name=name))
        if license_file:
            self.write(f"skills/{name}/LICENSE.txt", "MIT License\n")
        if resources:
            self.write(f"skills/{name}/scripts/check.py", "")
            self.write(f"skills/{name}/references/notes.md", "")
        self.write(f"catalog/entries/{name}.yml", LOCAL_ENTRY.format(name=name, title=title))

    def errors(self):
        with self.assertRaises(catalog.ValidationError) as ctx:
            catalog.load_catalog(self.root)
        return "\n".join(ctx.exception.errors)


class ValidationTests(CatalogTestCase):
    def test_empty_catalog_is_valid(self):
        self.assertEqual(catalog.load_catalog(self.root).entries, [])

    def test_local_and_external_entries(self):
        self.add_local()
        self.write("catalog/entries/ext-skill.yml", EXTERNAL_ENTRY)
        cat = catalog.load_catalog(self.root)
        self.assertEqual([e.id for e in cat.by_kind("local")], ["local-skill"])
        self.assertEqual([e.id for e in cat.by_kind("external")], ["ext-skill"])

    def test_malformed_yaml(self):
        self.write("catalog/entries/bad.yml", "id: [unclosed\n")
        self.assertIn("invalid YAML", self.errors())

    def test_missing_required_field(self):
        self.write("catalog/entries/ext-skill.yml", EXTERNAL_ENTRY.replace("rationale: Relevant upstream package.\n", ""))
        self.assertIn("missing required field 'rationale'", self.errors())

    def test_missing_license_file(self):
        self.add_local(license_file=False)
        self.assertIn("missing LICENSE.txt", self.errors())

    def test_missing_referenced_resource(self):
        self.add_local(resources=False)
        self.assertIn("missing resource 'scripts/check.py'", self.errors())

    def test_skill_name_must_match_directory(self):
        self.add_local()
        self.write("skills/local-skill/SKILL.md", SKILL_MD.format(name="other-name").replace("`scripts/check.py`", ""))
        self.assertIn("does not match directory", self.errors())

    def test_skill_directory_without_entry(self):
        self.write("skills/orphan/SKILL.md", SKILL_MD.format(name="orphan"))
        self.assertIn("skills/orphan: no catalog entry", self.errors())

    def test_unsupported_badge_claims_are_rejected(self):
        self.write("catalog/entries/ext-skill.yml", EXTERNAL_ENTRY + "rank: excellent\nbadges: [Evaluated]\n")
        errors = self.errors()
        self.assertIn("unsupported field 'rank'", errors)
        self.assertIn("unsupported field 'badges'", errors)

    def test_evidence_needs_a_real_source(self):
        self.write("catalog/entries/ext-skill.yml", EXTERNAL_ENTRY + textwrap.dedent("""\
            evidence:
              - kind: evaluation
                url: javascript:alert(1)
                summary: Claims things.
                outcome: positive
            """))
        self.assertIn("url must be an https URL", self.errors())

    def test_unsafe_local_path(self):
        self.add_local()
        text = (self.root / "catalog/entries/local-skill.yml").read_text()
        self.write("catalog/entries/local-skill.yml", text.replace("path: skills/local-skill", "path: skills/../tools"))
        self.assertIn("local path must be 'skills/local-skill'", self.errors())

    def test_unknown_license_not_allowed_for_local_without_file(self):
        self.add_local()
        text = (self.root / "catalog/entries/local-skill.yml").read_text()
        self.write("catalog/entries/local-skill.yml", text.replace("url_or_path: skills/local-skill/LICENSE.txt", "url_or_path: null"))
        self.assertIn("license.url_or_path is required", self.errors())


class BadgeTests(CatalogTestCase):
    def entry(self, extra=""):
        self.write("catalog/entries/ext-skill.yml", EXTERNAL_ENTRY + textwrap.dedent(extra))
        return catalog.load_catalog(self.root).entries[0]

    def test_listed_only_by_default(self):
        self.assertEqual([b.label for b in catalog.badges(self.entry())], ["Listed"])

    def test_badges_follow_evidence(self):
        entry = self.entry("""\
            evidence:
              - kind: usage-report
                url: https://example.org/report
                summary: Helped triage a bug.
                outcome: positive
              - kind: evaluation
                url: https://example.org/eval
                summary: Compared with baseline.
                outcome: negative
            """)
        badges = {b.label: b for b in catalog.badges(entry)}
        self.assertEqual(set(badges), {"Listed", "Reported useful", "Evaluated"})
        self.assertEqual(badges["Reported useful"].href, "https://example.org/report")
        self.assertIn("negative", badges["Evaluated"].note)
        self.assertTrue(catalog.cautions(entry))

    def test_negative_usage_report_is_not_reported_useful(self):
        entry = self.entry("""\
            evidence:
              - kind: usage-report
                url: https://example.org/report
                summary: Did not help.
                outcome: negative
            """)
        self.assertEqual([b.label for b in catalog.badges(entry)], ["Listed"])


class RenderTests(CatalogTestCase):
    def test_empty_catalog_renders_welcome(self):
        cat = catalog.load_catalog(self.root)
        self.assertIn("No skills are cataloged yet", catalog.render_markdown(cat))
        page = catalog.render_site(cat, "owner/repo", "main", self.root)
        self.assertIn("No skills cataloged yet", page)
        self.assertIn("0 skills cataloged", page)
        self.assertNotIn('class="entry"', page)

    def test_html_and_markdown_escaping(self):
        self.write("catalog/entries/ext-skill.yml", EXTERNAL_ENTRY.replace(
            "summary: Does an external task.", 'summary: "<script>alert(1)</script> [x](javascript:y) *bold*"'))
        cat = catalog.load_catalog(self.root)
        page = catalog.render_site(cat, "owner/repo", "main", self.root)
        self.assertNotIn("<script>", page)
        self.assertIn("&lt;script&gt;", page)
        markdown = catalog.render_markdown(cat)
        self.assertNotIn("<script>", markdown)
        self.assertNotIn("[x](javascript:y)", markdown)

    def test_project_subpath_links(self):
        self.add_local()
        cat = catalog.load_catalog(self.root)
        page = catalog.render_site(cat, "owner/repo", "main", self.root)
        self.assertIn('href="style.css"', page)
        self.assertNotIn('href="/', page)
        self.assertNotIn('src="/', page)
        self.assertIn("https://github.com/owner/repo/tree/main/skills/local-skill", page)
        self.assertIn("https://github.com/owner/repo/blob/main/skills/local-skill/LICENSE.txt", page)
        # CATALOG.md stays relative so it works when browsing the repository.
        self.assertIn("(<skills/local-skill>)", catalog.render_markdown(cat))

    def test_alphabetical_order(self):
        self.add_local("zeta-skill", "Zeta")
        self.add_local("alpha-skill", "alpha")
        cat = catalog.load_catalog(self.root)
        self.assertEqual([e.id for e in cat.by_kind("local")], ["alpha-skill", "zeta-skill"])

    def test_build_site_outputs_only_site_files(self):
        self.add_local()
        out = self.root / "_site"
        catalog.build_site(catalog.load_catalog(self.root), out, "owner/repo", "main", self.root)
        self.assertEqual(sorted(p.name for p in out.iterdir()), ["index.html", "style.css"])


class RepositoryTests(unittest.TestCase):
    def test_repository_catalog_is_valid(self):
        catalog.load_catalog(ROOT)


if __name__ == "__main__":
    unittest.main()
