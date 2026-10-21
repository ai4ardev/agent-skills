# Commit analysis behind this skill

## Corpus

- Repository: https://github.com/Z3Prover/z3, branch `master` at
  `a200baf4416121d396ed5e1f63aa7005d2658715` (2026-10-21).
- Author filter: commits whose author name is a spelling of Nikolaj Bjorner
  (`Nikolaj Bjorner`, `NikolajBjorner`, `nikolajbjorner`) or whose author is
  `unknown` with an `nbjorner@` address. Two commits recorded under other
  names with his address were excluded.
- Excluded: merge commits, and commits whose subject or body mentions Copilot
  (270 commits, almost all from 2026).
- Result: **11,364 commits**, 2012-10-08 to 2026-10-21.

```sh
git clone --bare --filter=blob:none https://github.com/Z3Prover/z3.git z3.git
git -C z3.git log master --no-merges -P \
  --author='^(Nikolaj ?Bjorner|nikolajbjorner|NikolajBjorner|unknown <nbjorner)' \
  --format='%H%x00%cs%x00%s%x00%b%x01' --name-only
```

Statistics were computed from that output; diffs were read for a random
sample of issue fixes and of commits that add unit tests.

## Statistics

| Measure | Value |
|---|---|
| Commits that touch at most 1 file | 48.1% |
| Commits that touch at most 3 files | 76.7% |
| Subjects referencing a GitHub issue (`#NNNN`) | 27.9% |
| Subjects of the form `fix #NNNN` or `#NNNN` | 1,981 commits |
| Commits touching `src/test/` | 3.6% |

Most-touched areas (number of commits touching each, whole history, merges
included): `src/smt` 2,793; `src/ast/rewriter` 1,161; `src/ast` 1,061;
`scripts` 1,028; `src/sat` 1,012; `src/sat/smt` 828; `src/opt` 735;
`src/util` 659; `src/api` 578; `src/math/lp` 515. Since 2022 the emphasis
shifts towards `src/sat/smt`, `src/math/lp`, `src/ast/sls`, and
`src/ast/simplifiers`.

The low share of commits touching `src/test/` reflects where tests live:
issue regressions go to the separate `Z3Prover/z3test` repository as
`regressions/smt2/<issue>.smt2` with a `.expected.out` file.

## Commits behind each practice

Short hashes refer to `Z3Prover/z3`. Subjects are quoted as recorded.

| Practice (SKILL.md) | Examples |
|---|---|
| Issue-driven, minimal fixes (dev 1, 3) | `868a6b359` "fix #3521" (one-line change in `opt/optsmt.cpp`); `f33d6f89b` "fix #4973" (two lines in `smt/smt_setup.cpp`) |
| Remove unsound rewrites (dev 4) | `dee8a9f30` "remove more unsound rewrites #2575"; `be4df46f6` "#5532 remove unsound rewrite rule that was recently added"; `864eaf8bf` "remove unsound rewrite #4778" |
| Fail explicitly on unsupported constructs (dev 4) | `498c9a686` "throw exceptions where sls lacks support" |
| Models after preprocessing (dev 5) | `e683f4be2` "#4525 regression in model generation"; `13be3c3fb` "reset model converter between rounds to elim-unconstrained." |
| Recursion and depth (dev 6) | `dbd5512d8` "ensure enode without recursion"; `6ea68310c` "fix stack overflow regression in bool_rewriter"; `c7a6721bf` "lessen depth expansin in nnf, add cancelation, add ast_marking to avoid repeated sub-expressions #3065" |
| Cancellation and limits (dev 6) | `25feb0ebe` "#5938 catch also rewriter_exception that can be raised on cancelation and memory pressure"; `11736f078` "ensure statistics survive cancelation in tactics" |
| Parameters for uncertain behavior (dev 7) | `8d2b65b20` "add options to allow testing the effect of non-linear hammers"; `63ac2ee0d` "#5614 turn on / off options to get better performance." |
| Unit-test drivers (test 5) | `5afcb489e` "adding totalizer" (adds `src/test/totalizer.cpp`); `624907823` "add tests for distribution utility and fix loose ends" |
| Regressions in z3test (test 4) | `1d83ecb9d` "Move SMTLIB2 verdict unit tests to z3test regressions" |

## What this analysis does not show

- Intent. Commit metadata shows what changed, not why one option was chosen
  over another.
- Review. Practices that happen in pull-request discussion or outside Git are
  invisible here.
- Completeness. Sampling diffs can miss patterns that are rare but important.
