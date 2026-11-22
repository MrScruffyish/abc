# Worked examples

Each `.abc` file is a short input program. Run any of them with the work
trace to get both LaTeX on stdout and a complete `.tex` document:

```sh
./abc --show-your-work --work-level=methods \
      --work-file=/tmp/calculus.tex examples/calculus.abc
```

Use `--work-level=top`, `methods` or `all` (the default) to choose how much
detail to record.

From the project root, `make examples` builds all of them at once into
`build/examples/`: `<name>.tex` (the self-contained article),
`<name>.stdout.tex` (the LaTeX printed on stdout), `abc-<name>.txt` (board
input) and, if `pdflatex` is installed, `<name>.pdf`. Every path is
printed, and `ONLY=algebra` builds just one example. Use
`make examples WORK_LEVEL=all` for the most detailed trace.

| File | What it shows |
|------|---------------|
| `algebra.abc` | expanding powers, factoring polynomials, cancelling a common factor |
| `equations.abc` | one equation, a linear system and a nonlinear system |
| `calculus.abc` | differentiation, integration by parts, L'Hopital's rule, Taylor series |
| `sums.abc` | closed forms with symbolic bounds, finite ranges and lists |
| `assumptions.abc` | how `assume(x > 0)` changes simplification and solving |
| `numbers.abc` | exact rationals, decimal approximations and complex numbers |

To see the ordinary (non-LaTeX) results, run a file without the flag:

```sh
./abc examples/algebra.abc
```

To turn those steps into blackboard videos, run `make movies` (slow) or
`make everything` for input files and movies together. `ONLY=numbers`
limits either command to one example:

```sh
make movies ONLY=numbers
```

`abc` writes the steps as board formulas (`--board-file`) or as LaTeX rows
(`--show-your-work`), with the statement as the only explanatory line and no
step labels in either case; then `board` renders `build/examples/abc-numbers.txt`
to `build/examples/abc-numbers.mp4`. Set `BOARD` if the executable is not
at `../Black-Bored-By-Numbers/board`. See the main README for the other
options.

The generated `.tex` files are self-contained articles; for example:

```sh
pdflatex /tmp/calculus.tex
```
