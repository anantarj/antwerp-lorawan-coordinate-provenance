# A finite-data bound for the stated median-centred objective

**Status:** elementary derivation added for the revision protocol. Constructed numerical tests passed; no field-level novelty or real-data causal explanation is asserted. The supplied diagnosis already derives the far-distance limit.

Let c = 10n = 47 and

\[
 a_j(g)=c\log_{10}(\|g-t_j\|+1),\quad
 L(g)=\operatorname{med}_j|r_j+a_j(g)-\operatorname{med}_h(r_h+a_h(g))|.
\]

Let \(M=\operatorname{med}_j|r_j-\operatorname{med}_h r_h|\). For finite nonempty data,

\[
 |L(g)-M|\leq \max_j a_j(g)-\min_j a_j(g)
 =c\log_{10}\frac{d_{\max}(g)+1}{d_{\min}(g)+1}.
\]

## Proof

Set q = (max a + min a)/2 and epsilon_j = a_j-q. Then max |epsilon_j| is half the range of a. Sample medians (including the average-of-middle-two convention for even n) are 1-Lipschitz under an elementwise uniform perturbation: moving each entry by at most delta moves its median by at most delta.

The common q cancels when the median is removed. Each centred residual therefore differs from the corresponding centred r_j by at most twice max |epsilon_j|, which is the range of a. Absolute value is 1-Lipschitz; applying the median again preserves that bound. This proves the expression above.

For any fixed centre t0, let B=max_j ||t_j-t0|| and g=t0+Ru, ||u||=1, R>B. Triangle inequalities give

\[
 |L(t_0+Ru)-M|\leq c\log_{10}\frac{R+B+1}{R-B+1}\longrightarrow0.
\]

## Use and limitation

The right-hand side is a computable upper bound on how much the distance variation can move this score away from the constant-RSSI median absolute deviation. It can be evaluated over a finite, fitting-only candidate domain rather than treating astronomical receiver positions as physically plausible fitted coordinates.

The bound may be loose. A small upper bound is informative about limited variation of the score relative to the constant reference; a large upper bound proves no actual discrepancy. The bound does not certify physical positions, identify every boundary failure, establish exact finite-coordinate nonidentifiability, or show that the global minimizer is at infinity. It also does not by itself validate a switching/acceptance threshold.

Constructed tests exercise 90 finite configurations of varying even/odd sizes, an asymptotic fixture, and common-RSSI-shift invariance. These are mathematical/implementation checks, not independent datasets or a new empirical result.
