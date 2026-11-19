# abc: a work-tracing fork of xyz

`abc` is a sibling copy of [`../xyz`](../xyz). The original was **not**
changed. This repository is a normal git clone whose remote `xyz` points
at the original local checkout:

```
$ git -C ../abc remote -v
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
conflict; they are small and additive.

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

## How the trace works

`--show-your-work` enables `trace::Level::All`. Levels are cumulative:

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
* `sum` — `power sum` (Faulhaber), `shift bounds`, and the overall
  `Faulhaber's formula`.
* `gcd`/`cancel` — `remove content`, `Euclid step`, `divide out the gcd`
  and `make the denominator positive`.
* `solve` — `augmented matrix`, `eliminate column` and `back substitute`.
* `integrate` — `divide numerator by denominator`, `solve coefficients`,
  `by-parts terms`, `rewrite the differential`, `substitute`,
  `integrate in` and `back substitute`.
* `mulExpand` — each multiplication is shown in two phases: first the raw
  term-by-term products (`square`/`multiply`, plus `power as product` when a
  power is rewritten as a product), then `sum the terms` combines like
  terms. This is trace-only; the `expand` computation is unchanged.

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

## Testing

`make test` runs the golden, CLI and randomised suites. The randomised
suite has pre-existing flakes in `test_taylor` and `test_factor_gauss`;
for example seed `574894500` (`test_taylor`) and seed `617788697` (both)
fail identically with the unmodified `../xyz/xyz`. The deterministic
suites pass, and the generated LaTeX compiles with
`pdflatex` when it is installed (checked by `cli_tests.py`).

`make examples` (optionally with `WORK_LEVEL=all` or `top`) runs every
file in `examples/` through the tracer and writes the resulting `.tex`,
`.stdout.tex` and (when `pdflatex` is available) `.pdf` files into
`build/examples/`. It is a convenient smoke test that the whole pipeline
still works after merging an `xyz` update.
