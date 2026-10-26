"""
Extracts the J.P. Morgan 2026 Long-Term Capital Market Assumptions into
data/processed/dataset.json for the mean-variance dashboard.

Source layout (sheet "2026"):
  col A  group header (FIXED INCOME / EQUITIES / ALTERNATIVES), sparse
  col B  asset name
  col C  compound return, 2025 vintage (%)
  col D  arithmetic return, 2026 vintage (%)
  col E  annualized volatility (%)
  col F  compound return, 2026 vintage (%)
  col G onward  correlation matrix, one column per asset in row order

The workbook itself is not in this repo; download it from J.P. Morgan and save
it at the SRC path below. data/processed/dataset.json is checked in, so the
site builds without it.

Run: python3 scripts/build_data.py
"""
import json
import math
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "raw" / "JP Morgan 2026 Capital Market Assumptions.xlsx"
OUT = ROOT / "data" / "processed" / "dataset.json"

SHEET = "2026"
FIRST_ROW = 9
CORR_FIRST_COL = 7  # column G

# Pre-checked teaching universe: one broad, non-overlapping proxy per major
# risk bucket, close to the opportunity set in the Idzorek paper.
PRESETS = {
    "teaching": {
        "label": "Teaching 10",
        "note": "Broad, roughly non-overlapping classes. The default.",
        "assets": [
            "U.S. Cash",
            "U.S. Intermediate Treasuries",
            "U.S. Aggregate Bonds",
            "U.S. High Yield Bonds",
            "U.S. Large Cap",
            "U.S. Small Cap",
            "EAFE Equity",
            "Emerging Markets Equity",
            "U.S. REITs",
            "Commodities",
        ],
    },
    "idzorek": {
        "label": "Idzorek-style 9",
        "note": (
            "Closest J.P. Morgan match to Idzorek's nine-class opportunity set. "
            "The value and size factors overlap U.S. Large Cap, which is exactly "
            "the near-duplicate-asset setup that makes MVO pick corners."
        ),
        "assets": [
            "U.S. Large Cap",
            "U.S. Equity\xa0Value Factor",
            "U.S. Mid Cap",
            "U.S. Small Cap",
            "EAFE Equity",
            "U.S. Aggregate Bonds",
            "World ex-U.S. Government Bonds",
            "Commodities",
            "U.S. Cash",
        ],
    },
    "broad": {
        "label": "JPM broad 16",
        "note": "Wider menu spanning all three groups, including private assets.",
        "assets": [
            "U.S. Cash",
            "U.S. Intermediate Treasuries",
            "U.S. Long Treasuries",
            "TIPS",
            "U.S. Aggregate Bonds",
            "U.S. High Yield Bonds",
            "Emerging Markets Sovereign Debt",
            "U.S. Large Cap",
            "U.S. Small Cap",
            "EAFE Equity",
            "Emerging Markets Equity",
            "U.S. Core Real Estate",
            "Global Core Infrastructure",
            "Commodities",
            "Gold",
            "Private Equity",
        ],
    },
    "all": {
        "label": "All 58",
        "note": "Every investable J.P. Morgan class. The covariance matrix is badly conditioned here.",
        "assets": None,  # filled in below
    },
}

# Not an investable asset class; kept for reference only.
NON_INVESTABLE = {"U.S. Inflation"}


def main():
    wb = openpyxl.load_workbook(SRC, data_only=True)
    ws = wb[SHEET]

    assets = []
    group = None
    row = FIRST_ROW
    while True:
        name = ws.cell(row, 2).value
        if name is None:
            break
        if ws.cell(row, 1).value:
            group = str(ws.cell(row, 1).value).title()
        assets.append(
            {
                "row": row,
                "name": str(name).replace("\xa0", " ").strip(),
                "group": group,
                "compound2025": ws.cell(row, 3).value,
                "arith2026": ws.cell(row, 4).value,
                "vol": ws.cell(row, 5).value,
                "compound2026": ws.cell(row, 6).value,
                "investable": str(name).replace("\xa0", " ").strip() not in NON_INVESTABLE,
            }
        )
        row += 1

    n = len(assets)

    # Correlation matrix: lower triangle is populated, mirror it and clean up
    # floating-point noise on the diagonal.
    corr = [[None] * n for _ in range(n)]
    for i, a in enumerate(assets):
        for j in range(n):
            v = ws.cell(a["row"], CORR_FIRST_COL + j).value
            if v is not None:
                corr[i][j] = float(v)
    for i in range(n):
        corr[i][i] = 1.0
        for j in range(i):
            if corr[i][j] is None:
                corr[i][j] = corr[j][i]
            if corr[j][i] is None:
                corr[j][i] = corr[i][j]
            if corr[i][j] is None:
                raise ValueError(f"missing correlation for {assets[i]['name']} / {assets[j]['name']}")
            # The sheet stores the lower triangle; force exact symmetry.
            corr[j][i] = corr[i][j]
    for i in range(n):
        for j in range(n):
            corr[i][j] = round(max(-1.0, min(1.0, corr[i][j])), 6)

    # Verify the header row names line up with the row labels.
    for j, a in enumerate(assets):
        hdr = ws.cell(5, CORR_FIRST_COL + j).value
        hdr = str(hdr).replace("\xa0", " ").strip()
        if hdr != a["name"]:
            raise ValueError(f"column {j} header {hdr!r} != row label {a['name']!r}")

    names = [a["name"] for a in assets]
    investable = [a["name"] for a in assets if a["investable"]]
    PRESETS["all"]["assets"] = investable

    for key, p in PRESETS.items():
        missing = [x.replace("\xa0", " ") for x in p["assets"] if x.replace("\xa0", " ") not in names]
        if missing:
            raise ValueError(f"preset {key} references unknown assets: {missing}")
        p["assets"] = [x.replace("\xa0", " ") for x in p["assets"]]

    for a in assets:
        del a["row"]
        for k in ("compound2025", "arith2026", "vol", "compound2026"):
            a[k] = round(float(a[k]), 4)

    # Smallest eigenvalue of the full investable correlation matrix, reported in
    # the sources note as evidence the matrix is near-singular.
    idx = [i for i, a in enumerate(assets) if a["investable"]]
    sub = [[corr[i][j] for j in idx] for i in idx]
    eig_min = smallest_eigenvalue(sub)

    data = {
        "meta": {
            "source": "J.P. Morgan Asset Management, 2026 Long-Term Capital Market Assumptions (USD), 30th edition",
            "sheet": SHEET,
            "nAssets": n,
            "nInvestable": len(investable),
            "corrMinEigenvalue": round(eig_min, 6),
            "riskFreeAsset": "U.S. Cash",
            "returnBases": {
                "arith2026": "Arithmetic return, 2026 edition",
                "compound2026": "Compound return, 2026 edition",
                "compound2025": "Compound return, 2025 edition",
            },
        },
        "assets": assets,
        "corr": corr,
        "presets": PRESETS,
    }

    OUT.write_text(json.dumps(data, separators=(",", ":")))
    print(f"Wrote {OUT} ({OUT.stat().st_size / 1024:.0f} KB)")
    print(f"{n} assets ({len(investable)} investable), {n}x{n} correlation matrix")
    print(f"smallest eigenvalue of the {len(investable)}-asset correlation matrix: {eig_min:.4f}")


def smallest_eigenvalue(a, iters=4000):
    """Inverse power iteration on a symmetric positive-ish matrix."""
    n = len(a)
    # Shift so the matrix is positive definite, then find the largest
    # eigenvalue of (cI - A) and undo the shift.
    c = max(sum(abs(v) for v in row) for row in a)
    b = [[(c if i == j else 0.0) - a[i][j] for j in range(n)] for i in range(n)]
    v = [1.0 / math.sqrt(n)] * n
    lam = 0.0
    for _ in range(iters):
        w = [sum(b[i][j] * v[j] for j in range(n)) for i in range(n)]
        nrm = math.sqrt(sum(x * x for x in w))
        if nrm == 0:
            break
        v = [x / nrm for x in w]
        lam = nrm
    return c - lam


if __name__ == "__main__":
    main()
