// Copyright (C) 2026 Gunnar Lindholm
// SPDX-License-Identifier: GPL-3.0-or-later
//
// LaTeX work trace: see trace.hpp.
#include "trace.hpp"

#include <fstream>
#include <iostream>

namespace xyz {
namespace trace {

namespace {

constexpr size_t kMaxStepsPerStatement = 400;
constexpr size_t kMaxStepsTotal = 8000;

struct Step {
	enum class Kind { Transform, Equals, Result, Note, Latex } kind = Kind::Transform;
	std::string label;
	Exprs before, after;
	std::string text;
};

Level g_level = Level::Off;
std::ostream* g_out = &std::cout;
std::string g_workFile = "work.tex";
bool g_active = false;
std::string g_source;
std::vector<Step> g_steps;
std::vector<std::string> g_scopes;
std::string g_document;
size_t g_total = 0;
bool g_truncated = false;
bool g_budgetUsed = false;
int g_silent = 0;

bool sameExprs(const Exprs& a, const Exprs& b)
{
	if (a.size() != b.size())
		return false;
	for (size_t i = 0; i < a.size(); i++)
		if (!equal(a[i], b[i]))
			return false;
	return true;
}

std::string scopedLabel(const std::string& label)
{
	if (g_scopes.empty())
		return label;
	return g_scopes.back() + ": " + label;
}

std::string exprsLatex(const Exprs& v)
{
	std::string s;
	for (size_t i = 0; i < v.size(); i++)
		s += (i ? ", " : "") + toLatex(v[i]);
	return s;
}

std::string stepLatex(const Step& s)
{
	switch (s.kind) {
	case Step::Kind::Transform:
		return "\\text{" + latexText(s.label) + "} &: " + exprsLatex(s.before) +
		       " = " + exprsLatex(s.after) + " \\\\\n";
	case Step::Kind::Equals:
		return "\\text{" + latexText(s.label) + "} &: = " +
		       exprsLatex(s.after) + " \\\\\n";
	case Step::Kind::Result:
		return "\\text{" + latexText(s.label) + "} &: " + exprsLatex(s.after) + " \\\\\n";
	case Step::Kind::Note:
		return "\\textit{" + latexText(s.text) + "} \\\\\n";
	case Step::Kind::Latex:
		return s.text; // already complete align rows
	}
	return {};
}

void add(Step s)
{
	if (!g_active || g_level == Level::Off || g_silent > 0)
		return;
	if (g_steps.size() >= kMaxStepsPerStatement || g_total >= kMaxStepsTotal) {
		if (!g_truncated) {
			g_truncated = true;
			g_budgetUsed = true;
			Step note;
			note.kind = Step::Kind::Note;
			note.text = "further steps omitted (trace limit reached)";
			g_steps.push_back(note);
			g_total++;
		}
		return;
	}
	g_steps.push_back(std::move(s));
	g_total++;
}

} // namespace

Level level() { return g_level; }

void setLevel(Level l)
{
	g_level = l;
	if (l == Level::Off)
		g_scopes.clear();
}

void setStream(std::ostream& out) { g_out = &out; }

void setWorkFile(std::string file) { g_workFile = std::move(file); }

const std::string& workFile() { return g_workFile; }

void beginStatement(const std::string& source)
{
	if (g_level == Level::Off)
		return;
	g_active = true;
	g_source = source;
	g_steps.clear();
	g_scopes.clear();
	g_truncated = false;
}

void endStatement()
{
	if (!g_active)
		return;
	g_active = false;
	std::string block = "\n\\begin{verbatim}\n" + g_source +
	                    (g_source.empty() || g_source.back() == '\n' ? "" : "\n") +
	                    "\\end{verbatim}\n";
	if (!g_steps.empty()) {
		block += "\\begin{align*}\n";
		for (const Step& s : g_steps)
			block += stepLatex(s);
		block += "\\end{align*}\n";
	}
	g_document += block;
	if (g_out) {
		*g_out << block;
		g_out->flush();
	}
	g_steps.clear();
	g_source.clear();
	g_scopes.clear();
}

void step(Level min, const std::string& label, const Expr& before, const Expr& after)
{
	step(min, label, Exprs{before}, Exprs{after});
}

void step(Level min, const std::string& label, const Exprs& before, const Exprs& after)
{
	if (g_level < min || !g_active)
		return;
	if (sameExprs(before, after) || exprsLatex(before) == exprsLatex(after))
		return; // a no-op is not a step worth showing
	Step s;
	s.kind = Step::Kind::Transform;
	s.label = scopedLabel(label);
	s.before = before;
	s.after = after;
	add(std::move(s));
}

void stepEquals(Level min, const std::string& label, const Expr& after)
{
	if (g_level < min || !g_active)
		return;
	Step s;
	s.kind = Step::Kind::Equals;
	s.label = scopedLabel(label);
	s.after = {after};
	add(std::move(s));
}

void latex(Level min, const std::string& rows)
{
	if (g_level < min || !g_active || rows.empty())
		return;
	Step s;
	s.kind = Step::Kind::Latex;
	s.text = rows;
	add(std::move(s));
}

Silence::Silence() : saved_(g_silent) { ++g_silent; }
Silence::~Silence() { g_silent = saved_; }

void result(const Expr& v) { result(Exprs{v}); }

void result(const Exprs& v)
{
	if (g_level < Level::Top || !g_active || v.empty())
		return;
	Step s;
	s.kind = Step::Kind::Result;
	s.label = scopedLabel("result");
	s.after = v;
	add(std::move(s));
}

void note(Level min, const std::string& text)
{
	if (g_level < min || !g_active)
		return;
	Step s;
	s.kind = Step::Kind::Note;
	s.text = text;
	add(std::move(s));
}

Scope::Scope(const std::string& label)
{
	if (g_level != Level::Off && g_active) {
		g_scopes.push_back(label);
		pushed_ = true;
	}
}

Scope::~Scope()
{
	if (pushed_ && !g_scopes.empty())
		g_scopes.pop_back();
}

bool writeDocument(const std::string& file)
{
	const std::string& path = file.empty() ? g_workFile : file;
	std::ofstream f(path);
	if (!f)
		return false;
	f << "% written by abc --show-your-work\n"
	     "\\documentclass{article}\n"
	     "\\usepackage{amsmath}\n"
	     "\\begin{document}\n";
	if (g_document.empty())
		f << "\n\\textit{No steps were recorded.}\\par\n";
	else
		f << g_document;
	if (g_budgetUsed)
		f << "\n\\textit{Some steps were omitted because the trace limit was reached.}\\par\n";
	f << "\n\\end{document}\n";
	f.close();
	return static_cast<bool>(f);
}

void reset()
{
	g_active = false;
	g_source.clear();
	g_steps.clear();
	g_scopes.clear();
	g_document.clear();
	g_total = 0;
	g_truncated = false;
	g_budgetUsed = false;
}

} // namespace trace
} // namespace xyz
