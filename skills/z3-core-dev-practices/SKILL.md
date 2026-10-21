---
name: z3-core-dev-practices
description: Development and testing practices for the Z3 SMT solver's C++ core (rewriters, simplifiers, SMT/SAT theory solvers, arithmetic, optimization, tactics, API), distilled from the public commit history of Z3's principal developer. Use when fixing a Z3 issue, changing solver internals, or adding regression and unit tests to Z3. Two modes, dev and test. Not for writing queries that use Z3, or for other solvers.
license: MIT
compatibility: Requires a local Z3 source checkout, a C++ toolchain and CMake; regression testing also uses a checkout of Z3Prover/z3test.
---

# Z3 core development practices

These practices were distilled from the public commit history of Nikolaj
Bjørner, Z3's principal developer: 11,364 non-merge commits on `master`,
2012 to 2026. They describe patterns observed in that history. **He did not
write or endorse this skill**, and it does not speak for him or the Z3 project.
See [PROVENANCE.md](PROVENANCE.md) and the
[commit analysis](references/commit-analysis.md) for the method and the
evidence behind each practice.

## Scope

Use this skill for work **inside** the Z3 repository (`Z3Prover/z3`):

- fixing a reported issue (crash, assertion violation, wrong `sat`/`unsat`,
  invalid model, regression, performance problem);
- changing a rewriter, simplifier, tactic, theory solver, the SAT core, model
  construction, optimization, or an API binding;
- reproducing a bug and turning it into a regression or unit test.

Do not use it for writing SMT-LIB or API queries *against* Z3, or as general
advice for other solvers; the conventions below are specific to Z3's code base
and test infrastructure.

Choose a mode:

- **dev**: change Z3's behavior (fix, feature, refactor).
- **test**: reproduce, classify, minimize, and record a regression.

A fix normally uses test mode first (reproduce) and last (record the
regression), with dev mode in between.

## Prerequisites and setup

Building Z3 takes several minutes and significant CPU. Ask before starting a
build, and reuse existing build directories.

```sh
# Debug build: enables SASSERT checks and TRACE output.
cmake -G Ninja -S . -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build --parallel

# Release build with tracing, for performance work that still needs traces.
cmake -G Ninja -S . -B build-rel -DCMAKE_BUILD_TYPE=Release -DZ3_ENABLE_TRACING_FOR_NON_DEBUG=ON

# Unit tests.
cmake --build build --target test-z3 --parallel
./build/test-z3 -a            # all tests in FOR_EACH_ALL_TEST
./build/test-z3 <name>        # one test, e.g. ./build/test-z3 totalizer
```

Regression tests live in a separate repository, `Z3Prover/z3test`. Check the
license of anything you copy from it. Cloning it uses the network:

```sh
git clone https://github.com/Z3Prover/z3test.git
python z3test/scripts/test_benchmarks.py ./build/z3 z3test/regressions/smt2
```

`test_benchmarks.py` runs each `<name>.smt2` with `model_validate=true` and
requires the output to match `<name>.expected.out` exactly. Files renamed to
`.smt2.disabled` are skipped.

Useful `z3` command-line switches: `-tr:<tag>` (trace a tag; needs a debug or
tracing build), `-v:<n>` (verbosity), `-st` (statistics), `-T:<seconds>`
(timeout), and `param=value` pairs such as `model_validate=true` or
`smt.arith.solver=6`.

## Dev mode

1. **Start from an input, not from the code.** Get the smallest SMT-LIB2 file
   or API script that shows the problem (test mode, steps 1–3). Record the Z3
   commit, the build type, and every non-default parameter. Most of the
   observed fixes are tied to a GitHub issue number with a reproducer.
2. **Find the layer where the invariant breaks.** Typical layers, in pipeline
   order: parsing and `cmd_context` → preprocessing (`ast/simplifiers`,
   `tactic`) → rewriting (`ast/rewriter`) → solving (`smt`, `sat/smt`,
   `math/lp`, `nlsat`, `opt`) → model construction (model converters) → API.
   Localize with `-tr:<tag>`, by turning preprocessing steps off through their
   parameters, and with `model_validate=true`. Add `TRACE(tag, tout << ...)`
   output where the state is unclear. New tags must be declared in
   `src/util/trace_tags.def`. Remove ad-hoc `std::cout` debugging before
   committing.
3. **Fix it there, minimally.** About half of the observed commits touch a
   single file and three quarters touch at most three. Prefer the smallest
   change that restores the invariant at the layer where it broke, instead of
   compensating downstream.
4. **Soundness comes before features.** When a rewrite rule is unsound outside
   its side conditions, the observed practice is to remove it or add the
   missing condition, not to patch the symptom. When a component cannot handle
   a construct, it should fail explicitly (for example by throwing
   `default_exception`, which surfaces as an error or `unknown`) rather than
   return an answer. Never turn a timeout, `unknown`, or a resource-limit
   exception into `sat` or `unsat`.
5. **Models must survive preprocessing.** Simplifiers that eliminate or
   replace variables must register what they did with the model converter so
   that the final model satisfies the *original* input. Check with
   `model_validate=true`.
6. **Respect resource limits.** Long-running loops must check for
   cancellation and resource limits. Deep terms must not overflow the stack:
   the history repeatedly replaces recursion with explicit worklists or adds
   depth bounds. Code that can be interrupted must catch the exceptions raised
   on cancellation and memory pressure.
7. **Make behavior configurable when its effect is uncertain.** New heuristics
   and transformations are typically added behind parameters, declared in
   `.pyg` parameter files, so that their effect can be measured and switched
   off. Measure before switching a default.
8. **Keep cleanups separate.** The history often mixes small modernizations
   (range-`for`, structured bindings) into fixes. An agent should not: put
   unrelated cleanup in a separate commit so the fix stays reviewable.
9. **Commit message.** Keep it short and reference the issue (`fix #1234`,
   `#1234 <what changed>`). Say what changed, not that it is now correct.

## Test mode

1. **Reproduce.** Run the input on a clean build at a recorded commit, with
   the exact parameters. Run it with `model_validate=true` as well.
2. **Classify the outcome before anything else:**
   - *crash or assertion violation*: reproduce in a debug build; record the
     `SASSERT` location;
   - *soundness bug*: a `sat` with a model that fails validation, or an
     `unsat` contradicted by a validated model from another configuration or
     solver. Agreement between configurations is evidence, not proof;
   - *incompleteness*: `unknown` or a timeout. This is not a soundness bug and
     should not be reported or tested as one;
   - *performance regression*: compare two commits with the same parameters
     and `-st`; report statistics, not only wall-clock time.
3. **Minimize.** Shrink the input while the classified behavior persists,
   using a delta debugger for SMT-LIB2 or by hand. Keep the declared logic and
   the parameters that matter.
4. **Record a regression in z3test** for issue-driven fixes: add
   `regressions/smt2/<issue>.smt2` and generate `<issue>.expected.out` from the
   *fixed* build. Then read the expected output and check that it is correct,
   not merely what Z3 currently prints. Use `.smt2.disabled` only for a known
   failure tracked in an issue. Avoid tests whose outcome depends on timing or
   random seeds.
5. **Add a unit test in `src/test/` for internal components** that SMT-LIB
   cannot reach directly (data structures, new solver modules, utilities).
   The convention is a file `src/test/<name>.cpp` defining `void
   tst_<name>()`, listed in `src/test/CMakeLists.txt` and registered as
   `X(<name>)` in `FOR_EACH_ALL_TEST` in `src/test/main.cpp`. Many existing
   tests are exploratory drivers that print results. Prefer checks with
   `ENSURE(...)` or `VERIFY(...)`, which also fail in release builds, over
   printed output that nobody compares.
6. **Run the relevant suites** (`test-z3 -a` and the affected z3test
   directories) and report what was run, what passed, and what was not run.

## Expected output

- **dev**: a minimal patch at the right layer, a commit message referencing the
  issue, and a short note on the invariant that was broken, how the fix
  restores it, and which tests cover it.
- **test**: a minimized reproducer, its classification, the exact command,
  commit, and parameters, and the regression or unit test files, with a clear
  split between what was observed (outputs, validated models) and what was not
  established (for example that an `unsat` answer is correct).

## Example

> Mode: test, then dev. Issue #NNNN reports that `(check-sat)` returns `sat`
> on a QF_LIA file, but `model_validate=true` reports an invalid model.

1. Reproduce at the recorded commit: `./build/z3 model_validate=true issue.smt2`.
2. Classify: soundness bug (invalid model). Minimize to a dozen lines.
3. Localize: disable preprocessing steps one at a time through their
   parameters until the model validates; trace the responsible simplifier.
4. Fix: the simplifier eliminated a variable without registering it with the
   model converter. Add the registration and nothing else.
5. Record `regressions/smt2/NNNN.smt2` and a reviewed `NNNN.expected.out` in
   z3test; run `test_benchmarks.py` on `regressions/smt2`.

## Limitations

- The practices are inferred from commit metadata and a sample of diffs, not
  from interviews or project documentation. They can be wrong, and they will
  drift as the code base changes. File paths and macros were checked against
  `master` at the revision in PROVENANCE.md.
- Commits since 2025 increasingly come from agent-assisted work. Commits that
  mention Copilot were excluded, but others may remain, so the analysis is
  weighted towards the earlier history.
- The skill does not replace Z3's own contributor documentation or maintainer
  review, and following it does not make a patch correct.
- It does not cover Z3's build, packaging, and release workflows (`scripts/`,
  `.github/`), although they account for many commits.

## References

- Z3 repository: https://github.com/Z3Prover/z3
- Z3 regression tests: https://github.com/Z3Prover/z3test
- [Commit analysis](references/commit-analysis.md): corpus, method, statistics,
  and the commits behind each practice.
