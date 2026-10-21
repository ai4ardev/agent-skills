# FM/AR Agent Skills

A community-maintained selection of agent skills for designing, developing,
and maintaining formal-methods and automated-reasoning tools: logic solvers,
theorem provers, model checkers, synthesis tools, computer algebra systems,
and optimization software.

The goal is to help developers find reusable, domain-specific workflows, not
to collect every coding prompt or rank agents. We maintain a catalog of relevant
skills, with some packages hosted here and others maintained upstream.

[Browse the catalog](CATALOG.md) · [Website](https://ai4ardev.github.io/agent-skills/) ·
[Contribute](CONTRIBUTING.md) · [Questions and requests](https://github.com/ai4ardev/agent-skills/issues)

## What belongs here?

Skills that address the distinctive engineering needs of reasoning software:
semantic correctness, certificates and witnesses, specification frontends,
testing, symbolic or numerical assumptions, performance analysis, and
reproducibility. A skill may be tool-specific when it serves this community;
it must say what it supports and where its advice does not apply.

General-purpose coding and development resources are
[linked below](#general-development-resources) rather than copied into this
collection.

## Find and use a skill

The [catalog](CATALOG.md) distinguishes locally maintained packages from
external skills and records their purpose, license, requirements, and evidence.
Read a skill's instructions and license before using it. Review any scripts and
setup steps before running them; installing a skill is a trust decision.

For a local package, take the whole skill directory under `skills/`, including
its license and required resources, not only `SKILL.md`. Follow your agent's
documented skill installation mechanism. External skills retain their upstream
installation instructions and licenses.

## What do the badges mean?

**Listed** links to the reason for inclusion. **Reviewed** links to a recorded
maintainer review of a stated version or scope; merging a catalog entry is not,
by itself, a review. **Reported useful** links to an explicit user or project
report. **Evaluated** links to an evaluation with a stated task, result, and
scope; it means evaluated, not successful. These are evidence labels, not a
universal quality ranking.

A report can be useful without being a controlled experiment. A paper about an
underlying technique is not, by itself, evidence that a particular agent skill
helps. Read the linked source and its limitations.

We collect evidence links; we do not operate or maintain evaluation suites.
Badges do not certify correctness, security, or effectiveness in your setting.
See the [catalog policy](catalog/README.md) for the precise rules.

## Contribute, ask, or request

Pull requests for new local skills should include `SKILL.md`, an explicit
license, and the resources and setup information needed to use the skill.
Catalog suggestions and improvements are welcome too; see
[CONTRIBUTING.md](CONTRIBUTING.md).

Issues are not just bug reports. [Ask which skills suit a task](https://github.com/ai4ardev/agent-skills/issues/new?template=skill-question.yml),
share experience, recommend an existing skill,
[request a missing skill](https://github.com/ai4ardev/agent-skills/issues/new?template=skill-request.yml),
or flag outdated advice and licensing questions. You do not need an
implementation to open an issue.

Anthropic's [Skill Creator](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md)
can help you draft or improve a contribution. Include the resources your final
skill needs. An evaluation harness is not required.

## Open skill requests

Browse [requested skills](https://github.com/ai4ardev/agent-skills/issues?q=is%3Aissue%20is%3Aopen%20label%3Askill-request).
The initial requests cover correctness auditing; differential, metamorphic, and
frontend testing; certificate checking; benchmarking and performance diagnosis;
symbolic-computation auditing; implementing research algorithms; and
reproducible releases. These are requests, not already available packages.

## General development resources

- [Anthropic's skills collection](https://github.com/anthropics/skills):
  general-purpose skills and examples, maintained upstream. It contains both
  open-source and source-available material; check each skill's license.
- [Agent Skills specification](https://agentskills.io/specification):
  the package format used by this collection.
- [Anthropic's Skill Creator](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md):
  help with authoring and revising skills.
- [Ponytail](https://github.com/DietrichGebert/ponytail): makes an agent
  reuse existing code, the standard library, and platform features before
  writing new code. MIT licensed.
- [Humanizer](https://github.com/blader/humanizer): removes signs of
  AI-generated writing from text, useful for documentation and skill prose.
  MIT licensed.

Other well-chosen collections can be proposed through a normal pull request.

## Licensing and independence

Unless otherwise stated, original repository-owned material is available under
the [MIT license](LICENSE). Each skill package and third-party resource is
governed by its own stated license; the root license does not override those
terms. MIT is recommended for new contributions, but individual skills may use
other licenses. Check the relevant license file and catalog entry.

This is an independent FM/AR community initiative. Its organization is inspired
by Anthropic's skills repository; it is not an official Anthropic project.

## Repository tooling

The catalog and website are generated from `catalog/entries/*.yml`:

```sh
pip install -r requirements-dev.txt
python tools/catalog.py validate
python tools/catalog.py render            # regenerate CATALOG.md
python tools/catalog.py build-site --output _site --repo ai4ardev/agent-skills --branch main
python -m unittest discover -s tests
```
