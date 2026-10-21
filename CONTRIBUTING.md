# Contributing

This is a community resource for people developing formal-methods and
automated-reasoning software. Contributions can be a complete skill, a catalog
suggestion, an experience report, a correction, a question about which skill to
use, or a request for a missing skill. You do not need a paper, benchmark suite,
or implementation to start a discussion.

For help writing or revising a skill, see
[Anthropic's Skill Creator](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md).
Use it as an authoring aid, not as a requirement to adopt a particular agent or
maintain an evaluation harness.

## Questions and requests

Open an issue; pick the form that fits, or open a blank issue:

- [Ask a question](https://github.com/ai4ardev/agent-skills/issues/new?template=skill-question.yml):
  which skill suits a task, how to use one, what has worked for others.
- [Request a skill](https://github.com/ai4ardev/agent-skills/issues/new?template=skill-request.yml):
  describe a missing workflow. You do not need to write it.
- [Suggest an existing skill](https://github.com/ai4ardev/agent-skills/issues/new?template=catalog-suggestion.yml)
  for the catalog.
- [Report evidence or a correction](https://github.com/ai4ardev/agent-skills/issues/new?template=evidence-or-correction.yml):
  experience (positive, negative, or mixed), stale content, or licensing concerns.

## New or substantially updated local skills

A pull request adding a local skill must contain a complete package under
`skills/<skill-id>/`:

1. **`SKILL.md`** with a meaningful trigger/description, intended use and
   non-use cases, prerequisites and setup, an actionable workflow, expected
   outputs, and limitations. Include at least one small invocation or use
   example. A package may legitimately need no executable scripts.
2. **`LICENSE.txt`** with the actual applicable license text and notices, not
   merely a license name in the Markdown. MIT is recommended for original
   contributions; other licenses are fine when the material can lawfully be
   distributed here. Document separately licensed bundled files.
3. **All required local resources**: scripts, templates, configuration,
   dependency files, and small fixtures that the instructions rely on. External
   solver installations and large dependencies may remain external; document how
   to obtain and configure them, version constraints, access requirements, and
   relevant licenses. Do not bundle executables or datasets merely for
   completeness.
4. **A catalog entry** at `catalog/entries/<skill-id>.yml` with purpose,
   location, license, tags, and a concise inclusion rationale. Evidence of
   usefulness is welcome but not required for a "Listed" entry. See the
   [catalog policy](catalog/README.md).
5. **Provenance where applicable**: for copied or adapted material, a
   `PROVENANCE.md` with the original source and revision, authors and notices,
   inherited license terms, and a short explanation of changes. Never replace an
   upstream license with MIT merely because MIT is recommended here.

Then run `python tools/catalog.py render` and commit the updated `CATALOG.md`.

### Format rules versus repository policy

The [Agent Skills specification](https://agentskills.io/specification) requires
a `SKILL.md` with YAML frontmatter containing `name` (lowercase letters, digits
and hyphens, at most 64 characters, matching the directory name) and
`description` (at most 1024 characters), and supports optional `license`,
`compatibility`, and other fields.

This repository additionally requires, as **its own packaging policy**, a
`license` field in the frontmatter and a bundled `LICENSE.txt`, so that copying
the package preserves its licensing information. Avoid unnecessary
agent-specific frontmatter extensions; where a skill really depends on a
particular agent or product, say so in `compatibility` or in the body.

### Starting from the template

Copy [`template/skill-template/`](template/skill-template) to
`skills/<your-skill-id>/`, then:

- rename `name` in the frontmatter to match the new directory;
- replace every prompt in the body with real content;
- fill in the copyright year and holder in `LICENSE.txt`, or replace it with
  the license you are actually using.

The template is not a skill and is never published as one.

## Catalog-only contributions

An external skill suggestion can be an issue or a pull request adding
`catalog/entries/<skill-id>.yml` with `location.kind: external`. It does **not**
require copying the upstream `SKILL.md`, resources, or license into this
repository. Link to the exact package and its license, explain its relevance,
and record the revision you examined when available. An unspecified license is
recorded as `id: unknown`; it is not permission to redistribute.

Documentation fixes, evidence updates, and website changes likewise do not need
a new `SKILL.md`. The full-package requirement applies only to pull requests
adding or substantially changing local skill packages.

## Evidence and review expectations

When you report experience, describe what you actually tried: task and context,
skill version where known, agent and tool versions if relevant, results, and
limitations. A public issue or a short experience report is enough. A link-only
mention without an explicit claim of use is not an effectiveness report.
Reports by a skill's authors or maintainers are welcome when identified as such.

We do not require contributor-run comparative evaluations, expensive solver
installations, or benchmark results. Evidence can be added later. Nobody should
claim a skill was reviewed before an actual review has taken place.

## Safety and scope

Instructions must not override user consent, conceal file or network
operations, export private inputs without authorization, or silently install
dependencies. Clearly identify commands that modify repositories, use network
services, require credentials, or launch expensive computations. Run examples in
disposable workspaces where appropriate.

For reasoning tools, state the relevant semantics and limitations. Instructions
must not turn a timeout, `UNKNOWN`, a failed checker, or resource exhaustion
into a positive proof claim. Examples and success criteria must distinguish what
was observed from what was formally established.

A skill must not present itself as written or endorsed by a real person or
project unless they actually wrote or endorsed it. Material derived from
someone's public work is attributed in `PROVENANCE.md`.

## Review process

Every pull request needs a maintainer review before merging. Reviewers check:

- relevance to FM/AR software development;
- accurate scope and stated limitations;
- a complete package, or an exact external link;
- license and provenance;
- clear setup;
- no hidden side effects;
- `python tools/catalog.py validate` and `render --check` pass;
- support for any badge the entry would earn.

Maintainers may request a narrower scope, keep an entry with a caution, or
remove a misleading or outdated entry. Corrections and negative experiences are
welcome.

## Licensing

Unless otherwise stated, original repository-owned material is available under
the [MIT license](LICENSE). Each skill package and third-party resource is
governed by its own stated license; the root license does not override those
terms. Use accurate copyright holders.
