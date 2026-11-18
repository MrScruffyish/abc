=== polynomial sums with symbolic upper bound
sum(k, k = 1 to n)
sum(k^2, k = 1 to n)
sum(k^3, k = 1 to n)
sum(1, k = 1 to n)
sum(3, k = 1 to n)
sum(k, k = 0 to n)
sum(k^2, k = 0 to n)
sum(1, k = 0 to n)
sum(2*k+1, k = 0 to n)
---
n^2/2+n/2
n^3/3+n^2/2+n/6
n^4/4+n^3/2+n^2/4
n
3*n
n^2/2+n/2
n^3/3+n^2/2+n/6
n+1
n^2+2*n+1

=== symbolic bounds and parameters
sum(k, k = 5 to n)
sum(i, i = a to b)
sum(a*k + b, k = 1 to n)
sum(i^2, i = m to n)
eval(sum(k, k = 1 to n), n = 10)
factor(sum(k, k = 1 to n))
---
n^2/2+n/2-10
-a^2/2+b^2/2+a/2+b/2
a*n^2/2+a*n/2+b*n
-m^3/3+n^3/3+m^2/2+n^2/2-m/6+n/6
55
n*(n+1)/2

=== definitions and non-polynomial summands
g(n) := sum(k^2, k = 1 to n)
g(3)
g(m)
sum(sin(k), k = 1 to n)
---
g(n) := sum(k^2, k=1 to n)
14
m^3/3+m^2/2+m/6
error: line 4: sum: cannot compute a symbolic sum of sin(k) in k (only polynomials in the index are supported for symbolic bounds)
