=== square roots of perfect-square polynomials
sqrt(x^2+2*x+1)
sqrt(9*x^2+6*x+1)
sqrt(4*x^2+12*x+9)
sqrt(x^2-6*x+9)
sqrt(x^2+2*x*y+y^2)
sqrt(x^2*y^2+2*x*y+1)
sqrt(25*x^2-10*x*y+y^2)
sqrt((x+1)^2)
sqrt(x^4+2*x^2+1)
sqrt(4*x^4+4*x^2+1)
---
abs(x+1)
abs(3*x+1)
abs(2*x+3)
abs(x-3)
abs(x+y)
abs(x*y+1)
abs(5*x-y)
abs(x+1)
x^2+1
2*x^2+1

=== square roots of non-squares are unchanged
sqrt(x^2+1)
sqrt(x^2-y^2)
sqrt(x^2+2*x+2)
sqrt(x)
---
(x^2+1)^(1/2)
(x^2-y^2)^(1/2)
(x^2+2*x+2)^(1/2)
x^(1/2)

=== an assumption can remove the absolute value
assume(x>0); sqrt(x^2+2*x+1)
assume(x>0); sqrt(4*x^2+12*x+9)
---
x+1
2*x+3
