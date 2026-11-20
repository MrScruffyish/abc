// Copyright (C) 2026 Gunnar Lindholm
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Optional "show your work" trace for abc. Disabled unless a command-line
// option turns it on; all rendering is LaTeX, both on stdout and in the
// .tex work file.
#pragma once

#include "expr.hpp"

#include <iosfwd>
#include <string>

namespace xyz {

namespace trace {

// What to record. Each level includes the ones below it.
//   Off     no tracing at all (the default)
//   Top     input, builtin calls and results
//   Methods the named algorithms (expand, factor, solve, integration
//           by parts, L'Hopital, ...) and their intermediate results
//   All     every expression rewrite seen by the interpreter and every
//           automatic simplification
enum class Level { Off = 0, Top = 1, Methods = 2, All = 3 };

Level level();
void setLevel(Level l);
void setStream(std::ostream& out);
void setWorkFile(std::string file);
const std::string& workFile();

// One statement at a time: begin clears the step list, end renders it to
// stdout and appends it to the document written by writeDocument().
void beginStatement(const std::string& source);
void endStatement();

// before -> after (each side is one or several expressions).
void step(Level min, const std::string& label, const Expr& before, const Expr& after);
void step(Level min, const std::string& label, const Exprs& before, const Exprs& after);
// A transform whose input was shown by the previous step: renders "= after".
void stepEquals(Level min, const std::string& label, const Expr& after);
// Pre-rendered LaTeX rows (each ending in "\\\n") to place in the align block.
void latex(Level min, const std::string& rows);
// A printed result, or a short note that has no mathematical expression.
void result(const Expr& v);
void result(const Exprs& v);
void note(Level min, const std::string& text);

// Suppresses ordinary steps while a composite value is computed; the caller
// then emits one clean step describing the whole calculation.
class Silence {
public:
	Silence();
	~Silence();
	Silence(const Silence&) = delete;
	Silence& operator=(const Silence&) = delete;

private:
	int saved_ = 0;
};

// Adds a name to the label of the steps recorded inside it, e.g.
// "integration by parts: ..." instead of just "...".
class Scope {
public:
	explicit Scope(const std::string& label);
	~Scope();
	Scope(const Scope&) = delete;
	Scope& operator=(const Scope&) = delete;

private:
	bool pushed_ = false;
};

// Writes the complete LaTeX document. Returns false if the file cannot be
// opened or written.
bool writeDocument(const std::string& file);
void reset();

} // namespace trace
} // namespace xyz
