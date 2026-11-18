// Copyright (C) 2026 Gunnar Lindholm
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Finite symbolic summation for polynomial summands.
// Uses Faulhaber's formula: sum_{k=1}^{n} k^p expressed as a polynomial in n.
#include "expr.hpp"

#include <map>
#include <vector>

namespace xyz {

namespace {

Rational binom(long n, long k)
{
	if (k < 0 || k > n)
		return Rational(0);
	if (k > n - k)
		k = n - k;
	Rational r(1);
	for (long i = 1; i <= k; i++)
		r = r * Rational(n - i + 1) / Rational(i);
	return r;
}

// Bernoulli numbers B_0..B_m with B_1 = -1/2
std::vector<Rational> bernoulli(long m)
{
	std::vector<Rational> B(static_cast<size_t>(m) + 1, Rational(0));
	B[0] = Rational(1);
	for (long n = 1; n <= m; n++) {
		Rational s(0);
		for (long k = 0; k < n; k++)
			s = s + binom(n + 1, k) * B[static_cast<size_t>(k)];
		B[static_cast<size_t>(n)] = -s / Rational(n + 1);
	}
	return B;
}

// sum_{k=1}^{N} k^p as an expression in N, for integer p >= 0
Expr powerSum(long p, const Expr& N)
{
	if (p == 0)
		return N;
	auto B = bernoulli(p);
	B[1] = -B[1]; // B^*_1 = +1/2
	Exprs terms;
	for (long j = 0; j <= p; j++) {
		Rational c = binom(p + 1, j) * B[static_cast<size_t>(j)] / Rational(p + 1);
		if (c.isZero())
			continue;
		long e = p + 1 - j;
		Expr term = mkNum(c);
		if (e == 1)
			term = mul(term, N);
		else if (e != 0)
			term = mul(term, simpPow(N, mkInt(e)));
		terms.push_back(term);
	}
	return simpAdd(terms);
}

} // namespace

Expr symbolicSum(const Expr& f, const std::string& var, const Expr& from, const Expr& to)
{
	std::map<long, Expr> cm;
	try {
		cm = polyCoefficients(f, var);
	} catch (const Error&) {
		throw Error("sum: cannot compute a symbolic sum of " + toString(f) + " in " + var +
		            " (only polynomials in the index are supported for symbolic bounds)");
	}

	Expr count = expand(sub(add(to, mkInt(1)), from)); // to - from + 1
	Expr from1 = expand(sub(from, mkInt(1)));
	Exprs parts;
	for (const auto& [p, coeff] : cm) {
		if (p == 0) {
			parts.push_back(mul(coeff, count));
		} else {
			Expr diff = expand(sub(powerSum(p, to), powerSum(p, from1)));
			parts.push_back(mul(coeff, diff));
		}
	}
	if (parts.empty())
		return mkInt(0);
	return expand(simpAdd(parts));
}

} // namespace xyz
