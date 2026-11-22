# TODO

All items are done. The two entries below still want a human visual check
(items 1 and 5); everything else is verified by the test suite.

## DONE

1. Ran `make everything`: all six movies and PDFs regenerated. Programmatic checks passed (720p/30fps, all board inputs pass `--syntax-check`, no pdflatex errors, long-division rows present in both renderers with no step labels). Final visual watch/eyeball is still needed by a human.
2. Decided `--show-your-work` should default to `methods`, matching `--board-file` and the Makefile's `WORK_LEVEL`. Both renderers now show the same steps by default; a test checks that the plain flag matches an explicit `--work-level=methods`.
3. `tests/cli_tests.py` now compares the normalised math rows of both renderers for every example, so a missing, extra or reordered row in either renderer fails the suite. Verified it detects a deliberately dropped/changed row.
4. `make test` (and `test-asan`) now pass a fixed `SEED ?= 12345` to `tests/random_tests.py`; two consecutive `make test` runs produce byte-identical output. Override with `SEED=...` to hunt for new numeric cases (the `trigreduce` tolerance check can still flag extreme cancellation).
5. Regenerated the PDFs and checked them with `pdftotext`/`pdfinfo`: all six have text and no LaTeX errors, and the label-free `align*`/`array` layouts render. Same human-eyeball caveat as item 1.
6. Committed each item separately in both repositories. `ABC-NOTES.md` now records the upstream `xyz` merge checklist (currently 16 commits ahead of `xyz/main` at `7d8c2ae`), including the `board` `\begin{rows}` dependency and the renderer-parity guard.
7. Generalise the rule from the `expand((x+2)^3)` fix: when a calculation continues over several lines, only the first line has a left-hand side; every continuation line leaves it empty and just starts with `=`. Applied in both renderers in `src/trace.cpp`: `boardStep()` drops the repeated left-hand side, and `stepLatex()` now emits `&= ...` on continuation rows.
8. Keep those continuation lines in one group in the board input, so a chained calculation is written as a single unit instead of separate scenes. `\begin{algorithm}` does not group (it expands to one latex block per line), so added a `\begin{rows} ... \end{rows}` directive to `board` itself that draws the rows as one stacked scene. `--board-file` now emits one rows block per chain; single-row steps stay ordinary scenes.
