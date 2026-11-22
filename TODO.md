# TODO

1. Run `make everything` and watch the six movies in `build/examples/`. Check the long-division rows in `abc-algebra.mp4` and `abc-calculus.mp4` for legibility now that the step labels are gone.
4. Make `make test` deterministic: give `tests/random_tests.py` a fixed `--seed` or fix the existing `trigreduce` / `factor_gauss` numeric flakes.
5. Eyeball the regenerated PDFs in `build/examples/` to confirm the label-free `align*` and `array` rows still lay out correctly.
6. Commit the integration (C++ renderers, Make targets, docs, tests) and record the upstream `xyz` merge plan in `ABC-NOTES.md`.

## DONE

2. Decided `--show-your-work` should default to `methods`, matching `--board-file` and the Makefile's `WORK_LEVEL`. Both renderers now show the same steps by default; a test checks that the plain flag matches an explicit `--work-level=methods`.
3. `tests/cli_tests.py` now compares the normalised math rows of both renderers for every example, so a missing, extra or reordered row in either renderer fails the suite. Verified it detects a deliberately dropped/changed row.

7. Generalise the rule from the `expand((x+2)^3)` fix: when a calculation continues over several lines, only the first line has a left-hand side; every continuation line leaves it empty and just starts with `=`. Applied in both renderers in `src/trace.cpp`: `boardStep()` drops the repeated left-hand side, and `stepLatex()` now emits `&= ...` on continuation rows.
8. Keep those continuation lines in one group in the board input, so a chained calculation is written as a single unit instead of separate scenes. `\begin{algorithm}` does not group (it expands to one latex block per line), so added a `\begin{rows} ... \end{rows}` directive to `board` itself that draws the rows as one stacked scene. `--board-file` now emits one rows block per chain; single-row steps stay ordinary scenes.
