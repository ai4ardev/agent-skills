# Worked instantiation: cvc5

Use this reference when applying the skill inside `cvc5/cvc5`. Commands,
paths, options, and macros were checked against cvc5 `main` at
`f250cf18eebd6b22e2ac0d5e654ce5640699dce1` (2026-10-22). This is a worked
instantiation, not a layout to assume for other tools. Recheck it against
your checkout.

## Build and tests

```sh
./configure.sh debug          # assertions and tracing on; build dir ./build
cd build && make -j8          # binaries in build/bin
ctest -L regress0             # level-0 regressions (<= 1 s each)
ctest -L unit                 # unit tests (test/unit)
ctest -R <regex> --output-on-failure
TEST_TIMEOUT=0.5 ctest -L regress0
CVC5_REGRESSION_ARGS="--ackermann" ctest -L regress0
```

Other build types: `unrestricted`, `stable`, `safe`, `testing`,
`competition`; `--assertions` and `--tracing` add those to an optimized build,
and `--name=<dir>` picks the build directory. `--auto-download` fetches
missing dependencies from the network; ask before using it. Reuse existing
build directories.

## Regressions

Regressions live in `test/regress/cli/regress0` to `regress4`, by run time
(level 0 at most 1 s, 1 at most 5 s, 2 at most 10 s, 3 at most 100 s, 4
longer). A new file must also be listed in `test/regress/cli/CMakeLists.txt`.
Moving a slow regression means moving it to a higher level, not deleting it.

Directives go in comments (`;` in SMT-LIB files):

- `EXPECT:`, `EXPECT-ERROR:`, `EXIT:` for expected output and exit status.
- `COMMAND-LINE:` for options; several lines run the file once per line.
  Do not put `--safe-mode` or `--check-proofs` there; the build and the
  proof testers handle them.
- `REQUIRES:` for build features (e.g. `cryptominisat`,
  `unrestricted-mode`).
- `DISABLE-TESTER:` to skip one tester for this file, e.g. `alethe` with a
  comment saying why. Disabling `proof` also disables the testers that check
  external proof formats.
- `SCRUBBER:` / `ERROR-SCRUBBER:` to normalize output before comparison.

`test/regress/cli/run_regression.py` runs one file:
`run_regression.py [--tester T ...] <cvc5 binary> <benchmark>`. Testers are
`base`, `unsat-core`, `proof`, `model`, `synth`, `abduct`, `dump` (the
defaults), plus `alethe`, `cpc`, and `cpc-logos`, which need external
checkers passed with `--carcara-binary`, `--ethos-binary`, or
`--logos-binary`.

Prefer expectations that survive unrelated improvements: when any unsat core
is acceptable, do not hard-code its size.

## Useful options

- `--produce-proofs`, `--check-proofs`, `--dump-proofs`,
  `--proof-check=MODE`, `--proof-format-mode=MODE` (e.g. `alethe`).
- `--check-models`, `--check-unsat-cores`.
- `-t <tag>` / `--trace=<tag>` (tracing builds only; wildcards allowed),
  `--verbosity=N`, `--stats`, `--tlimit=MS`.

## Code conventions seen in review

- Assertions: `Assert(cond)` is active only with assertions enabled;
  `AlwaysAssert(cond)` always; `Unreachable()` and `Unhandled()` for
  impossible or unhandled cases (`src/base/check.h`). Reviews asked for these
  instead of exceptions.
- Tracing: `Trace("tag") << ...;` and `TraceIsOn("tag")` to guard work done
  only for tracing (`src/base/output.h`).
- Proof rules are documented in `include/cvc5/cvc5_proof_rule.h` as
  reStructuredText inside the comments (`\verbatim embed:rst:leading-asterisk`,
  `\inferrule`). Match the existing heading style, capitalization, and
  punctuation; describe introduced skolems and mark optional arguments the
  way existing rules do.
- Formatting: `contrib/format-code.sh check` (or `fix`), which requires
  `clang-format` 22 or newer and uses the repository's `.clang-format`.
- `NEWS.md` holds user-visible changes only.
- Contributions are squashed into one commit and signed off
  (`git commit -s`, Developer Certificate of Origin), per `CONTRIBUTING.md`.
  Pull request titles commonly carry area tags such as `[proofs]` or
  `[alethe]`.

## External checkers

`contrib/get-carcara-checker`, `contrib/get-ethos-checker`, and
`contrib/get-logos-checker` download and build checkers from the network.
Running them is a download: ask first. If a checker is not installed, skip
the corresponding tester, say so, and report that the proofs were not checked
by it, as described in SKILL.md ("Optional external checks").
