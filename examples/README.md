# Worked examples

Each `.abc` file is a short input program. Run any of them with the work
trace to get both LaTeX on stdout and a complete `.tex` document:

```sh
./abc --show-your-work --work-level=methods \
      --work-file=/tmp/calculus.tex examples/calculus.abc
```

Use `--work-level=top`, `methods` (the default) or `all` to choose how much
detail to record.

From the project root, `make examples` builds all of them at once into
`build/examples/`: `<name>.tex` (the self-contained article),
`<name>.stdout.tex` (the LaTeX printed on stdout), `abc-<name>.txt` (board
input) and, if `pdflatex` is installed, `<name>.pdf`. Every path is
printed, and `ONLY=algebra` builds just one example. Use
`make examples WORK_LEVEL=all` for the most detailed trace.

| File | What it shows |
|------|---------------|
| `algebra.abc` | expanding powers, factoring by roots and Kronecker interpolation, cancelling, perfect-square roots |
| `assumptions.abc` | sign and integer assumptions changing roots, logs, trig and solving |
| `calculus.abc` | differentiation, higher derivatives, integration by parts, substitution, definite integrals |
| `complex.abc` | complex arithmetic, `Re`/`Im`/`conj`/`abs`, Gaussian gcd/cancel/factor |
| `equations.abc` | linear, quadratic, cubic and symbolic equations, systems and edge cases |
| `functions.abc` | trig, inverse trig, exponential, logarithms, hyperbolic functions and trig identities |
| `limits.abc` | one-sided limits, limits at infinity, L'Hopital and Taylor series |
| `lists.abc` | list literals, indexing, elementwise arithmetic and `table` ranges |
| `logic.abc` | comparisons, Boolean operators and symbolic equality tests |
| `numbers.abc` | exact rationals, big integers, powers, roots and decimal approximations |
| `polynomials.abc` | polynomial `gcd`/`lcm`, `quo`/`rem`, `deg` and `coeff` |
| `programming.abc` | `=`/`:=`, user functions, `eval`/`subs`, `if`, loops and tables |
| `sums.abc` | closed forms with symbolic bounds, ranges, steps, lists and `seq` |

Other useful variations:

```sh
./abc --work-level=top examples/algebra.abc
./abc --work-level=all examples/algebra.abc
./abc --show-your-work=all --work-file=/tmp/all.tex examples/algebra.abc
./abc --board-file=- --work-level=all examples/numbers.abc
./abc --expression=2^10
./abc --trunc -e 'num(2/3, 5)'
./abc --imag=i -e '(3+2i)*(1-i)'
```

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
