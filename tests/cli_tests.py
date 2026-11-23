#!/usr/bin/env python3
# Command-line interface tests for abc: pipes, files, -e, options.
# Copyright (C) 2026 Gunnar Lindholm
# SPDX-License-Identifier: GPL-3.0-or-later
import os
import pty
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time

failures = 0


def run(binary, args, stdin=""):
    p = subprocess.run([binary] + args, input=stdin, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, text=True, timeout=60)
    return p.stdout, p.stderr, p.returncode


def run_tty(binary, text):
    """Runs abc with a pseudo-terminal as stdin (interactive mode)."""
    master, slave = pty.openpty()
    p = subprocess.Popen([binary], stdin=slave, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True)
    os.close(slave)
    os.write(master, text.encode())
    os.write(master, b"\x04")  # end of input (Ctrl-D)
    out, _ = p.communicate(timeout=60)
    os.close(master)
    return out


def run_editing(binary, keys):
    """Runs xyz with stdin and stderr on a pseudo-terminal, so that line
    editing is used if abc was built with readline. Returns stdout."""
    master, slave = pty.openpty()
    env = dict(os.environ, TERM="xterm")
    p = subprocess.Popen([binary], stdin=slave, stdout=subprocess.PIPE,
                         stderr=slave, text=True, env=env)
    os.close(slave)

    def drain():  # read the terminal side like a real terminal would
        try:
            while os.read(master, 4096):
                pass
        except OSError:
            pass
    reader = threading.Thread(target=drain, daemon=True)
    reader.start()
    for line in keys.splitlines(keepends=True):
        time.sleep(0.2)  # let readline switch the terminal to raw mode
        os.write(master, line.encode())
    time.sleep(0.2)
    os.write(master, b"\x04")  # Ctrl-D at the start of a line: end
    out, _ = p.communicate(timeout=60)
    os.close(master)
    return out


def has_readline(binary):
    # the binary links readline if it contains readline's symbols
    with open(binary, "rb") as f:
        return b"rl_outstream" in f.read()


def check(name, got, want):
    global failures
    if got != want:
        failures += 1
        print(f"FAIL {name}\n  expected {want!r}\n  got      {got!r}")


# --show-your-work and --board-file render the same Step list. Compare the rows
# they emit for every example, after stripping only the formatting that is
# deliberately different (LaTeX row separators and align markers vs board's
# $...$ lines and \begin{rows} blocks). Any missing, extra or reordered row
# then means the two renderers have drifted apart.
PLAIN_COMMANDS = ("sin", "cos", "tan", "asin", "acos", "atan", "sinh", "cosh",
                  "tanh", "exp", "ln", "log", "arcsin", "arccos", "arctan")
WRAPPERS = ("operatorname", "mathrm", "text", "textit", "texttt", "mathbf",
            "mathsf", "mathtt", "mathit", "boldsymbol", "emph")


def latex_blocks(text):
    """Split a work trace into (statement, align rows) pairs."""
    pattern = (r"\\begin\{verbatim\}\n(.*?)\\end\{verbatim\}\n"
               r"(?:\\begin\{align\*\}\n(.*?)\\end\{align\*\}\n)?")
    return [(m.group(1).strip(), (m.group(2) or "").splitlines())
            for m in re.finditer(pattern, text, re.S)]


def board_blocks(text, sources):
    """Split board input into the rows following each statement line."""
    lines = [l for l in text.splitlines() if l and not l.startswith("#")]
    blocks, pos = [], 0
    for k, src in enumerate(sources):
        start = lines.index("$" + src + "$", pos)
        later = ["$" + s + "$" for s in sources[k + 1:]]
        end = next((j for j in range(start + 1, len(lines)) if lines[j] in later),
                   len(lines))
        blocks.append((src, lines[start + 1:end]))
        pos = start + 1
    return blocks


def canonical_row(row, in_array):
    row = re.sub(r"\\(?:" + "|".join(WRAPPERS) + r")\{([^{}]*)\}", r"\1", row)
    row = re.sub(r"\\(?:ldots|cdots|dots)", "...", row)
    row = re.sub(r"\\(" + "|".join(PLAIN_COMMANDS) + r")", r"\1", row)
    row = row.replace("&", ":" if in_array else "")
    row = re.sub(r"\\cline\{[^}]*\}", "", row)
    return re.sub(r"\s+", "", row)


def trace_rows(rows, latex):
    """The mathematical content of one statement's rows, in order."""
    out, in_array = [], False
    for row in rows:
        row = row.strip()
        if latex:
            row = row.replace("\\\\", "").strip()
            if row.startswith(r"\begin{array}"):
                in_array = True
                continue
            if row == r"\end{array}":
                in_array = False
                continue
        else:
            if row in (r"\begin{rows}", r"\end{rows}"):
                continue
            if row.startswith("$") and row.endswith("$"):
                row = row[1:-1]
        row = canonical_row(row, in_array)
        if row:
            out.append(row)
    return out


def renderer_drift(latex_text, board_text):
    """Describe any row-level differences between the two renderers."""
    blocks = latex_blocks(latex_text)
    board = board_blocks(board_text, [src for src, _ in blocks])
    drift = []
    for (src, latex_rows), (_, board_rows) in zip(blocks, board):
        a, b = trace_rows(latex_rows, True), trace_rows(board_rows, False)
        if a != b:
            drift.append((src, a, b))
    return drift


def main():
    b = sys.argv[1] if len(sys.argv) > 1 else "./abc"
    with tempfile.TemporaryDirectory() as d:
        f1 = os.path.join(d, "one.xyz")
        f2 = os.path.join(d, "two.xyz")
        with open(f1, "w") as f:
            f.write("a := x+1;\n# comment\nexpand(a^2)\n")
        with open(f2, "w") as f:
            f.write("x = 2;\na\n1/0\n")

        check("pipe", run(b, [], "a=4; b=a*a+3;\nb\n"), ("19\n", "", 0))
        check("pipe without trailing newline", run(b, [], "1+1"), ("2\n", "", 0))
        check("empty input", run(b, [], ""), ("", "", 0))
        check("-e", run(b, ["-e", "expand((x+2)^2)"]), ("x^2+4*x+4\n", "", 0))
        check("--expression=", run(b, ["--expression=2^10"]), ("1024\n", "", 0))
        check("several -e share variables",
              run(b, ["-e", "a := x;", "-e", "b := a*a+3;", "-e", "eval(b, x=1)"]),
              ("4\n", "", 0))
        check("-e does not read stdin", run(b, ["-e", "1"], "2\n"), ("1\n", "", 0))
        check("-e then stdin with -", run(b, ["-e", "a = 5;", "-"], "a*2\n"),
              ("10\n", "", 0))
        check("files share variables", run(b, [f1, f2]),
              ("x^2+2*x+1\n3\n", "error: line 3: division by zero\n", 1))
        check("-e before files", run(b, ["-e", "a := y;", f2]),
              ("y\n", "error: line 3: division by zero\n", 1))
        check("quit in -e stops everything", run(b, ["-e", "disp(1); quit", f1]),
              ("1\n", "", 0))
        check("missing file", run(b, [os.path.join(d, "nope")])[1:],
              (f"abc: cannot open {os.path.join(d, 'nope')}\n", 1))
        check("unknown option exit status", run(b, ["-z"])[2], 2)
        check("-e needs an argument", run(b, ["-e"])[1:],
              ("abc: option -e needs an argument\n", 2))
        out, err, code = run(b, ["--help"])
        check("--help", (out.startswith("usage: abc"), err, code), (True, "", 0))
        out, err, code = run(b, ["-v"])
        check("--version mentions licenses",
              ("GPL" in out and "BSD 2-Clause" in out, code), (True, 0))
        check("-- ends options", run(b, ["--", f1]), ("x^2+2*x+1\n", "", 0))
        check("assignments echo unless ';'", run(b, [], "a = 2\nb = 3;\nb\n"),
              ("a = 2\n3\n", "", 0))
        # interactive mode: each finished statement runs as soon as it is typed
        check("interactive: unfinished lines wait",
              run_tty(b, "(1+\n2)\nf(x) := (x+\n1)\nf(1)\nif (1)\n{\ndisp(7)\n}\n"),
              "3\nf(x) := x+1\n2\n7\n")
        check("interactive: if, then else typed on later lines (taken)",
              run_tty(b, "a = 2;\nif (a == 2)\n{ b = 3; }\nelse { b = 10; }\nb\n"),
              "3\n")
        check("interactive: if, then else typed on later lines (not taken)",
              run_tty(b, "a = 5;\nif (a == 2)\n{ b = 3; }\nelse { b = 10; }\nb\n"),
              "10\n")
        check("interactive: errors have no line numbers",
              run_tty(b, "1/0\n"), "error: division by zero\n")
        if has_readline(b):
            left, up = "\x1b[D", "\x1b[A"
            check("line editing: left arrow",
                  run_editing(b, "23" + left + "+\n"), "5\n")
            check("line editing: history with up arrow",
                  run_editing(b, "7*6\n" + up + "\n"), "42\n42\n")
            check("line editing: typed keys do not reach stdout",
                  run_editing(b, "a = 2;\na+1\n"), "3\n")
        else:
            print("skipping line editing tests (built without readline)")
        # save() and transcript()
        work, trans = os.path.join(d, "work.xyz"), os.path.join(d, "work.txt")
        session = ("a = 4\nb = a*a+3;\nb\nf(x) := x^2+1\n"
                   "for (i = 1 to 2) {\n  disp(f(i))\n}\n1/0\n"
                   f'save("{work}")\ntranscript("{trans}");\n')
        out, err, code = run(b, [], session)
        check("save prints a confirmation unless ';'",
              out.splitlines()[-1], f"saved 6 statements to {work}")
        with open(work) as f:
            check("save writes the statements as typed", f.read(),
                  "a = 4\nb = a*a+3;\nb\nf(x) := x^2+1\n"
                  "for (i = 1 to 2) {\n  disp(f(i))\n}\n1/0\n")
        with open(trans) as f:
            check("transcript adds the output as comments", f.read(),
                  "a = 4\n# a = 4\nb = a*a+3;\nb\n# 19\n"
                  "f(x) := x^2+1\n# f(x) := x^2+1\n"
                  "for (i = 1 to 2) {\n  disp(f(i))\n}\n# 2\n# 5\n"
                  "1/0\n# error: line 8: division by zero\n")
        want = ("a = 4\n19\nf(x) := x^2+1\n2\n5\n",
                "error: line 8: division by zero\n", 1)
        check("a saved session replays the same", run(b, [work]), want)
        # (the comment lines shift the line numbers in error messages)
        check("a transcript replays the same", run(b, [trans]),
              (want[0], "error: line 13: division by zero\n", 1))
        check("save from -e and interactive input",
              (run(b, ["-e", "x = 1", "-e", f'save("{work}");']),
               open(work).read()), (("x = 1\n", "", 0), "x = 1\n"))
        check("save in interactive mode records what was typed",
              (run_tty(b, f'a := x+1\nif (1)\n{{ c = 2; }}\nsave("{work}");\n'),
               open(work).read()),
              ("a := x+1\n", "a := x+1\nif (1)\n{ c = 2; }\n"))
        # transcript as a LaTeX document
        tex = os.path.join(d, "work.tex")
        run(b, [], "a = 4\nf(x) := x^2/x\nfor (i = 1 to 2) { disp(i, i/2) }\n"
                   f'1/0\ntranscript("{tex}")\n')
        with open(tex) as f:
            doc = f.read()
        check("LaTeX transcript", all(part in doc for part in (
            "\\documentclass{article}", "\\begin{verbatim}\na = 4\n\\end{verbatim}",
            "\\begin{gather*}\na = 4\n\\end{gather*}",
            "f\\left(x\\right) \\mathrel{:=} \\frac{x^{2}}{x}",
            "\\begin{array}{cc}\n1 & \\frac{1}{2} \\\\\n2 & 1\n\\end{array}",
            "\\textit{error: line 4: division by zero}",
            "\\end{document}")), True)
        if shutil.which("pdflatex"):
            p = subprocess.run(["pdflatex", "-interaction=nonstopmode",
                                "-halt-on-error", "work.tex"], cwd=d,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            check("LaTeX transcript compiles with pdflatex", p.returncode, 0)
        else:
            print("skipping pdflatex check (not installed)")

        check("--trunc truncates like bc",
              run(b, ["--trunc", "-e", "disp(num(2/3, 5), num(pi, 4), num(-2/3, 3))"]),
              ("0.66666\t3.1415\t-0.666\n", "", 0))
        check("without --trunc num rounds",
              run(b, ["-e", "disp(num(2/3, 5), num(pi, 4), num(-2/3, 3))"]),
              ("0.66667\t3.1416\t-0.667\n", "", 0))

        # --show-your-work: the same math-only steps as board, inside LaTeX
        worktex = os.path.join(d, "show.tex")
        out, err, code = run(b, ["--show-your-work", "--work-file=" + worktex,
                                 "-e", "expand((x+1)^2)"])
        check("show-your-work: stdout is LaTeX",
              all(s in out for s in ("\\begin{verbatim}", "\\begin{align*}",
                                     "x^{2}+2 x+1 \\\\", "\\end{align*}"))
              and "x^2+2*x+1\n" not in out, True)
        check("show-your-work: clean stderr and exit", (err, code), ("", 0))
        check("show-your-work: no step labels", "\\text{" not in out, True)
        with open(worktex) as f:
            doc = f.read()
        check("show-your-work: complete .tex document",
              all(s in doc for s in (
                  "\\documentclass{article}", "\\usepackage{amsmath}",
                  "\\begin{verbatim}\nexpand((x+1)^2)\n\\end{verbatim}",
                  "x^{2}+2 x+1 \\\\", "\\end{document}")), True)
        out, _, _ = run(b, ["--show-your-work=top", "--work-file=" + worktex,
                            "-e", "expand((x+1)^2)"])
        check("work-level=top omits rewrites",
              ("\\left(x+1\\right) \\left(x+1\\right)" not in out and
               "x^{2}+2 x+1 \\\\" in out), True)
        out, _, _ = run(b, ["--show-your-work", "--work-file=" + worktex,
                            "-e", "diff(x^2*exp(x), x)"])
        default_out, _, _ = run(b, ["--show-your-work", "--work-level=methods",
                                    "--work-file=" + worktex,
                                    "-e", "diff(x^2*exp(x), x)"])
        check("show-your-work defaults to methods", out, default_out)
        out, _, _ = run(b, ["--show-your-work", "--work-level=methods",
                            "--work-file=" + worktex, "-e", "expand((x+1)^2)"])
        check("work-level=methods keeps intermediate products",
              ("\\left(x+1\\right)^{2} = \\left(x+1\\right) \\left(x+1\\right)" in out and
               "combine terms" not in out), True)
        out, _, _ = run(b, ["--show-your-work", "--work-level=all",
                            "--work-file=" + worktex, "-e", "diff(x^2*exp(x), x)"])
        check("work trace groups exp powers for LaTeX",
              ("{e^{x}}^{1}" in out and "e^{x}^{" not in out), True)
        out, _, _ = run(b, ["--show-your-work", "--work-level=methods",
                            "--work-file=" + worktex, "-e", "diff((x+1)^3,x)"])
        check("work trace uses a difference quotient for polynomials",
              all(s in out for s in (
                  r"\frac{\left(\left(h+x+1\right)^{3}-\left(x+1\right)^{3}\right)}{h} = h^{2}+3 h x+3 x^{2}+3 h+6 x+3",
                  r"\operatorname{limit}\left(\frac{\left(\left(h+x+1\right)^{3}-\left(x+1\right)^{3}\right)}{h}, h, 0\right) = 3 x^{2}+6 x+3",
                  r"3 x^{2}+6 x+3 \\")), True)
        # L'Hopital and differentiation are operator results: the rows must
        # not claim that a function equals its derivative or its limit.
        out, _, _ = run(b, ["--show-your-work", "--work-level=methods",
                            "--work-file=" + worktex, "-e", "limit(sin(x)/x,x=0)"])
        check("L'Hopital row shows the limit on both sides",
              all(s in out for s in (
                  r"\frac{d}{dx} \left(\sin\left(x\right)\right) = \cos\left(x\right) \\",
                  r"\frac{d}{dx} \left(x\right) = 1 \\",
                  r"\operatorname{lim}_{x \to 0} \frac{\sin\left(x\right)}{x} = "
                  r"\operatorname{lim}_{x \to 0} \cos\left(x\right) \\",
              )), True)
        check("no false equalities in limit traces",
              all(s not in out for s in (
                  r"\sin\left(x\right) = \cos\left(x\right) \\",
                  r"x = 1 \\",
                  r"\frac{\sin\left(x\right)}{x} = \cos\left(x\right) \\",
              )), True)
        # Named algorithms still expose the simpler steps they are built from.
        traces = {
            "quo(x^3-1,x-1,x)": [r"x^{2} \left(x-1\right) = x^{3}-x^{2}"],
            "sum(i^2,i=1 to n)": [r"\frac{n^{3}}{3}+\frac{n^{2}}{2}+\frac{n}{6}"],
            "cancel((x^2-1)/(x^3-1))": [r"\begin{array}{r|l}", r"\mathrm{GCD}"],
            "solve([x+y=3,x-y=1],[x,y])": [r"\left[2, 1\right]"],
            "integrate(x*exp(x),x)": [r"x e^{x} = x e^{x}-e^{x}"],
            "integrate(x*exp(x^2),x)": [r"\int x e^{x^{2}} \, dx = \frac{e^{x^{2}}}{2}"],
            "expand((x+1)^3)": [r"x^{3}+3 x^{2}+3 x+1"],
        }
        for expr, wanted in traces.items():
            out, _, _ = run(b, ["--show-your-work", "--work-level=methods",
                                "--work-file=" + worktex, "-e", expr])
            check(f"work trace steps for {expr}",
                  all(s in out for s in wanted) and "\\text{" not in out, True)
        out, _, _ = run(b, ["--show-your-work", "--work-level=methods",
                            "--work-file=" + worktex, "-e", "cancel((x^2-1)/(x-1))"])
        check("work trace shows the complete cancellation",
              all(s in out for s in (
                  r"x^{2}-1-x \left(x-1\right) &= x^{2}-1-x^{2}+x = x-1 \\",
                  r"x-1-\left(x-1\right) &= x-1-x+1 = 0 \\",
                  r"\mathrm{GCD} &= x-1 \\",
                  r"\begin{array}{r|l}",
                  r" & x+1 \\ \cline{2-2}",
                  r"x-1 & x^{2}-1 \\",
                  r" & -\left(x^{2}-x\right) \\ \cline{2-2}",
                  r" & x-1 \\",
                  r" & -\left(x-1\right) \\ \cline{2-2}",
                  r" & 0 \\",
                  r"\frac{\left(x-1\right)}{\left(x-1\right)} &= 1 \\",
                  r"\frac{\left(x^{2}-1\right)}{\left(x-1\right)} = \frac{\left(x+1\right) \left(x-1\right)}{\left(x-1\right)} = x+1 \\",
                  r"x+1 \\",
              )), True)
        check("work trace has no text headings",
              all(s not in out for s in ("Finding GCD:", "Divide out the GCD:", "Canceling:")), True)
        out, _, _ = run(b, ["--show-your-work", "--work-level=methods",
                            "--work-file=" + worktex, "-e", "factor(x^4-1)"])
        check("work trace shows how rational roots give the factors",
              all(s in out for s in (
                  r"x^{4}-1 = \left[-1, 1\right] \\",
                  r"\left[p\left(-1\right), p\left(1\right)\right] = \left[0, 0\right] \\",
                  r"p\left(-1\right) = 0 \\",
                  r"\frac{\left(x^{4}-1\right)}{\left(x+1\right)} = x^{3}-x^{2}+x-1 \\",
                  r"p\left(1\right) = 0 \\",
                  r"\frac{\left(x^{3}-x^{2}+x-1\right)}{\left(x-1\right)} = x^{2}+1 \\",
              )), True)
        check("rational roots are not printed as values of p",
              all(s not in out for s in (r"x^{4}-1 = -1", r"x^{4}-1 = 1")), True)
        out, _, _ = run(b, ["--show-your-work", "--work-level=methods",
                            "--work-file=" + worktex, "-e", "factor(x^4+x^2+1)"])
        check("work trace shows the Kronecker factor",
              all(s in out for s in (
                  r"x^{4}+x^{2}+1 = x^{2}+x+1 \\",
                  r"\frac{\left(x^{4}+x^{2}+1\right)}{\left(x^{2}+x+1\right)} = x^{2}-x+1 \\",
              )), True)
        out, _, _ = run(b, ["--show-your-work", "--work-level=methods",
                            "--work-file=" + worktex, "-e", "factor(2*x^3-3*x^2-2*x)"])
        check("work trace tries fractional root candidates",
              all(s in out for s in (
                  r"2 x^{2}-3 x-2 = \left[-2, -1, -\frac{1}{2}, \frac{1}{2}, 1, 2\right] \\",
                  r"\left[p\left(-2\right), p\left(-1\right), p\left(-\frac{1}{2}\right), p\left(\frac{1}{2}\right), p\left(1\right), p\left(2\right)\right] = \left[12, 3, 0, -3, -3, 0\right] \\",
              )), True)
        out, _, _ = run(b, ["--show-your-work", "--work-level=methods",
                            "--work-file=" + worktex, "-e", "expand((x+2)^3)"])
        check("expansion shows raw products before combining",
              all(s in out for s in (
                  r"\left(x+2\right)^{2} = \left(x+2\right) \left(x+2\right) \\",
                  r"&= x^{2}+2 x+2 x+4 \\",
                  r"&= x^{2}+4 x+4 \\",
                  r"\left(x+2\right) \left(x^{2}+4 x+4\right) = x^{3}+4 x^{2}+4 x+2 x^{2}+8 x+8 \\",
                  r"&= x^{3}+6 x^{2}+12 x+8 \\",
              )), True)
        check("work trace: repeated left sides become leading equals",
              r"\left(x+2\right) \left(x+2\right) = x^{2}+2 x+2 x+4" not in out, True)
        out, _, _ = run(b, ["--show-your-work", "--work-level=methods",
                            "--work-file=" + worktex, "-e", "sqrt(x^2+2*x+1)"])
        check("work trace shows the square-root algorithm",
              all(s in out for s in (
                  r"\operatorname{sqrt}\left(1\right) = 1 \\",
                  r"\frac{2}{2} = 1 \\",
                  r"x^{2}+2 x+1 = \left(x+1\right)^{2} \\",
                  r"\left|x+1\right| \\",
              )), True)
        out, _, _ = run(b, ["--show-your-work", "--work-file=" + worktex,
                            "-e", "1+1", "-e", "2+2"])
        check("work trace has one block per statement",
              out.count("\\begin{verbatim}"), 2)
        check("bad work level", run(b, ["--work-level=nope", "-e", "1"])[1:],
              ("abc: --work-level: must be top, methods or all\n", 2))
        check("empty work file name", run(b, ["--work-file=", "-e", "1"])[1:],
              ("abc: --work-file needs a file name\n", 2))
        out, _, _ = run(b, ["--help"])
        check("help mentions --show-your-work", "--show-your-work" in out, True)
        if shutil.which("pdflatex"):
            p = subprocess.run(["pdflatex", "-interaction=nonstopmode",
                                "-halt-on-error", "show.tex"], cwd=d,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            check("work trace compiles with pdflatex", p.returncode, 0)
            exptex = os.path.join(d, "exp.tex")
            run(b, ["--show-your-work", "--work-level=all", "--work-file=" + exptex,
                    "-e", "diff(x^2*exp(x), x)"])
            p = subprocess.run(["pdflatex", "-interaction=nonstopmode",
                                "-halt-on-error", "exp.tex"], cwd=d,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            check("exp work trace compiles with pdflatex", p.returncode, 0)
            limtex = os.path.join(d, "lim.tex")
            run(b, ["--show-your-work", "--work-file=" + limtex,
                    "-e", "limit(sin(x)/x,x=0)", "-e", "limit(ln(x)/x,x=inf)"])
            p = subprocess.run(["pdflatex", "-interaction=nonstopmode",
                                "-halt-on-error", "lim.tex"], cwd=d,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            check("limit work trace compiles with pdflatex", p.returncode, 0)
        else:
            print("skipping work-trace pdflatex check (not installed)")

        # --board-file: steps as board formulas, with only the opening
        # statement naming what is about to happen
        check("board-file to stdout",
              run(b, ["--board-file=-", "-e", "1/3+1/6"]),
              ("# written by abc --board-file\n$1/3+1/6$\n"
               "$\\frac{1}{2}$\n", "", 0))
        board_input = os.path.join(d, "steps.txt")
        before = set(os.listdir(d))
        out, err, code = run(b, ["--board-file=" + board_input,
                                 "-e", "expand((x+1)^2)"])
        check("board-file: clean stdout, stderr and exit", (out, err, code), ("", "", 0))
        check("board-file: no work document", set(os.listdir(d)) - before, {"steps.txt"})
        with open(board_input) as f:
            text = f.read()
        check("board-file: formula lines are preserved", all(s in text for s in (
            "$expand((x+1)^2)$",
            "$\\left(x+1\\right)^{2} = \\left(x+1\\right) \\left(x+1\\right)$",
            "$= x^{2}+x+x+1$",
            "$= x^{2}+2 x+1$")), True)
        out, _, _ = run(b, ["--board-file=-", "--work-level=methods",
                            "-e", "expand((x+2)^3)"])
        check("board-file: repeated left sides become leading equals",
              all(s in out for s in (
                  "$\\left(x+2\\right)^{2} = \\left(x+2\\right) \\left(x+2\\right)$",
                  "$= x^{2}+2 x+2 x+4$",
                  "$= x^{2}+4 x+4$")), True)
        groups = [g.split("\\end{rows}")[0].strip().splitlines()
                  for g in out.split("\\begin{rows}")[1:]]
        check("board-file: each chain is one rows block", len(groups), 2)
        check("board-file: a chain keeps all of its rows", groups[0], [
            "$\\left(x+2\\right)^{2} = \\left(x+2\\right) \\left(x+2\\right)$",
            "$= x^{2}+2 x+2 x+4$",
            "$= x^{2}+4 x+4$"])
        check("board-file: rows blocks are closed",
              out.count("\\begin{rows}") == out.count("\\end{rows}"), True)
        check("board-file: step labels are left out", all(s not in text for s in (
            "expand:", "result:", "power as product", "sum the terms")), True)
        lines = [line for line in text.splitlines() if line.startswith("$")]
        check("board-file: no identical neighbouring scenes",
              any(a == b for a, b in zip(lines, lines[1:])), False)
        check("board-file: no LaTeX math environments", all(e not in text for e in (
            "\\begin{align", "\\begin{array", "\\begin{verbatim}")), True)
        out, _, _ = run(b, ["--board-file=-", "--work-level=top",
                            "-e", "expand((x+1)^2)"])
        check("board-file: work-level=top omits rewrites",
              ("power as product" not in out and "$x^{2}+2 x+1$" in out), True)
        out, _, _ = run(b, ["--board-file=-", "-e", "cancel((x^2-1)/(x-1))"])
        check("board-file: array rows become formulas", all(s in out for s in (
            "$GCD = x-1$", "$x-1 : x^{2}-1$",
            "$\\frac{\\left(x^{2}-1\\right)}{\\left(x-1\\right)} = "
            "\\frac{\\left(x+1\\right) \\left(x-1\\right)}{\\left(x-1\\right)} = x+1$")), True)
        check("board-file: no text-only detail headers", all(s not in out for s in (
            "$Finding GCD:$", "$Divide out the GCD:$", "$Canceling:$")), True)
        check("empty board file name", run(b, ["--board-file=", "-e", "1"])[1:],
              ("abc: --board-file needs a file name\n", 2))
        out, _, _ = run(b, ["--help"])
        check("help mentions --board-file", "--board-file" in out, True)

        # --imag=NAME
        check("--imag=i: input and output use i",
              run(b, ["--imag=i", "-e", "disp((3+2i)*(1-i), Re(1/(x+i)), num(i/3, 3))"]),
              ("5-i\tx/(x^2+1)\t0.333*i\n", "", 0))
        check("--imag=i: im is an ordinary name",
              run(b, ["--imag", "i", "-e", "im = 5; im*2i"]), ("10*i\n", "", 0))
        check("--imag=i: i cannot be assigned",
              run(b, ["--imag=i", "-e", "i = 3"])[1],
              "error: line 1: 'i' is the imaginary unit and cannot be assigned\n")
        check("--imag needs a usable name", run(b, ["--imag=if", "-e", "1"])[1:],
              ("abc: --imag: 'if' cannot be used as a name\n", 2))
        run(b, ["--imag=i", "-e", "a = 2i;", "-e", f'save("{work}");'])
        with open(work) as f:
            check("saved files say which unit they need", f.read(),
                  f"# the imaginary unit is i: run with  abc --imag=i {work}\n"
                  "a = 2i;\n")
        check("errors go to stderr, results to stdout",
              run(b, [], "1\nfoo(1)\n2\n"),
              ("1\n2\n", "error: line 2: unknown function 'foo'\n", 1))

    # a note (once, only at a terminal) when an assumption would simplify
    out = run_tty(b, "f := x/x\nsqrt(y^2)\nabs(z)\n")
    check("assumption note once", out.count("note:"), 1)
    check("assumption note text", "x/x would be 1 with assume(x != 0)" in out, True)
    out = run_tty(b, "1+1\nsqrt(x^2)\n")
    check("assumption note for abs", "abs(x) would be x with assume(x >= 0), or -x with "
          "assume(x <= 0)" in out, True)
    out = run_tty(b, "assume(x > 0)\nsqrt(x^2)\n")
    check("no note when assumed", "note:" in out, False)
    o, e, _ = run(b, [], "sqrt(x^2)\n")
    check("no note in a pipe", "note:" in o + e, False)

    # the worked examples all produce a LaTeX work document, and both renderers
    # must show the same rows at the same level
    exroot = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")
    with tempfile.TemporaryDirectory() as exdir:
        for name in sorted(n for n in os.listdir(exroot) if n.endswith(".abc")):
            source = os.path.join(exroot, name)
            tex = os.path.join(exdir, name[:-4] + ".tex")
            board = os.path.join(exdir, name[:-4] + ".txt")
            out, err, code = run(b, ["--show-your-work", "--work-level=methods",
                                    "--work-file=" + tex, source])
            with open(tex) as f:
                has_document = "\\begin{document}" in f.read()
            check(f"example {name}", (err, code, has_document), ("", 0, True))
            _, err, code = run(b, ["--board-file=" + board, "--work-level=methods", source])
            with open(board) as f:
                board_text = f.read()
            check(f"example {name}: board input", (err, code), ("", 0))
            check(f"example {name}: renderer parity", renderer_drift(out, board_text), [])

    print(f"cli tests: {'ok' if not failures else f'{failures} FAILED'}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
