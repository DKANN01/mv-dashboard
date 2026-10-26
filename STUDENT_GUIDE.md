# Mean-Variance Optimization: Student Guide

Live site: https://dkann01.github.io/mv-dashboard/

The dashboard is built around one lesson: **mean-variance optimization is an estimation-error maximizer.** It takes J.P. Morgan's published 2026 Long-Term Capital Market Assumptions — real, carefully produced forecasts — and shows the optimizer concentrating the portfolio in whichever classes happen to carry the most favorable forecast error.

Each tab answers one question and maps to the Revisiting Asset Allocation lecture and the Idzorek paper.

## Defaults and conventions

Unless you change them: arithmetic returns from the 2026 edition, long-only weights, and the Teaching 10 universe (one broad, roughly non-overlapping proxy per risk bucket). Returns and volatilities are annualized percentages taken directly from the J.P. Morgan file; the covariance matrix is built from their published volatilities and 59×59 correlation matrix. U.S. Cash is the risk-free rate.

- **Expected return input**: switch between arithmetic 2026, compound 2026, and compound 2025. Nothing else changes — only the return vector.
- **Weight constraints**: long only, shorting allowed to a chosen bound, or long only with a per-asset cap.
- **Universe presets**: Teaching 10, Idzorek-style 9, JPM broad 16, All 58. Or open the asset picker and build your own.
- **Target volatility** sliders pick one portfolio off the frontier for the tables below them.

## Tabs

| Tab | Question it answers | Lecture topic |
|---|---|---|
| **Frontier & Allocations** | What does the optimizer actually hold at each risk level? The frontier plots every optimal portfolio against the individual asset classes; the area graph below is Idzorek's efficient-frontier asset allocation graph, where band thickness is a weight. | Markowitz setup; corner portfolios |
| **Estimation Error** | Which input is the optimizer most sensitive to? Shock any forecast by hand and watch the weights move, then run the Chopra–Ziemba experiment that perturbs returns, volatilities and correlations separately by one standard error's worth of noise. | Chopra & Ziemba (1993): returns ≈ 11× variances ≈ 22× covariances |
| **Robust Fixes** | What do practitioners do about it? Black-Litterman reverse optimization with confidence-weighted views, resampled (Michaud) MVO, risk parity, and minimum variance, all compared at the same risk level. | Idzorek Figures 5–16; Michaud's "Markowitz optimization enigma" |

## Things to try

1. **Frontier tab, Teaching 10, long only.** Read the right-hand edge of the area graph: the highest-return portfolio is 100% in one asset class. Now look at the scorecard — the average frontier portfolio holds about 3 of 10 classes. U.S. Large Cap, U.S. Small Cap and EAFE Equity are excluded at almost every risk level, not because they are bad assets but because U.S. REITs carries the highest Sharpe ratio in the set.
2. **Tick "Overlay the frontier from the 2025-edition assumptions."** Same volatilities, same correlations, one year of revisions to the return forecasts. The allocations are completely different. No investor would have held either.
3. **Switch the universe to Idzorek-style 9.** It puts the U.S. value factor next to U.S. Large Cap — near-duplicate assets. Watch the corner portfolios multiply.
4. **Switch to All 58.** The smallest eigenvalue of the correlation matrix tile drops to 0.0042. A near-singular matrix means Σ⁻¹ amplifies noise, which is why the weights swing so violently.
5. **Estimation Error tab.** Give U.S. Large Cap a +1 standard error shock — that is roughly +4.7% a year at T = 20, well inside what you could not reject. Watch the allocation flip.
6. **Robust tab.** With no views, Black-Litterman returns the equilibrium implied by your reference portfolio, so the optimizer reproduces the reference portfolio. Add one view at 50% confidence and watch only the classes correlated with it move. Then compare the six methods in the cross-section table at the bottom: traditional MVO holds 6 of 10 classes, Black-Litterman holds all 10.

## Data

J.P. Morgan Asset Management, *2026 Long-Term Capital Market Assumptions* (USD), 30th edition. 59 asset classes (58 investable; U.S. Inflation is reference only) with arithmetic and compound return forecasts, annualized volatilities, and the full correlation matrix. See the Sources section at the bottom of the page for the method notes.

## Building

```
python3 scripts/build_data.py   # xlsx -> data/processed/dataset.json
python3 scripts/build_site.py   # site/template.html + dataset -> index.html
```

`index.html` is standalone with no dependencies, ready for GitHub Pages.
