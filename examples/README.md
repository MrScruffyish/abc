# Worked examples

Each `.abc` file is a short input program. Run any of them with the work
trace to get both LaTeX on stdout and a complete `.tex` document:

```sh
./abc --show-your-work --work-level=methods \
      --work-file=/tmp/calculus.tex examples/calculus.abc
```

Use `--work-level=top`, `methods` or `all` (the default) to choose how much
detail to record.

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

The generated `.tex` files are self-contained articles; for example:

```sh
pdflatex /tmp/calculus.tex
```
