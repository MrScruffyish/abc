# abc: a work-tracing fork of xyz

`abc` is a sibling copy of [`../xyz`](../xyz) and is its own program, hosted at
[`git@github.com:MrScruffyish/abc.git`](https://github.com/MrScruffyish/abc).
Its `origin` remote is that GitHub repo; the separate `xyz` remote points at
the original local checkout and is used only to pull upstream fixes:

```
$ git -C ../abc remote -v
origin	git@github.com:MrScruffyish/abc.git (fetch)
origin	git@github.com:MrScruffyish/abc.git (push)
xyz	/home/gunnar/MrScruffy/xyz (fetch)
xyz	/home/gunnar/MrScruffy/xyz (push)
```

## Bringing in later `xyz` changes

```
cd ../abc
git fetch xyz
git merge xyz/main
make test
```

Merge conflicts are most likely in the files listed below, because that is
where the tracing hooks live. Keep the `trace::...` calls when resolving a
conflict; they are small and additive. For example, the square-root support
added in `xyz` commit `7d8c2ae` was merged here and given trace steps.

* `Makefile` — binary renamed to `abc`, test targets updated.
* `src/main.cpp` — new CLI options and LaTeX document writing.
* `src/interpreter.{hpp,cpp}` — wrappers around `resolveKeep` and
  `callBuiltin`, statement/result/error capture, plain stdout suppressed
  while tracing.
* `src/simplify.cpp`, `src/factor.cpp`, `src/gcd.cpp`,
  `src/integrate.cpp`, `src/limit.cpp`, `src/numeric.cpp`, `src/solve.cpp`,
  `src/sum.cpp` — thin `*Impl` wrappers that label named algorithms.
* `tests/cli_tests.py` — renamed expectations and new flag tests.
* `tests/cases/05_functions.t` — the derivative of `(x+1)^3` is now the
  expanded `3*x^2+6*x+3` (see below).

New files: `src/trace.hpp`, `src/trace.cpp` and the runnable inputs in
`examples/`. The C++ namespace is still `xyz` inside the code; only the
binary, docs and messages are called `abc`. That keeps the diff small.

`--board-file=FILE` is a second renderer for the same `Step` list: the
`toBoard()` helpers in `src/trace.cpp` translate each step's LaTeX into the
small subset `board` understands and write one `$...$` formula per scene.
Both renderers print the statement once and then only mathematics; only the
wrappers differ (`align*`/`array` in LaTeX, `$...$` lines for board). A
chained calculation is one `align*` group in LaTeX and one `\begin{rows}`
block in board input, which `board` draws as a single stacked scene. Keep
the two renderers together when merging `xyz` changes; the `rows` directive
lives in `board` itself (no `--expand` needed), so update both repositories.

### Merge checklist

`xyz/main` is currently `7d8c2ae`, already merged here as `1fde401`; abc is
16 commits ahead. When new upstream commits appear:

1. `git fetch xyz && git merge xyz/main`. Resolve the conflict-prone files
   listed above by keeping every `trace::step` call at its existing loop
   point (the wrappers are additive and do not change results).
2. Rebuild and run `make test`. The CLI suite includes a renderer-parity
   check that compares the normalised math rows of `--show-your-work` and
   `--board-file` for every example, so a fix applied to only one renderer
   fails here. `random_tests.py` runs with a pinned `SEED`; override it with
   `SEED=...` only when deliberately hunting for new numeric cases.
3. If an `xyz` change adds a new algorithm, give it a `methods`-level trace
   in the matching `*Impl` wrapper and extend both renderers' regression
   expectations. If it changes `toLatex()` output, update `toBoard()` in
   `src/trace.cpp` and the parity normaliser in `tests/cli_tests.py`
   together.
4. If board's input language changes, update `../Black-Bored-By-Numbers` in
   its own commit first — in particular the `\begin{rows}` directive is a
   core (non-`--expand`) feature that `--board-file` depends on.
5. Finish with `make everything` and spot-check the regenerated PDFs and
   movies before merging upstream changes into abc's history.

## How the trace works

`--show-your-work` and `--board-file` both enable `trace::Level::Methods` by
default; pass `--work-level=all` for the full trace. Levels are cumulative:

| Level     | Captured |
|-----------|----------|
| `top`     | statement source, builtin calls, printed results, errors |
| `methods` | named algorithms (expand, factor, solve, integration by parts, L'Hopital, ...) |
| `all`     | every expression rewrite seen by `resolveKeep` and every automatic simplification |

Steps are stored as expressions and rendered with the existing `toLatex()`
when a statement finishes. The same LaTeX block goes to stdout and into
the article written by `--work-file=FILE` (default `work.tex`). Plain-text
results are suppressed while tracing so that stdout is LaTeX only.

To keep pathological inputs safe there are caps of 400 steps per statement
and 8000 per run; the LaTeX notes when steps were omitted.

## Showing algorithms as simpler steps

At `methods` level the tracer now prints the smaller operations that the
named algorithms are built from, using intermediate expression values the
algorithms already compute (tracing does not change the calculation):

* `polyDivide` — each `long-division step` shows the updated quotient and
  remainder.
* `simpPow` — `sqrt` of a perfect-square polynomial shows `leading term`,
  `next coefficient` and `verify the square`; steps are buffered and only
  emitted once the whole polynomial is known to be a square.
* `factor` — `possible rational roots` lists the candidates (divisors of
  the constant term over divisors of the leading coefficient, capped at 24
  shown); `try the candidates` shows `p(r)` for each one and its value, so
  the zeros are the roots. `rational root` then states `p(r) = 0` (a root is
  a value of `x`, not of `p`); `divide by the root` shows the division that
  removes it. `Kronecker
  factor` and `divide by the factor` do the same for the higher-degree
  factors found by interpolation.
* `sum` — `power sum` (Faulhaber), `shift bounds`, and the overall
  `Faulhaber's formula`.
* `gcd`/`cancel` — `remove content`, `Euclid step`, `divide out the gcd`
  and `make the denominator positive`. `cancel` instead presents the whole
  calculation as one block: `Finding GCD:` (every subtraction, with the
  product expanded and terms collected, then `GCD = ...`), `Divide out the
  GCD:` and `Canceling:` (the fraction with numerator and denominator
  factored by the GCD). A quotient of equal polynomials is written directly;
  otherwise the division is laid out as a schoolbook long division (divisor,
  quotient, each subtraction and remainder) using `DivStep`s collected from
  `exactDiv`. Internal steps are hidden with `trace::Silence` while that
  block is collected, so the confusing bare `expand` steps no longer appear.
* `solve` — `augmented matrix`, `eliminate column` and `back substitute`.
* `integrate` — `divide numerator by denominator`, `solve coefficients`,
  `by-parts terms`, `rewrite the differential`, `substitute`,
  `integrate in` and `back substitute`.
* `mulExpand` — each multiplication is shown in two phases: first the raw
  term-by-term products (`square`/`multiply`, plus `power as product` when a
  power is rewritten as a product), then `sum the terms` shows only
  `= <combined terms>` (the raw products are already on the previous line).
  This is trace-only; the `expand` computation is unchanged.

When merging an `xyz` update, keep these `trace::step` calls at their
existing loop points; a conflict is most likely in the same files listed
above.

## Polynomial derivatives by limits

For a simple polynomial (degree 1..20, at most 30 coefficients) `diff` now
computes the derivative from the difference quotient rather than by the
power rule: it substitutes `f(x+h)`, expands `f(x+h)-f(x)`, divides by `h`,
cancels the `h` factor and takes `limit(..., h, 0)`. This is a real
computation change: results can come out expanded, e.g.
`diff((x+1)^3, x)` is `3*x^2+6*x+3` instead of `3*(x+1)^2`. It also uses a
fresh increment (`h`, or `~h`, `~h1`, …) when the expression already uses
`h`, and a `thread_local` guard prevents `limit` → L'Hopital → `diff` from
recursing back into the limit definition. Expressions that are not small
polynomials still use the ordinary derivative rules. With
`--show-your-work` the quotient, cancellation and limit are printed at
`methods` level.

## Trace rows must be true statements

Some methods produce an operator result rather than a rewrite, so `before =
after` would be false. These `abc` traces therefore use explicit notation
instead of `trace::step`:

* `diff` writes `\frac{d}{dx} \left(f\right) = f'` (not `f = f'`).
* L'Hopital writes the limit on both sides of the equality (not `f =
  f'/g'`); the limit point and one-sided superscript come from the `Limit`
  being evaluated.
* a rational root writes `p(r) = 0` (not `p(x) = r`).

`\operatorname` is used for `lim` because the board parser accepts it after
`abc`'s LaTeX-to-board conversion (a bare `\lim` would not survive). The
rows compile with `pdflatex` and pass `board --syntax-check`.

## Testing

`make test` runs the golden, CLI and randomised suites. The randomised
suite has pre-existing numeric flakes in `test_taylor`, `test_trigreduce`
and `test_factor_gauss` that also fail with the unmodified `../xyz/xyz`;
`make test` therefore passes a fixed `SEED ?= 12345` so results are
reproducible. Override with `SEED=...` to look for new cases. The
deterministic suites pass, and the generated LaTeX compiles with
`pdflatex` when it is installed (checked by `cli_tests.py`).

`make examples` (optionally with `WORK_LEVEL=all` or `top`, or `ONLY=name`)
runs the examples through the tracer and writes `.tex`, `.stdout.tex`,
`abc-<name>.txt` and (when `pdflatex` is available) `.pdf` files into
`build/examples/`. `make movies` renders the inputs to `abc-<name>.mp4` in
the same directory, and `make everything` does both. They are convenient
smoke tests that the whole pipeline still works after merging an `xyz`
update.
