"""
STEP 2 — Fit a GLMM (mixed-effects logistic regression) for each of the four
outcomes, following the UCLA tutorial / Craig's request.

For each outcome (Recall, Precision, Token Recall, Token Precision):
  outcome ~ family + size + prompt + mode + category + sent_pos
            + (1 | text_id)          # random intercept per game

Two fits per outcome:
  - Mixed model  : statsmodels BinomialBayesMixedGLM (variational Bayes;
                   the Python analogue of R's glmer).
  - Sanity check : plain logistic with cluster-robust SE by game (p-values).

Outputs (glmm_analysis/results/):
  <outcome>_glmm.csv         per-outcome coefficient table (OR + p-value + sig)
  GLMM_SUMMARY.md            all four, side by side, paper-ready
  sanity_check.csv           per-config predicted rate vs scorer number

Run from the PRACTICUM root:
    python3 glmm_analysis/02_run_glmm.py
"""

import warnings
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from statsmodels.genmod.bayes_mixed_glm import BinomialBayesMixedGLM
warnings.filterwarnings("ignore")

TBL = "glmm_analysis/tables"
OUT = "glmm_analysis/results"

# (nice name, file, outcome column)
OUTCOMES = [
    ("Recall",          "recall_table",          "detected"),
    ("Precision",       "precision_table",       "correct"),
    ("Token Recall",    "token_recall_table",    "covered"),
    ("Token Precision", "token_precision_table", "correct"),
]

PROMPT_ORDER = ["p0", "p0a", "p0b", "p0c", "p0d", "p1", "p2", "p3", "p4"]


def prep(df):
    df = df[df["prompt"].notna() & (df["prompt"].astype(str) != "")].copy()
    df = df[df["size"] != "14b"].copy()          # exclude 14B from the analysis
    df["family"] = pd.Categorical(df["family"], ["llama", "qwen"])
    sizes = [s for s in ["small", "14b", "medium"] if s in set(df["size"])]
    df["size"] = pd.Categorical(df["size"], sizes)
    prompts = [p for p in PROMPT_ORDER if p in set(df["prompt"])]
    df["prompt"] = pd.Categorical(df["prompt"], prompts)
    df["mode"] = pd.Categorical(df["mode"], ["full", "sent"])
    cats = ["NAME"] + sorted(c for c in df["category"].unique() if c != "NAME")
    df["category"] = pd.Categorical(df["category"], cats)
    sd = df["sentence_id"].std()
    df["sent_pos"] = (df["sentence_id"] - df["sentence_id"].mean()) / (sd if sd else 1)
    return df


def fit_one(name, df, y):
    df = df.rename(columns={y: "y"})
    formula = "y ~ family + size + prompt + mode + category + sent_pos"

    # cluster-robust logistic (fast, gives p-values)
    log = smf.logit(formula, df).fit(disp=0, cov_type="cluster",
                                     cov_kwds={"groups": df["text_id"]})
    tab = pd.DataFrame({"odds_ratio": np.exp(log.params).round(3),
                        "p_value": log.pvalues.round(4)})
    tab["sig"] = np.where(tab.p_value < .001, "***",
                 np.where(tab.p_value < .01, "**",
                 np.where(tab.p_value < .05, "*", "")))

    # mixed model (random intercept per game) — OR to cross-check
    try:
        mm = BinomialBayesMixedGLM.from_formula(
            formula, {"game": "0 + C(text_id)"}, df).fit_vb()
        mm_or = pd.Series(np.exp(mm.fe_mean), index=log.params.index).round(3)
        tab["mixed_OR"] = mm_or
        ranef_sd = float(np.exp(mm.vcp_mean)[0])
    except Exception as e:
        tab["mixed_OR"] = np.nan
        ranef_sd = float("nan")
        print(f"    (mixed model skipped for {name}: {e})")

    tab.index.name = "term"
    tab.to_csv(f"{OUT}/{name.lower().replace(' ', '_')}_glmm.csv")
    return tab, ranef_sd, df["y"].mean()


def main():
    import os
    os.makedirs(OUT, exist_ok=True)
    results = {}
    for name, fname, ycol in OUTCOMES:
        print(f"\n=== {name} ===")
        df = prep(pd.read_csv(f"{TBL}/{fname}.csv"))
        print(f"  rows={len(df)}  base rate={df[ycol].mean():.3f}")
        tab, sd, base = fit_one(name, df, ycol)
        results[name] = (tab, sd, base)
        print(tab[["odds_ratio", "p_value", "sig"]].to_string())

    # ---- combined paper-ready markdown -------------------------------
    with open(f"{OUT}/GLMM_SUMMARY.md", "w") as fh:
        fh.write("# GLMM Analysis — Which dimensions drive performance?\n\n")
        fh.write("Mixed-effects logistic regression (random intercept per game). "
                 "Odds ratios from cluster-robust logistic; `mixed_OR` from the "
                 "Bayesian mixed model cross-checks them. Baseline config = "
                 "**Llama / small / P0 / full / NAME error**. "
                 "OR > 1 helps, OR < 1 hurts. Sig: \\*\\*\\* p<.001, \\*\\* p<.01, \\* p<.05.\n\n")
        for name, (tab, sd, base) in results.items():
            fh.write(f"## {name}  (base rate {base:.3f}, game-SD {sd:.3f})\n\n")
            t = tab.reset_index()
            fh.write("| term | odds ratio | mixed OR | p | sig |\n|---|---|---|---|---|\n")
            for _, r in t.iterrows():
                fh.write(f"| {r['term']} | {r['odds_ratio']} | {r.get('mixed_OR','')} "
                         f"| {r['p_value']} | {r['sig']} |\n")
            fh.write("\n")
    print(f"\nsaved -> {OUT}/GLMM_SUMMARY.md and per-outcome CSVs")


if __name__ == "__main__":
    main()
