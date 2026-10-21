# Catalog policy and metadata format

Each cataloged skill has one file, `catalog/entries/<id>.yml`. These files are
the single source for [`CATALOG.md`](../CATALOG.md) and the website; do not
maintain skill lists anywhere else. After editing, run:

```sh
python tools/catalog.py validate
python tools/catalog.py render
```

## Entry format

The examples below illustrate the schema; they are not catalog entries.

### Local skill

```yaml
id: example-skill                 # lowercase, hyphenated; equals the file name
title: Example skill
summary: One sentence explaining the concrete development task.
location:
  kind: local
  path: skills/example-skill      # must be skills/<id>
tags:
  - correctness
  - logic-solvers
license:
  id: MIT                         # SPDX expression or LicenseRef-*
  url_or_path: skills/example-skill/LICENSE.txt
rationale: Why this belongs in an FM/AR developer's toolkit.
```

### External skill

```yaml
id: example-external
title: Example external skill
summary: One sentence explaining the concrete development task.
location:
  kind: external
  url: https://github.com/example/skills/tree/<commit>/skills/example
  revision: <commit or tag examined>        # optional
tags: [testing]
license:
  id: unknown                     # when terms have not been established
  url_or_path: null               # allowed only with id: unknown
rationale: Why this belongs in an FM/AR developer's toolkit.
```

External entries never copy upstream content. `id: unknown` is not permission
to redistribute.

### Optional fields

Leave a field out when it is not known; do not invent values to fill it.

| Field | Meaning |
|---|---|
| `maintainer` | Contact or maintaining project. |
| `limitations` | Known limits of the skill's scope. |
| `last_inspected` | Date (`YYYY-MM-DD`) someone last checked the entry. |
| `status: needs-review` | Known-broken source or materially stale advice. Shown as a caution. |
| `caution` | A short visible warning, e.g. following a negative report. |
| `review` | A recorded maintainer review (below). |
| `evidence` | A list of linked reports or evaluations (below). |

Unsupported fields are rejected, including ranking fields such as `rank`,
`score`, or hand-assigned `badges`.

### Review record

```yaml
review:
  url: https://github.com/OWNER/REPO/pull/123#pullrequestreview-...   # the actual review
  reviewer: Reviewer name or handle
  date: 2026-10-21
  revision: <commit or tag reviewed>   # optional
  scope: What was reviewed             # optional
```

### Evidence item

```yaml
evidence:
  - kind: usage-report        # or: evaluation
    url: https://...          # the actual public report, not a homepage
    summary: The specific claim this source supports.
    outcome: positive         # positive | negative | mixed
    date: 2026-10-21          # optional
    skill_revision: null      # commit/tag/content reference when known
    context: Task, agent, tool version, or environment.   # optional
    limitations: What this report does not establish.     # optional
    reporter_role: independent  # optional: author | maintainer | independent
```

## Badges

Badges are generated from the records above; they cannot be set by hand.

| Badge | Shown when | Links to |
|---|---|---|
| **Listed** | Always (every entry has a rationale and a real package). | The entry's rationale. |
| **Reviewed** | A `review` record exists. | That review. |
| **Reported useful** | A `usage-report` with outcome `positive` or `mixed`. | The first such report. |
| **Evaluated** | Any `evaluation`, whatever its outcome. The outcome is shown next to the badge. | The first evaluation. |

The labels are not ordered and entries are listed alphabetically. There are no
star counts, install counts, or scores.

Distinctions to keep in mind:

- A test suite without results is a resource, not an evaluation.
- Script smoke tests show that scripts run; they do not by themselves show
  improved agent performance. State the evaluated property.
- A study of an underlying technique (differential testing, certificate
  checking, ...) can justify a skill's design but is not an evaluation of the
  skill.
- Inclusion in a repository alone does not establish use. An explicit account
  of using a skill and finding it helpful supports "Reported useful".
- "Evaluated" means evaluated, not successful.
- Author and maintainer reports are fine when marked with `reporter_role`; do
  not present them as independent.
- Merging an entry is not a review. "Reviewed" requires a recorded review of a
  stated version or scope.

## Freshness

Dates and revisions are shown where known. An entry or report without a
revision says "version not specified", which implies nothing about current
compatibility. When an entry changes
materially, keep historical evidence with its original `skill_revision` and say
in the pull request what needs re-review; do not carry a review of one version
over to a materially different one. A negative report adds a visible caution;
do not remove contrary evidence to preserve a badge.

There is no automatic expiry, scheduled synchronization, or recurring
evaluation. Corrections arrive through normal issues and pull requests.

## Licensing boundaries

- Local packages carry their own `LICENSE.txt`; the entry's `license` points to
  it. The root MIT license does not override it.
- External entries link to the upstream license. Linking does not import
  upstream content into this repository or its license.
- Mixed-license packages document which files each license covers.
- Adapted material records its source, revision, and changes in
  `PROVENANCE.md`, with any required notices.

## What the checks cover

`tools/catalog.py validate` checks: supported fields, unique ids, file names,
https URLs, safe relative paths, SPDX-style license ids, badge-supporting
records, a catalog entry for every `skills/` directory and vice versa,
`SKILL.md` frontmatter (`name`, `description`, `compatibility` limits, and the
repository's `license` requirement), presence of `LICENSE.txt`, and existence of
files referenced from `SKILL.md` as Markdown links or `scripts/`, `references/`,
`assets/` paths.

It does **not** check remote links, run bundled scripts, verify external
dependencies, or detect resources referenced only in prose or built at run time.
