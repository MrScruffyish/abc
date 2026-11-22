# TODO

1. Run `make everything` and watch the six movies in `build/examples/`. Check the long-division rows in `abc-algebra.mp4` and `abc-calculus.mp4` for legibility now that the step labels are gone.
2. Decide whether `--show-your-work` should default to `methods` like `--board-file`; right now plain CLI traces use `all`, so the two renderers only match when `WORK_LEVEL=methods` is set.
3. Add a regression test that compares the math rows of `--show-your-work --work-level=methods` with `--board-file` for each example, so the LaTeX and board renderers cannot drift apart.
4. Make `make test` deterministic: give `tests/random_tests.py` a fixed `--seed` or fix the existing `trigreduce` / `factor_gauss` numeric flakes.
5. Eyeball the regenerated PDFs in `build/examples/` to confirm the label-free `align*` and `array` rows still lay out correctly.
6. Commit the integration (C++ renderers, Make targets, docs, tests) and record the upstream `xyz` merge plan in `ABC-NOTES.md`.

## DONE

7. Generalise the rule from the `expand((x+2)^3)` fix: when a calculation continues over several lines, only the first line has a left-hand side; every continuation line leaves it empty and just starts with `=`. Applied in both renderers in `src/trace.cpp`: `boardStep()` drops the repeated left-hand side, and `stepLatex()` now emits `&= ...` on continuation rows.
8. Keep those continuation lines in one group in the board input, so a chained calculation is written as a single unit instead of separate scenes. `\begin{algorithm}` does not group (it expands to one latex block per line), so added a `\begin{rows} ... \end{rows}` directive to `board` itself that draws the rows as one stacked scene. `--board-file` now emits one rows block per chain; single-row steps stay ordinary scenes.
