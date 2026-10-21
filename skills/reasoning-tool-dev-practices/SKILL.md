---
name: reasoning-tool-dev-practices
description: Develop and test reasoning-tool internals in dev and test modes, including SMT/SAT solvers, provers, model checkers, optimization and synthesis tools. Use for input-driven fixes, pipeline changes, model or witness reconstruction, resource handling, and regression tests. Extrapolated by the skill authors from one developer's Z3 commit history, with a verified Z3 worked reference. Not for routine queries against these tools, general application development, or claiming formal correctness from test results.
license: MIT
---

# Reasoning tool development practices

Use these practices when changing or testing the internals of SMT/SAT solvers,
provers, model checkers, optimization tools, or synthesis tools.

The practices were distilled from **one developer on one project**: Nikolaj
Bjørner's public Z3 history (11,364 non-merge commits, 2012 to 2026).
**Applying them beyond Z3 is an extrapolation by the skill authors.** Nikolaj
Bjørner, Microsoft, and the Z3 project **did not write or endorse this skill**.
Everything needed to use it is in this file and, for Z3, in
`references/z3.md`; nothing here requires network access.

## Scope and modes

Use **dev** to fix behavior, add a feature, or refactor an internal component.
Use **test** to reproduce, classify, minimize, and record a regression. A fix
normally starts in test mode, moves to dev mode, and returns to test mode to
record the regression.

Do not use this skill for routine queries against a reasoning tool, general
application development, or as a substitute for a correctness proof. A small
input or API call can still be the reproducer for an internal bug.

## Prerequisites and setup

Read the target repository's contributor, build, and test instructions. Find
its supported input formats, result contracts, diagnostic options, parameter
registration, and regression and unit test mechanisms. Record the revision,
build configuration, toolchain, and relevant dependencies. Reuse existing
builds and follow the task's time, memory, and CPU limits.

For Z3, read `references/z3.md` for verified build commands, tracing, and
test conventions. For any other tool, locate these
facilities in its repository; do not assume Z3's commands, paths, or APIs apply.
No external checker is required to use this skill.

## Dev mode

1. **Start from an input.** For a reported failure, use test mode to get a
   small input or API script that preserves it. Record the command, revision,
   build, non-default options, random seed, and resource limits. For a new
   feature, start with a small example and its required semantics.
2. **Find the broken layer.** Map the actual pipeline: input or API handling,
   normalization, preprocessing, rewriting, search or solving, artifact
   reconstruction, and output. Some tools combine or reorder these stages.
   Use existing diagnostics and supported options to isolate where the
   invariant first fails. Disabling a transformation is a localization aid,
   not proof that it caused the bug. Remove temporary debugging output.
3. **Fix the invariant there, minimally.** Restore the contract at the layer
   that broke it rather than masking the symptom downstream. Include related
   reconstruction or interface changes when needed; minimizing the file count
   is not the goal.
4. **Put soundness before features.** State a rewrite's side conditions and
   restrict or remove it when they do not hold. Reject unsupported input or
   return the project's explicit unsupported or inconclusive result. Never
   convert unsupported input, timeout, cancellation, memory exhaustion, or
   `unknown` into a conclusive answer. Preserve the project's distinction
   between a feasible solution and a proved optimum, or a candidate and a
   verified witness.
5. **Preserve models and witnesses through preprocessing.** When eliminating
   variables or changing representations, keep enough reconstruction data to
   lift a model, counterexample, solution, or synthesized program back to the
   original input. Preserve proof or certificate validity through the same
   transformations when those artifacts are supported. Check artifacts
   against the original semantics, not just the simplified instance.
6. **Respect resource limits and cancellation.** Use the project's existing
   checks in long-running loops. Handle deep inputs with worklists or depth
   bounds where needed. Follow its interruption and exception contracts so
   cancellation and memory pressure leave safe state and an honest result.
   Do not swallow an interruption and return a success verdict. Test affected
   cleanup and incremental reuse paths where the API permits reuse.
7. **Keep uncertain heuristics configurable.** Use the project's parameter
   mechanism for heuristics whose benefit depends on the workload. Provide a
   way to compare or disable them, record seeds, and measure representative
   cases before changing defaults. An option is not a remedy for unsoundness.
8. **Separate cleanups.** Keep unrelated renaming, formatting, and refactoring
   out of the behavioral fix so reviewers can assess its effect. This is the
   skill authors' recommendation; the source history sometimes mixes them.
9. **Record the reason for the change.** Explain the broken invariant, the
   fix, and any issue reference. Keep claims tied to the checks actually run;
   follow the target repository's contribution conventions.

## Test mode

1. **Reproduce.** Run the exact input and options at a recorded revision and
   build. Capture output, exit status, diagnostics, and resource limits. Use
   the project's model, witness, proof, or certificate validation options
   where available and relevant.
2. **Classify the outcome.** Keep suspected failures distinct from confirmed
   ones; check the input semantics and the validator before blaming a result.

   | Outcome | What to record and establish |
   |---|---|
   | Crash or assertion violation | Reproduce with the project's debug or diagnostic build; record the failing assertion or stack and input. |
   | Soundness or artifact correctness bug | Identify the violated contract: a wrong conclusive answer, invalid model or witness, invalid proof, or wrong claimed optimum. A rejected model establishes a model-output failure once the validation is trusted; it does not by itself show the input is unsatisfiable. Conflicting solver verdicts need investigation, not a vote. |
   | Incompleteness or incomplete run | Record `unknown`, unsupported input, timeout, cancellation, or exhaustion and its cause. Distinguish a capability limit from a run cut short by its budget. None establishes a conclusive truth claim. |
   | Performance regression | Compare revisions or configurations on the same inputs, machine, build settings, options, seeds, and budgets. Report available search or resource statistics and repeat timings when noisy. Keep timed-out cases visible. |

3. **Minimize without changing the failure.** Reduce the input while the
   classified behavior persists. Keep the relevant logic, semantic
   assumptions, options, and proof or witness context. A smaller input that
   merely times out does not preserve a soundness failure.
4. **Record the regression using the repository's harness.** Find its input
   fixtures, assertions, expected results, and conventions for known failures.
   Derive or review the expected outcome independently of the fixed program's
   output; do not bless a result just because the new build prints it. Check
   semantic properties when exact textual output is unstable. Record seeds
   and budgets; avoid timing-dependent pass criteria for correctness tests.
5. **Add a component test when needed.** Use the project's unit test mechanism
   for invariants that an end-to-end input cannot reach reliably. Choose
   assertions that fail in the tested build configurations. For a behavioral
   fix, show that the regression distinguishes the affected and fixed builds
   when practical.
6. **Run the affected checks and report their scope.** Start with the
   reproducer and relevant component or regression tests, then run suites
   required by the target repository. Report passed, failed, inconclusive,
   and skipped checks separately. Consider the optional checks below when
   they would help assess a correctness claim.

## Optional external checks

These are suggestions from the skill authors, not practices established by
the commit analysis. Examples include checking a model under the original
constraints with a second SMT solver, validating a DRAT proof with
`drat-trim` or an LRAT proof with `cake_lpr`, checking a certificate, or
formalizing a lemma in a proof assistant. Use them only when the logic,
artifact format, and intended claim match the checker's capabilities.

Before using an external tool, check whether its executable is installed
locally with `command -v <tool>`, for example `command -v drat-trim`. Do not
download tools, data, or documentation from the network without the user's
permission. Confirm
its version, supported formats, and invocation from its documentation; do not
invent commands. A second solver's matching verdict alone does not validate
the first solver's model. The check must constrain or evaluate that model
against the original problem's semantics.

If the tool is not found, **warn the user, name the check skipped, explain
what that leaves unestablished, and continue** with available checks. For
example: "cake_lpr was not found; LRAT proof validation was skipped. The
unsatisfiability certificate remains unchecked by that checker."
**Never install tools silently or treat a skipped check as passed.** If an
installed checker fails, rejects an artifact, times out, or cannot handle the
input, report that outcome explicitly; it is not a successful validation.

Record the tool version, artifact, options, result, and scope of any completed
check. A checked certificate supports the claim it certifies under the
checker's assumptions. A proof of a lemma does not establish that the code
implements it, and testing does not establish general solver soundness.

## Expected output

- **dev**: a focused patch, the broken invariant and restored contract, an
  issue reference if available, and the tests and other checks run.
- **test**: a minimized reproducer, classification, revision, build, exact
  invocation and options, and regression or component test files as needed.
- **Both**: observed results, what checks establish, and what remains
  unestablished, including unavailable dependencies and skipped validation.

## Example

> Mode: test, then dev. A model checker returns a counterexample that cannot
> be replayed against the original transition system after preprocessing.

Reproduce with the reported options and minimize while replay still fails.
Localize whether the failure starts in preprocessing, witness reconstruction,
or replay. If preprocessing drops state needed for reconstruction, preserve
that information and add a regression that replays the reconstructed trace
against the original system. Use the repository's documented commands. If an
optional independent witness checker is unavailable, report the skipped
check and the lack of independent validation, then continue with local tests.

## Limitations

- The source is commit metadata and sampled diffs from one developer on Z3,
  not interviews, a cross-project study, or an evaluation of this skill.
  Applying the practices to other reasoning tools is an extrapolation.
- The analysis excluded commits mentioning Copilot; other agent-assisted
  commits may remain.
- Z3 paths and commands were checked at the revisions and date recorded in
  the provenance; recheck them against the local checkout. No other tool's
  layout or command line is asserted here.
- Follow the target project's semantics, contributor guidance, and review
  requirements. The skill does not establish patch correctness or cover
  build-system development, packaging, or release workflows.
