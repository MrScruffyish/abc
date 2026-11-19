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

## Testing

`make test` runs the golden, CLI and randomised suites. The randomised
suite has a pre-existing numerical flake in `test_taylor`; for example
seed `574894500` fails identically with the unmodified `../xyz/xyz`.
The deterministic suites pass, and the generated LaTeX compiles with
`pdflatex` when it is installed (checked by `cli_tests.py`).
