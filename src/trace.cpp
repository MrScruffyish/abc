// Copyright (C) 2026 Gunnar Lindholm
// SPDX-License-Identifier: GPL-3.0-or-later
//
// LaTeX work trace: see trace.hpp.
#include "trace.hpp"

#include <cctype>
#include <fstream>
#include <initializer_list>
#include <iostream>
#include <sstream>
#include <utility>

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
std::string g_boardFile;
bool g_active = false;
std::string g_source;
std::vector<Step> g_steps;
std::vector<std::string> g_scopes;
std::string g_document;
std::string g_boardDocument;
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

// Both renderers show the statement once, then only the mathematics. These
// two helpers decide which rare pieces of prose still have to be shown: a
// text-only heading in a detail block, and notes about limits or errors.
bool textHeader(const std::string& line)
{
	if (line.empty() || line.back() != ':')
		return false;
	for (char c : line)
		if (!std::isalpha(static_cast<unsigned char>(c)) && c != ' ' && c != ':')
			return false;
	return true;
}

bool keepNote(const std::string& text)
{
	return text.rfind("error", 0) == 0 ||
	       text.rfind("showing the first", 0) == 0 ||
	       text.find("omitted") != std::string::npos;
}

// Detail rows from gcd.cpp are already LaTeX. Drop their headings and turn
// the one remaining text symbol (\text{GCD}) into maths styling.
bool latexTextHeader(const std::string& line)
{
	const std::string prefix = "\\text{";
	if (line.compare(0, prefix.size(), prefix) != 0)
		return false;
	size_t end = line.find('}', prefix.size());
	return end != std::string::npos &&
	       textHeader(line.substr(prefix.size(), end - prefix.size()));
}

std::string latexRows(const std::string& rows)
{
	std::string out;
	std::istringstream in(rows);
	std::string line;
	while (std::getline(in, line)) {
		if (latexTextHeader(line))
			continue;
		for (size_t p = 0; (p = line.find("\\text{", p)) != std::string::npos; p += 8)
			line.replace(p, 6, "\\mathrm{");
		out += line + "\n";
	}
	return out;
}

// A chain reads better without repeating a side the viewer has just seen: if
// a transform starts where the previous row ended, only show "= after". The
// leading & marks the empty left-hand side as an align* column.
std::string stepLatex(const Step& s, std::string& previous)
{
	switch (s.kind) {
	case Step::Kind::Transform: {
		std::string before = exprsLatex(s.before);
		std::string after = exprsLatex(s.after);
		bool repeated = !before.empty() && before == previous;
		previous = after;
		return (repeated ? "&= " + after : before + " = " + after) + " \\\\\n";
	}
	case Step::Kind::Equals: {
		std::string after = exprsLatex(s.after);
		previous = after;
		return "&= " + after + " \\\\\n";
	}
	case Step::Kind::Result:
		previous = exprsLatex(s.after);
		return exprsLatex(s.after) + " \\\\\n";
	case Step::Kind::Note:
		return keepNote(s.text) ? "\\textit{" + latexText(s.text) + "} \\\\\n" : std::string();
	case Step::Kind::Latex:
		return latexRows(s.text);
	}
	return {};
}

// With labels gone, neighbouring rows can now be identical. Keep one.
void appendLatexRows(std::string& block, const std::string& rows)
{
	std::istringstream in(rows);
	std::string line, last;
	while (std::getline(in, line)) {
		if (!line.empty() && line == last)
			continue;
		block += line + "\n";
		last = line;
	}
}

// ---------- board output ----------
// board draws one formula per input line, using a small LaTeX subset. The
// step values are already available as expressions above, so they are turned
// into board text directly; only the LaTeX syntax they are printed with needs
// translating (see toBoard()). Step labels are left out: the statement at the
// start of each block already tells the viewer what is about to happen.

bool oneOf(const std::string& cmd, std::initializer_list<const char*> names)
{
	for (const char* n : names)
		if (cmd == n)
			return true;
	return false;
}

// What to keep from a command's brace argument.
std::string wrapperText(const std::string& cmd, const std::string& inner)
{
	if (cmd == "textbackslash")
		return " ";
	if (cmd == "overline")
		return "\\overline{" + inner + "}";
	return inner;
}

bool isWrap(const std::string& cmd)
{
	return oneOf(cmd, {"text", "textit", "texttt", "mathrm", "mathbf", "mathsf",
	                   "mathtt", "mathit", "boldsymbol", "operatorname", "emph",
	                   "mathrel", "overline", "textbackslash"});
}

bool isDropped(const std::string& cmd)
{
	return oneOf(cmd, {"begin", "end", "cline", "label", "nonumber", "noalign",
	                   "displaystyle", "textstyle"});
}

std::string plainCommand(const std::string& cmd)
{
	static const std::pair<const char*, const char*> map[] = {
		{"sin", "sin"}, {"cos", "cos"}, {"tan", "tan"}, {"asin", "asin"},
		{"acos", "acos"}, {"atan", "atan"}, {"sinh", "sinh"}, {"cosh", "cosh"},
		{"tanh", "tanh"}, {"exp", "exp"}, {"ln", "ln"}, {"log", "log"},
		{"arcsin", "arcsin"}, {"arccos", "arccos"}, {"arctan", "arctan"},
		{"ldots", "..."}, {"cdots", "..."}, {"dots", "..."},
		{"lor", "or"}, {"land", "and"}, {"lnot", "not"},
	};
	for (const auto& p : map)
		if (cmd == p.first)
			return p.second;
	return {};
}

std::string readGroup(const std::string& s, size_t& i)
{
	if (i >= s.size() || s[i] != '{')
		return {};
	size_t start = ++i, depth = 1;
	while (i < s.size() && depth) {
		if (s[i] == '{') depth++;
		else if (s[i] == '}') { if (--depth == 0) break; }
		i++;
	}
	std::string inner = s.substr(start, i - start);
	if (i < s.size())
		i++;
	return inner;
}

bool trailingAlign(const std::string& s, size_t i)
{
	size_t e = s.find('\n', i);
	if (e == std::string::npos)
		e = s.size();
	for (size_t k = i; k < e;) {
		if (std::isspace(static_cast<unsigned char>(s[k]))) { k++; continue; }
		if (s.compare(k, 2, "\\\\") == 0) { k += 2; continue; }
		return false;
	}
	return true;
}

std::string toBoard(const std::string& tex)
{
	std::string out;
	size_t i = 0;
	while (i < tex.size()) {
		char c = tex[i];
		if (c == '\\' && i + 1 < tex.size()) {
			char n = tex[i + 1];
			if (n == '\\') { out += ' '; i += 2; continue; }
			if (std::isalpha(static_cast<unsigned char>(n))) {
				size_t j = i + 1;
				while (j < tex.size() && std::isalpha(static_cast<unsigned char>(tex[j]))) j++;
				std::string cmd = tex.substr(i + 1, j - i - 1);
				i = j;
				if (isWrap(cmd)) {
					while (i < tex.size() && tex[i] == ' ') i++;
					if (i < tex.size() && tex[i] == '{')
						out += wrapperText(cmd, toBoard(readGroup(tex, i)));
					else if (cmd != "textbackslash")
						out += cmd;
				} else if (isDropped(cmd)) {
					while (i < tex.size() && tex[i] == ' ') i++;
					if (i < tex.size() && tex[i] == '{') {
						readGroup(tex, i);
						if (cmd == "begin" || cmd == "end") {
							while (i < tex.size() && tex[i] == ' ') i++;
							if (i < tex.size() && tex[i] == '{')
								readGroup(tex, i); // \begin{array}{r|l}
						}
					}
				} else {
					std::string plain = plainCommand(cmd);
					out += plain.empty() ? "\\" + cmd : plain;
				}
				continue;
			}
			// Escaped character: latexText() uses \& \_ \# \$ \% and friends.
			out += (n == '{' || n == '}' || n == '|' || n == ',' || n == ';')
			     ? std::string("\\") + n : std::string(1, n);
			i += 2;
			continue;
		}
		if (c == '&') { // align* / array column separator, but keep logical &&
			if (i + 1 < tex.size() && tex[i + 1] == '&') {
				out += "&&";
				i += 2;
				continue;
			}
			size_t j = i + 1;
			while (j < tex.size() && (tex[j] == ' ' || tex[j] == '\t')) j++;
			if (j < tex.size() && tex[j] == ':') { out += ':'; i = j + 1; continue; }
			if (j < tex.size() && tex[j] == '=') { i = j; continue; } // keep the '='
			if (trailingAlign(tex, j)) { i = j; continue; }
			out += " : ";
			i++;
			continue;
		}
		out += c;
		i++;
	}
	return out;
}

std::string trim(const std::string& s)
{
	size_t a = 0, b = s.size();
	while (a < b && std::isspace(static_cast<unsigned char>(s[a]))) a++;
	while (b > a && std::isspace(static_cast<unsigned char>(s[b - 1]))) b--;
	return s.substr(a, b - a);
}

// One converted formula line, without the board "$...$" wrapper.
std::string boardText(const std::string& line, bool dropHeaders = false)
{
	std::string clean;
	for (char ch : trim(toBoard(line)))
		if (ch != ' ' || clean.empty() || clean.back() != ' ')
			clean += ch;
	if (clean.empty() || (dropHeaders && textHeader(clean)))
		return {};
	return clean;
}

// Consecutive rows of a calculation are written as one \begin{rows} block so
// board draws them in a single scene. Standalone formulas stay one per scene.
struct BoardOut {
	std::string block;
	std::vector<std::string> rows;
	std::string previous, last;

	void flush()
	{
		if (rows.empty())
			return;
		if (rows.size() == 1) {
			block += "$" + rows.front() + "$\n";
		} else {
			block += "\\begin{rows}\n";
			for (const std::string& f : rows)
				block += "$" + f + "$\n";
			block += "\\end{rows}\n";
		}
		rows.clear();
	}

	void formula(const std::string& tex, bool dropHeaders = false)
	{
		flush();
		std::istringstream in(tex);
		std::string line;
		while (std::getline(in, line)) {
			std::string f = boardText(line, dropHeaders);
			// Without labels, two rewrites can now look identical.
			if (f.empty() || f == last)
				continue;
			block += "$" + f + "$\n";
			last = f;
		}
	}

	void row(const std::string& tex)
	{
		std::string f = boardText(tex);
		if (f.empty() || f == last)
			return;
		rows.push_back(f);
		last = f;
	}
};

// A chain reads better without repeating a side the viewer has just seen: if
// a transform starts where the previous row ended, only show "= after" and
// keep it in the same rows block as the row before it.
void boardStep(const Step& s, BoardOut& out)
{
	switch (s.kind) {
	case Step::Kind::Transform: {
		std::string before = exprsLatex(s.before);
		std::string after = exprsLatex(s.after);
		bool repeated = !before.empty() && before == out.previous;
		if (!repeated)
			out.flush();
		out.row(repeated ? "= " + after : before + " = " + after);
		out.previous = std::move(after);
		break;
	}
	case Step::Kind::Equals:
		out.row("= " + exprsLatex(s.after));
		out.previous = exprsLatex(s.after);
		break;
	case Step::Kind::Result:
		out.formula(exprsLatex(s.after));
		out.previous = exprsLatex(s.after);
		break;
	case Step::Kind::Note:
		if (keepNote(s.text))
			out.formula(s.text);
		break;
	case Step::Kind::Latex:
		out.formula(s.text, true);
		break;
	}
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

void setBoardFile(std::string file) { g_boardFile = std::move(file); }

const std::string& boardFile() { return g_boardFile; }

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
	if (!g_boardFile.empty()) {
		// The statement is its own scene; each chained calculation is one
		// rows block, with standalone results and detail rows in between.
		BoardOut out;
		out.formula(g_source);
		for (const Step& s : g_steps)
			boardStep(s, out);
		out.flush();
		g_boardDocument += out.block;
	} else {
		std::string block = "\n\\begin{verbatim}\n" + g_source +
		                    (g_source.empty() || g_source.back() == '\n' ? "" : "\n") +
		                    "\\end{verbatim}\n";
		if (!g_steps.empty()) {
			block += "\\begin{align*}\n";
			std::string rows, previous;
			for (const Step& s : g_steps)
				rows += stepLatex(s, previous);
			appendLatexRows(block, rows);
			block += "\\end{align*}\n";
		}
		g_document += block;
		if (g_out) {
			*g_out << block;
			g_out->flush();
		}
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

bool writeBoardFile(const std::string& file)
{
	if (file == "-") {
		std::cout << "# written by abc --board-file\n" << g_boardDocument;
		std::cout.flush();
		return static_cast<bool>(std::cout);
	}
	std::ofstream f(file);
	if (!f)
		return false;
	f << "# written by abc --board-file; render with:\n"
	     "# board FILE.mp4 --auto-speed 0 --max-scene-seconds 0\n"
	  << g_boardDocument;
	f.close();
	return static_cast<bool>(f);
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
	g_boardDocument.clear();
	g_total = 0;
	g_truncated = false;
	g_budgetUsed = false;
}

} // namespace trace
} // namespace xyz
