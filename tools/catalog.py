#!/usr/bin/env python3
"""Validate the skill catalog, render CATALOG.md, and build the static site.

    python tools/catalog.py validate
    python tools/catalog.py render [--check]
    python tools/catalog.py build-site --output _site --repo OWNER/REPO --branch BRANCH

The catalog entries in catalog/entries/*.yml are the single source for both
CATALOG.md and the website. Validation always runs first; a malformed entry
fails the whole command rather than producing a partial catalog.

This tool never executes skill-bundled scripts, fetches remote content, or
renders contributor-supplied HTML.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import re
import shutil
import string
import sys
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from urllib.parse import quote, urlsplit

import yaml

ROOT = Path(__file__).resolve().parent.parent

TITLE = "FM/AR Agent Skills"

SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
BRANCH_RE = re.compile(r"^[A-Za-z0-9._/-]+$")
# SPDX license expression tokens; the list of identifiers is not checked.
LICENSE_TOKEN_RE = re.compile(r"^(\(|\)|AND|OR|WITH|[A-Za-z0-9.+-]+)$")

ENTRY_KEYS = {
    "id", "title", "summary", "location", "tags", "license", "rationale",
    "review", "evidence", "maintainer", "limitations", "last_inspected",
    "status", "caution",
}
REQUIRED_ENTRY_KEYS = {"id", "title", "summary", "location", "tags", "license", "rationale"}
LOCATION_KEYS = {"local": {"kind", "path"}, "external": {"kind", "url", "revision"}}
LICENSE_KEYS = {"id", "url_or_path"}
REVIEW_KEYS = {"url", "reviewer", "date", "revision", "scope"}
EVIDENCE_KEYS = {
    "kind", "url", "summary", "date", "skill_revision", "context",
    "limitations", "outcome", "reporter_role",
}
EVIDENCE_KINDS = {"usage-report"}
OUTCOMES = {"positive", "negative", "mixed"}
REPORTER_ROLES = {"author", "maintainer", "independent"}
STATUSES = {"needs-review"}

SKILL_NAME_MAX = 64
SKILL_DESCRIPTION_MAX = 1024
SKILL_COMPATIBILITY_MAX = 500
SKILL_LICENSE_FILE = "LICENSE.txt"
# Directories conventionally referenced from SKILL.md; mentions of files under
# them are checked for existence.
RESOURCE_DIRS = ("scripts", "references", "assets")


class ValidationError(Exception):
    def __init__(self, errors: list[str]):
        super().__init__("\n".join(errors))
        self.errors = errors


@dataclass
class Entry:
    data: dict
    source: Path

    @property
    def id(self) -> str:
        return self.data["id"]

    @property
    def kind(self) -> str:
        return self.data["location"]["kind"]

    @property
    def sort_key(self) -> tuple[str, str]:
        return (self.data["title"].casefold(), self.id)


@dataclass
class Catalog:
    entries: list[Entry] = field(default_factory=list)

    def by_kind(self, kind: str) -> list[Entry]:
        return sorted((e for e in self.entries if e.kind == kind), key=lambda e: e.sort_key)


# --------------------------------------------------------------------------
# Validation


def is_https_url(value: object) -> bool:
    if not isinstance(value, str) or any(c.isspace() for c in value):
        return False
    parts = urlsplit(value)
    return parts.scheme == "https" and bool(parts.netloc)


def safe_relative_path(value: object) -> PurePosixPath | None:
    """Return a normalized relative POSIX path, or None if it could escape."""
    if not isinstance(value, str) or not value or "\\" in value or "\0" in value:
        return None
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ("..", "") for part in path.parts):
        return None
    if ":" in path.parts[0]:  # reject scheme-like values such as javascript:x
        return None
    return path


def is_within(path: Path, base: Path) -> bool:
    try:
        path.resolve().relative_to(base.resolve())
    except ValueError:
        return False
    return True


def nonempty_str(value: object) -> bool:
    return isinstance(value, str) and value.strip() != ""


def date_str(value: object) -> str | None:
    if isinstance(value, dt.date):
        return value.isoformat()
    if isinstance(value, str):
        try:
            return dt.date.fromisoformat(value).isoformat()
        except ValueError:
            return None
    return None


def check_keys(where: str, data: dict, allowed: set[str], required: set[str], errors: list[str]) -> None:
    for key in sorted(set(data) - allowed):
        errors.append(f"{where}: unsupported field '{key}'")
    for key in sorted(required - set(data)):
        errors.append(f"{where}: missing required field '{key}'")


def validate_license_id(where: str, value: object, errors: list[str]) -> None:
    if not nonempty_str(value):
        errors.append(f"{where}: license id must be a non-empty string")
        return
    if value == "unknown":
        return
    tokens = value.replace("(", " ( ").replace(")", " ) ").split()
    if not tokens or not all(LICENSE_TOKEN_RE.match(t) for t in tokens):
        errors.append(f"{where}: license id '{value}' is not an SPDX expression, LicenseRef-*, or 'unknown'")


def parse_frontmatter(text: str) -> dict | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end == -1:
        end = text.find("\n---", 4)
        if end == -1 or text[end + 4:].strip():
            return None
    try:
        data = yaml.safe_load(text[4:end])
    except yaml.YAMLError:
        return None
    return data if isinstance(data, dict) else None


def validate_skill_md(where: str, skill_dir: Path, require_license: bool, errors: list[str]) -> str | None:
    """Check SKILL.md against the Agent Skills format and repository policy.

    Returns the SKILL.md text when it was readable.
    """
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        errors.append(f"{where}: missing SKILL.md")
        return None
    text = skill_md.read_text(encoding="utf-8")
    meta = parse_frontmatter(text)
    if meta is None:
        errors.append(f"{where}: SKILL.md must start with YAML frontmatter between '---' lines")
        return text
    name = meta.get("name")
    if not isinstance(name, str) or not SLUG_RE.match(name) or len(name) > SKILL_NAME_MAX:
        errors.append(f"{where}: SKILL.md 'name' must be lowercase letters, digits and single hyphens, at most {SKILL_NAME_MAX} characters")
    elif name != skill_dir.name:
        errors.append(f"{where}: SKILL.md name '{name}' does not match directory '{skill_dir.name}'")
    desc = meta.get("description")
    if not nonempty_str(desc) or len(desc) > SKILL_DESCRIPTION_MAX:
        errors.append(f"{where}: SKILL.md 'description' must be non-empty and at most {SKILL_DESCRIPTION_MAX} characters")
    compat = meta.get("compatibility")
    if compat is not None and (not nonempty_str(compat) or len(compat) > SKILL_COMPATIBILITY_MAX):
        errors.append(f"{where}: SKILL.md 'compatibility' must be non-empty and at most {SKILL_COMPATIBILITY_MAX} characters")
    # Repository policy, stricter than the upstream format.
    if require_license and not nonempty_str(meta.get("license")):
        errors.append(f"{where}: SKILL.md must declare 'license' (repository policy)")
    if require_license and not (skill_dir / SKILL_LICENSE_FILE).is_file():
        errors.append(f"{where}: missing {SKILL_LICENSE_FILE} (repository policy)")
    return text


def referenced_resources(text: str) -> set[str]:
    """Relative paths mentioned in SKILL.md that can be checked statically.

    Covers Markdown link targets and `scripts/`, `references/`, `assets/`
    paths. Paths built at runtime or named in prose are not detected.
    """
    found: set[str] = set()
    for target in re.findall(r"\]\(([^)\s]+)", text):
        target = target.split("#", 1)[0]
        if target and not urlsplit(target).scheme and not target.startswith("#"):
            found.add(target)
    dirs = "|".join(RESOURCE_DIRS)
    for match in re.findall(rf"(?<![\w./-])((?:{dirs})/[\w./-]*\w)", text):
        found.add(match)
    return found


def validate_local_package(where: str, entry: dict, root: Path, errors: list[str]) -> None:
    path = safe_relative_path(entry["location"].get("path"))
    expected = PurePosixPath("skills", entry["id"])
    if path is None or path != expected:
        errors.append(f"{where}: local path must be '{expected}'")
        return
    skill_dir = root / path
    if not skill_dir.is_dir() or not is_within(skill_dir, root / "skills"):
        errors.append(f"{where}: local skill directory '{path}' does not exist")
        return
    for item in skill_dir.rglob("*"):
        if item.is_symlink() and not is_within(item, skill_dir):
            errors.append(f"{where}: symlink '{item.relative_to(root)}' points outside the skill directory")
    text = validate_skill_md(where, skill_dir, require_license=True, errors=errors)
    if text is not None:
        for ref in sorted(referenced_resources(text)):
            rel = safe_relative_path(ref)
            if rel is None or not is_within(skill_dir / rel, skill_dir):
                errors.append(f"{where}: SKILL.md references '{ref}', which leaves the skill directory")
            elif not (skill_dir / rel).exists():
                errors.append(f"{where}: SKILL.md references missing resource '{ref}'")

    lic = entry["license"].get("url_or_path")
    if isinstance(lic, str) and not is_https_url(lic):
        rel = safe_relative_path(lic)
        if rel is None or not (root / rel).is_file() or not is_within(root / rel, skill_dir):
            errors.append(f"{where}: license path '{lic}' must be a file inside {path}")


def validate_entry(path: Path, root: Path, errors: list[str]) -> Entry | None:
    where = str(path.relative_to(root))
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        errors.append(f"{where}: invalid YAML: {exc}")
        return None
    if not isinstance(data, dict):
        errors.append(f"{where}: entry must be a mapping")
        return None
    start = len(errors)
    check_keys(where, data, ENTRY_KEYS, REQUIRED_ENTRY_KEYS, errors)
    if len(errors) > start:
        return None

    entry_id = data["id"]
    if not isinstance(entry_id, str) or not SLUG_RE.match(entry_id) or len(entry_id) > SKILL_NAME_MAX:
        errors.append(f"{where}: id must be lowercase letters, digits and single hyphens")
        return None
    if path.stem != entry_id:
        errors.append(f"{where}: file name must be '{entry_id}.yml'")
    for key in ("title", "summary", "rationale"):
        if not nonempty_str(data[key]):
            errors.append(f"{where}: '{key}' must be a non-empty string")
    for key in ("maintainer", "limitations", "caution"):
        if key in data and not nonempty_str(data[key]):
            errors.append(f"{where}: '{key}' must be a non-empty string when present")
    if "last_inspected" in data and date_str(data["last_inspected"]) is None:
        errors.append(f"{where}: 'last_inspected' must be a YYYY-MM-DD date")
    if "status" in data and data["status"] not in STATUSES:
        errors.append(f"{where}: 'status' must be one of {sorted(STATUSES)}")

    tags = data["tags"]
    if not isinstance(tags, list) or not tags or not all(isinstance(t, str) and SLUG_RE.match(t) for t in tags):
        errors.append(f"{where}: 'tags' must be a non-empty list of lowercase hyphenated tags")
    elif len(set(tags)) != len(tags):
        errors.append(f"{where}: duplicate tags")

    loc = data["location"]
    kind = loc.get("kind") if isinstance(loc, dict) else None
    if kind not in LOCATION_KEYS:
        errors.append(f"{where}: location.kind must be 'local' or 'external'")
        return None
    required_loc = {"kind", "path"} if kind == "local" else {"kind", "url"}
    check_keys(f"{where}: location", loc, LOCATION_KEYS[kind], required_loc, errors)
    if kind == "external":
        if not is_https_url(loc.get("url")):
            errors.append(f"{where}: external location.url must be an https URL")
        if "revision" in loc and not nonempty_str(loc["revision"]):
            errors.append(f"{where}: location.revision must be a non-empty string when present")

    lic = data["license"]
    if not isinstance(lic, dict):
        errors.append(f"{where}: 'license' must be a mapping")
    else:
        check_keys(f"{where}: license", lic, LICENSE_KEYS, {"id"}, errors)
        validate_license_id(where, lic.get("id"), errors)
        url_or_path = lic.get("url_or_path")
        if url_or_path is None:
            if lic.get("id") != "unknown" or kind == "local":
                errors.append(f"{where}: license.url_or_path is required unless an external license is 'unknown'")
        elif kind == "external" and not is_https_url(url_or_path):
            errors.append(f"{where}: external license.url_or_path must be an https URL")
        elif not isinstance(url_or_path, str):
            errors.append(f"{where}: license.url_or_path must be a string")

    review = data.get("review")
    if review is not None:
        if not isinstance(review, dict):
            errors.append(f"{where}: 'review' must be a mapping or null")
        else:
            check_keys(f"{where}: review", review, REVIEW_KEYS, {"url", "reviewer", "date"}, errors)
            if not is_https_url(review.get("url")):
                errors.append(f"{where}: review.url must be an https URL to the actual review")
            if not nonempty_str(review.get("reviewer")):
                errors.append(f"{where}: review.reviewer must be a non-empty string")
            if date_str(review.get("date")) is None:
                errors.append(f"{where}: review.date must be a YYYY-MM-DD date")

    evidence = data.get("evidence", [])
    if not isinstance(evidence, list):
        errors.append(f"{where}: 'evidence' must be a list")
    else:
        for i, item in enumerate(evidence):
            ew = f"{where}: evidence[{i}]"
            if not isinstance(item, dict):
                errors.append(f"{ew}: must be a mapping")
                continue
            check_keys(ew, item, EVIDENCE_KEYS, {"kind", "url", "summary", "outcome"}, errors)
            if item.get("kind") not in EVIDENCE_KINDS:
                errors.append(f"{ew}: kind must be one of {sorted(EVIDENCE_KINDS)}")
            if not is_https_url(item.get("url")):
                errors.append(f"{ew}: url must be an https URL to the actual report")
            if not nonempty_str(item.get("summary")):
                errors.append(f"{ew}: summary must state the specific claim the source supports")
            if item.get("outcome") not in OUTCOMES:
                errors.append(f"{ew}: outcome must be one of {sorted(OUTCOMES)}")
            if "date" in item and date_str(item["date"]) is None:
                errors.append(f"{ew}: date must be a YYYY-MM-DD date")
            if "reporter_role" in item and item["reporter_role"] not in REPORTER_ROLES:
                errors.append(f"{ew}: reporter_role must be one of {sorted(REPORTER_ROLES)}")
            for key in ("skill_revision", "context", "limitations"):
                if key in item and item[key] is not None and not nonempty_str(item[key]):
                    errors.append(f"{ew}: {key} must be a non-empty string or null")

    if kind == "local" and len(errors) == start:
        validate_local_package(where, data, root, errors)
    return Entry(data, path) if len(errors) == start else None


def load_catalog(root: Path = ROOT) -> Catalog:
    errors: list[str] = []
    entries_dir = root / "catalog" / "entries"
    entries: list[Entry] = []
    for path in sorted(entries_dir.glob("*")):
        if path.name == ".gitkeep":
            continue
        if path.suffix != ".yml" or not path.is_file():
            errors.append(f"{path.relative_to(root)}: catalog entries must be .yml files")
            continue
        entry = validate_entry(path, root, errors)
        if entry is not None:
            entries.append(entry)

    seen: dict[str, Path] = {}
    for entry in entries:
        if entry.id in seen:
            errors.append(f"{entry.source.relative_to(root)}: duplicate id '{entry.id}'")
        seen[entry.id] = entry.source

    local_ids = {e.id for e in entries if e.kind == "local"}
    skills_dir = root / "skills"
    if skills_dir.is_dir():
        for item in sorted(skills_dir.iterdir()):
            if item.name == ".gitkeep":
                continue
            if not item.is_dir():
                errors.append(f"skills/{item.name}: only skill directories belong in skills/")
            elif item.name not in local_ids:
                errors.append(f"skills/{item.name}: no catalog entry catalog/entries/{item.name}.yml with kind 'local'")

    template = root / "template" / "skill-template"
    if template.is_dir():
        validate_skill_md("template/skill-template", template, require_license=True, errors=errors)

    if errors:
        raise ValidationError(errors)
    return Catalog(entries)


# --------------------------------------------------------------------------
# Badges


@dataclass
class Badge:
    label: str
    href: str  # a URL, or "#anchor" within the entry
    note: str = ""


def evidence_items(entry: Entry) -> list[dict]:
    return list(entry.data.get("evidence") or [])


def badges(entry: Entry) -> list[Badge]:
    """Derive badges from supporting records only; there is no manual override."""
    out = [Badge("Listed", f"#{entry.id}-rationale")]
    review = entry.data.get("review")
    if review:
        out.append(Badge("Reviewed", review["url"], date_str(review["date"]) or ""))
    useful = [e for e in evidence_items(entry) if e["kind"] == "usage-report" and e["outcome"] in ("positive", "mixed")]
    if useful:
        out.append(Badge("Reported useful", useful[0]["url"], f"{len(useful)} report(s)" if len(useful) > 1 else ""))
    return out


def cautions(entry: Entry) -> list[str]:
    notes = []
    if entry.data.get("status") == "needs-review":
        notes.append("Needs review: this entry may be outdated or broken.")
    if entry.data.get("caution"):
        notes.append(entry.data["caution"])
    if any(e["outcome"] == "negative" for e in evidence_items(entry)):
        notes.append("At least one linked report describes a negative outcome; see the evidence below.")
    return notes


# --------------------------------------------------------------------------
# Link resolution


@dataclass
class Links:
    """Resolves local repository paths for a given output."""

    repo: str | None = None
    branch: str | None = None
    root: Path = ROOT

    def local(self, rel: str) -> str:
        path = safe_relative_path(rel)
        if path is None:  # validation rejects this earlier; never emit it
            raise ValueError(f"unsafe path {rel!r}")
        if self.repo is None:
            return quote(str(path))
        kind = "tree" if (self.root / path).is_dir() else "blob"
        return f"https://github.com/{self.repo}/{kind}/{quote(self.branch)}/{quote(str(path))}"

    def source(self, entry: Entry) -> str:
        loc = entry.data["location"]
        return self.local(loc["path"]) if loc["kind"] == "local" else loc["url"]

    def license(self, entry: Entry) -> str | None:
        value = entry.data["license"].get("url_or_path")
        if value is None:
            return None
        return value if is_https_url(value) else self.local(value)


def version_text(entry: Entry) -> str:
    loc = entry.data["location"]
    if loc["kind"] == "external":
        return f"revision {loc['revision']}" if loc.get("revision") else "version not specified"
    return "maintained in this repository"


# --------------------------------------------------------------------------
# Markdown rendering

MD_SPECIAL = re.compile(r"([\\`*_\[\]{}#|~!])")


def md(text: str) -> str:
    """Escape untrusted text for Markdown, including any inline HTML."""
    text = " ".join(str(text).split())
    return MD_SPECIAL.sub(r"\\\1", html.escape(text, quote=False))


def md_link(label: str, url: str) -> str:
    return f"[{md(label)}](<{url.replace('>', '%3E').replace(' ', '%20')}>)"


def render_markdown(catalog: Catalog) -> str:
    links = Links()
    lines = [
        f"# {TITLE}: catalog",
        "",
        "<!-- Generated by tools/catalog.py from catalog/entries/. Do not edit by hand. -->",
        "",
        "Entries are listed alphabetically. Badges are evidence labels, not a ranking;",
        "see [What do the badges mean?](README.md#what-do-the-badges-mean) and the",
        "[catalog policy](catalog/README.md).",
        "",
    ]
    if not catalog.entries:
        lines += [
            "No skills are cataloged yet. We add entries only for real skills, with a",
            "stated reason for inclusion.",
            "",
            "- Know a suitable skill? [Suggest it](CONTRIBUTING.md#catalog-only-contributions).",
            "- Missing a workflow? [Request a skill](CONTRIBUTING.md#questions-and-requests).",
            "- Wrote one? [Contribute a skill](CONTRIBUTING.md#new-or-substantially-updated-local-skills).",
            "",
        ]
        return "\n".join(lines)

    for kind, heading in (("local", "Skills maintained here"), ("external", "External skills")):
        entries = catalog.by_kind(kind)
        lines += [f"## {heading}", ""]
        if not entries:
            lines += ["None yet.", ""]
            continue
        for entry in entries:
            d = entry.data
            lines += [f'<a id="{entry.id}"></a>', "", f"### {md(d['title'])}", ""]
            badge_md = []
            for b in badges(entry):
                text = f"[{b.label}]({b.href})" if b.href.startswith("#") else md_link(b.label, b.href)
                badge_md.append(f"**{text}**" + (f" ({md(b.note)})" if b.note else ""))
            lines += [" · ".join(badge_md), ""]
            for note in cautions(entry):
                lines += [f"> **Caution:** {md(note)}", ""]
            lines += [md(d["summary"]), ""]
            lic_url = links.license(entry)
            lic = md(d["license"]["id"])
            lines += [
                f"- **Source:** {md_link(d['location'].get('path') or d['location']['url'], links.source(entry))} ({md(version_text(entry))})",
                f"- **License:** {md_link(d['license']['id'], lic_url) if lic_url else lic + ' (terms not established; not permission to redistribute)'}",
                f"- **Tags:** {', '.join(md(t) for t in d['tags'])}",
            ]
            if d.get("maintainer"):
                lines.append(f"- **Maintainer:** {md(d['maintainer'])}")
            if d.get("last_inspected"):
                lines.append(f"- **Last inspected:** {date_str(d['last_inspected'])}")
            if d.get("limitations"):
                lines.append(f"- **Limitations:** {md(d['limitations'])}")
            lines += ["", f'<a id="{entry.id}-rationale"></a>**Why it is listed:** {md(d["rationale"])}', ""]
            review = d.get("review")
            if review:
                scope = ", ".join(x for x in (review.get("revision"), review.get("scope")) if x)
                lines += [
                    f"**Review:** {md_link('review by ' + review['reviewer'], review['url'])}, "
                    f"{date_str(review['date'])}" + (f" ({md(scope)})" if scope else ""),
                    "",
                ]
            if evidence_items(entry):
                lines += ["**Evidence:**", ""]
                for e in evidence_items(entry):
                    lines.append(f"- {md_link(e['kind'], e['url'])} ({md(e['outcome'])}): {md(e['summary'])}")
                    for key, label in (("reporter_role", "Reported by"), ("date", "Date"),
                                       ("skill_revision", "Skill revision"), ("context", "Context"),
                                       ("limitations", "Limitations")):
                        value = e.get(key)
                        if value is not None:
                            value = date_str(value) if key == "date" else value
                            lines.append(f"  - {label}: {md(value)}")
                    if e.get("skill_revision") is None:
                        lines.append("  - Skill revision: version not specified")
                lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


# --------------------------------------------------------------------------
# HTML rendering


def h(text: object) -> str:
    return html.escape(" ".join(str(text).split()), quote=True)


def a(label: str, href: str, cls: str | None = None) -> str:
    cls_attr = f' class="{cls}"' if cls else ""
    return f'<a href="{h(href)}"{cls_attr}>{h(label)}</a>'


def render_entry_html(entry: Entry, links: Links) -> str:
    d = entry.data
    eid = entry.id
    parts = [f'<article class="entry" id="{eid}">', f'<h3><a class="anchor" href="#{eid}">{h(d["title"])}</a></h3>']
    badge_items = []
    for b in badges(entry):
        note = f' <span class="badge-note">({h(b.note)})</span>' if b.note else ""
        badge_items.append(f"<li>{a(b.label, b.href, 'badge')}{note}</li>")
    parts.append(f'<ul class="badges" aria-label="Evidence labels">{"".join(badge_items)}</ul>')
    for note in cautions(entry):
        parts.append(f'<p class="caution"><strong>Caution:</strong> {h(note)}</p>')
    parts.append(f'<p class="summary">{h(d["summary"])}</p>')
    lic_url = links.license(entry)
    lic = a(d["license"]["id"], lic_url) if lic_url else f'{h(d["license"]["id"])} (terms not established; not permission to redistribute)'
    src_label = d["location"].get("path") or d["location"]["url"]
    rows = [
        ("Source", f"{a(src_label, links.source(entry))} ({h(version_text(entry))})"),
        ("License", lic),
        ("Tags", " ".join(f'<span class="tag">{h(t)}</span>' for t in d["tags"])),
    ]
    if d.get("maintainer"):
        rows.append(("Maintainer", h(d["maintainer"])))
    if d.get("last_inspected"):
        rows.append(("Last inspected", h(date_str(d["last_inspected"]))))
    if d.get("limitations"):
        rows.append(("Limitations", h(d["limitations"])))
    parts.append("<dl>" + "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in rows) + "</dl>")
    parts.append(f'<p id="{eid}-rationale"><strong>Why it is listed:</strong> {h(d["rationale"])}</p>')
    review = d.get("review")
    if review:
        scope = ", ".join(x for x in (review.get("revision"), review.get("scope")) if x)
        parts.append(
            f'<p><strong>Review:</strong> {a("review by " + review["reviewer"], review["url"])}, '
            f'{h(date_str(review["date"]))}' + (f" ({h(scope)})" if scope else "") + "</p>"
        )
    if evidence_items(entry):
        items = []
        for e in evidence_items(entry):
            details = []
            for key, label in (("reporter_role", "Reported by"), ("date", "Date"), ("context", "Context"),
                               ("limitations", "Limitations")):
                if e.get(key) is not None:
                    value = date_str(e[key]) if key == "date" else e[key]
                    details.append(f"<li>{label}: {h(value)}</li>")
            details.append(f"<li>Skill revision: {h(e.get('skill_revision') or 'version not specified')}</li>")
            items.append(
                f"<li>{a(e['kind'], e['url'])} ({h(e['outcome'])}): {h(e['summary'])}"
                f"<ul>{''.join(details)}</ul></li>"
            )
        parts.append(f'<div id="{eid}-evidence"><strong>Evidence:</strong><ul class="evidence">{"".join(items)}</ul></div>')
    parts.append("</article>")
    return "\n".join(parts)


def render_site(catalog: Catalog, repo: str, branch: str, root: Path = ROOT) -> str:
    links = Links(repo=repo, branch=branch, root=root)
    gh = f"https://github.com/{repo}"
    blob = f"{gh}/blob/{quote(branch)}"
    sections = []
    count = len(catalog.entries)
    if count == 0:
        sections.append(
            '<section class="empty" aria-labelledby="empty-title">'
            '<h2 id="empty-title">No skills cataloged yet</h2>'
            "<p>We add entries only for real skills, with a stated reason for inclusion. "
            "Help get the catalog started:</p>"
            f'<ul><li>{a("Suggest an existing skill", gh + "/issues/new?template=catalog-suggestion.yml")}</li>'
            f'<li>{a("Request a missing skill", gh + "/issues/new?template=skill-request.yml")}</li>'
            f'<li>{a("Contribute a skill", blob + "/CONTRIBUTING.md")}</li></ul>'
            "</section>"
        )
    else:
        for kind, heading, sid in (("local", "Skills maintained here", "local"),
                                   ("external", "External skills", "external")):
            entries = catalog.by_kind(kind)
            body = "\n".join(render_entry_html(e, links) for e in entries) or "<p>None yet.</p>"
            sections.append(f'<section aria-labelledby="{sid}-title"><h2 id="{sid}-title">{heading}</h2>\n{body}\n</section>')

    template = string.Template((root / "site" / "index.html.in").read_text(encoding="utf-8"))
    return template.substitute(
        title=h(TITLE),
        repo_url=h(gh),
        readme_url=h(f"{blob}/README.md"),
        badges_url=h(f"{blob}/README.md#what-do-the-badges-mean"),
        policy_url=h(f"{blob}/catalog/README.md"),
        catalog_md_url=h(f"{blob}/CATALOG.md"),
        contributing_url=h(f"{blob}/CONTRIBUTING.md"),
        question_url=h(f"{gh}/issues/new?template=skill-question.yml"),
        request_url=h(f"{gh}/issues/new?template=skill-request.yml"),
        requests_url=h(f"{gh}/issues?q=is%3Aissue%20is%3Aopen%20label%3Askill-request"),
        issues_url=h(f"{gh}/issues"),
        count=f"{count} skill{'s' if count != 1 else ''} cataloged",
        sections="\n".join(sections),
    )


def build_site(catalog: Catalog, output: Path, repo: str, branch: str, root: Path = ROOT) -> None:
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    (output / "index.html").write_text(render_site(catalog, repo, branch, root), encoding="utf-8")
    shutil.copyfile(root / "site" / "style.css", output / "style.css")


# --------------------------------------------------------------------------
# CLI


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate", help="validate catalog entries and local skill packages")
    render = sub.add_parser("render", help="write CATALOG.md")
    render.add_argument("--check", action="store_true", help="fail if CATALOG.md is out of date")
    site = sub.add_parser("build-site", help="build the static website")
    site.add_argument("--output", type=Path, default=ROOT / "_site")
    site.add_argument("--repo", required=True, help="OWNER/REPO used for source links")
    site.add_argument("--branch", required=True, help="branch used for source links")
    args = parser.parse_args(argv)

    try:
        catalog = load_catalog(ROOT)
    except ValidationError as exc:
        for err in exc.errors:
            print(f"error: {err}", file=sys.stderr)
        print(f"{len(exc.errors)} validation error(s)", file=sys.stderr)
        return 1

    if args.command == "validate":
        print(f"ok: {len(catalog.entries)} catalog entr{'y' if len(catalog.entries) == 1 else 'ies'}")
        return 0

    if args.command == "render":
        target = ROOT / "CATALOG.md"
        text = render_markdown(catalog)
        current = target.read_text(encoding="utf-8") if target.exists() else None
        if args.check:
            if current != text:
                print("error: CATALOG.md is out of date; run 'python tools/catalog.py render'", file=sys.stderr)
                return 1
            print("ok: CATALOG.md is up to date")
            return 0
        target.write_text(text, encoding="utf-8")
        print("wrote CATALOG.md")
        return 0

    if not REPO_RE.match(args.repo) or not BRANCH_RE.match(args.branch) or ".." in args.branch:
        print("error: --repo must be OWNER/REPO and --branch a plain branch name", file=sys.stderr)
        return 2
    output = args.output.resolve()
    if output == ROOT or ROOT.is_relative_to(output) or output.is_relative_to(ROOT / "skills"):
        print("error: refusing to write the site over the repository or skills/", file=sys.stderr)
        return 2
    build_site(catalog, output, args.repo, args.branch)
    print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
