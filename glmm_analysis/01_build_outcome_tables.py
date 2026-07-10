"""
STEP 1 — Build the four per-observation outcome tables for the GLMM analysis
(Craig's meeting-16 request: separate analysis for Recall, Precision,
Token Recall, Token Precision).

Everything here reuses the SAME matching rules as the official scorer
evaluate.py, so the per-observation 1/0 outcomes aggregate back to the exact
numbers in master_comparison.xlsx.

  Mistake level (greedy 1-to-1 matching, spans intersect):
    recall_table.csv      : one row per GOLD mistake  x config -> detected 0/1
    precision_table.csv   : one row per MODEL flag     x config -> correct  0/1

  Token level (union membership, no greedy):
    token_recall_table.csv    : one row per GOLD token     x config -> covered 0/1
    token_precision_table.csv : one row per SUBMITTED token x config -> correct 0/1

Common columns: text_id, category, sentence_id, family, size, prompt, mode, <outcome>

Run from the PRACTICUM root:
    python3 glmm_analysis/01_build_outcome_tables.py
"""

import os
import re
import glob
import yaml
import pandas as pd

GSML = "data/gsml_30_rows.csv"
TOKEN_LOOKUP = "data/token_lookup.yaml"
SUB_DIR = "results/formatted/stage_abcde"
OUTDIR = "glmm_analysis/tables"

STD_CATS = {"NAME", "NUMBER", "WORD", "CONTEXT", "NOT_CHECKABLE", "OTHER"}


def parse_run(run_id):
    parts = run_id.split("_")
    family, size = parts[0], parts[1]
    mode = "sent" if "sent" in parts[2:] else "full"
    prompt = "_".join(t for t in parts[2:] if t != "sent" and not t.startswith("run"))
    return family, size, prompt, mode


def main():
    os.makedirs(OUTDIR, exist_ok=True)

    # ---- gold mistakes: spans + per-mistake metadata -------------------
    g = pd.read_csv(GSML)
    g["TID"] = g["TEXT_ID"].str.replace(".txt", "", regex=False)
    gold = {}                       # text_id -> list of mistakes
    gold_tokens = {}                # text_id -> set of all gold doc-token ids
    for _, r in g.iterrows():
        tid = r["TID"]
        ds, de = int(r["DOC_TOKEN_START"]), int(r["DOC_TOKEN_END"])
        cat = str(r["TYPE"]).upper()
        gold.setdefault(tid, []).append({
            "category": cat if cat in STD_CATS else "OTHER",
            "sentence_id": int(r["SENTENCE_ID"]),
            "set": set(range(ds, de + 1)),
        })
        gold_tokens.setdefault(tid, set()).update(range(ds, de + 1))
    n_gold = sum(len(v) for v in gold.values())
    print(f"gold mistakes: {n_gold} | games: {len(gold)}")

    with open(TOKEN_LOOKUP) as f:
        s2d = yaml.safe_load(f)["sent_to_doc"]

    def sub_spans(fp):
        """Return list of submitted annotations: dict(category, sentence_id, set)."""
        d = pd.read_csv(fp)
        out = []
        for _, r in d.iterrows():
            tid = str(r["TEXT_ID"])
            try:
                if pd.notna(r.get("DOC_TOKEN_START")) and pd.notna(r.get("DOC_TOKEN_END")):
                    ds, de = int(r["DOC_TOKEN_START"]), int(r["DOC_TOKEN_END"])
                else:
                    sid = int(r["SENTENCE_ID"])
                    ds = s2d[tid][sid][int(r["SENT_TOKEN_START"])]
                    de = s2d[tid][sid][int(r["SENT_TOKEN_END"])]
            except Exception:
                continue
            cat = str(r.get("TYPE", "")).upper()
            out.append({
                "text_id": tid,
                "category": cat if cat in STD_CATS else "OTHER",
                "sentence_id": int(r["SENTENCE_ID"]) if pd.notna(r.get("SENTENCE_ID")) else 0,
                "set": set(range(ds, de + 1)),
            })
        return out

    rec_rows, prec_rows, trec_rows, tprec_rows = [], [], [], []
    files = sorted(glob.glob(f"{SUB_DIR}/results_*_abcde.csv"))
    print(f"configs: {len(files)}")

    for fp in files:
        run_id = re.sub(r"_run\d+_abcde$", "",
                        os.path.basename(fp)[len("results_"):-len(".csv")])
        family, size, prompt, mode = parse_run(run_id)
        if not prompt:              # stray run with no prompt in name
            continue
        cfg = dict(family=family, size=size, prompt=prompt, mode=mode)

        subs = sub_spans(fp)
        subs_by_text = {}
        sub_tokens = {}             # text_id -> union of submitted doc tokens
        for i, sdat in enumerate(subs):
            t = sdat["text_id"]
            subs_by_text.setdefault(t, []).append((i, sdat))
            sub_tokens.setdefault(t, set()).update(sdat["set"])

        # ---- greedy 1-to-1 matching (recall + precision) --------------
        matched_sub_idx = set()
        for tid, mistakes in gold.items():
            avail = {i: s["set"] for i, s in subs_by_text.get(tid, [])}
            for m in mistakes:
                hit = next((k for k, s in avail.items() if s & m["set"]), None)
                if hit is not None:
                    avail.pop(hit)
                    matched_sub_idx.add((tid, hit))
                rec_rows.append({"text_id": tid, "category": m["category"],
                                 "sentence_id": m["sentence_id"], **cfg,
                                 "detected": int(hit is not None)})

        # precision: each submission -> was it matched?
        for tid, lst in subs_by_text.items():
            for i, sdat in lst:
                prec_rows.append({"text_id": tid, "category": sdat["category"],
                                  "sentence_id": sdat["sentence_id"], **cfg,
                                  "correct": int((tid, i) in matched_sub_idx)})

        # ---- token level (union membership) ---------------------------
        # token recall: each gold token -> is it in the submitted union?
        for tid, mistakes in gold.items():
            su = sub_tokens.get(tid, set())
            for m in mistakes:
                for tok in m["set"]:
                    trec_rows.append({"text_id": tid, "category": m["category"],
                                      "sentence_id": m["sentence_id"], **cfg,
                                      "covered": int(tok in su)})
        # token precision: each submitted token -> is it a gold token?
        for tid, lst in subs_by_text.items():
            gu = gold_tokens.get(tid, set())
            for i, sdat in lst:
                for tok in sdat["set"]:
                    tprec_rows.append({"text_id": tid, "category": sdat["category"],
                                       "sentence_id": sdat["sentence_id"], **cfg,
                                       "correct": int(tok in gu)})

    for name, rows in [("recall_table", rec_rows), ("precision_table", prec_rows),
                       ("token_recall_table", trec_rows),
                       ("token_precision_table", tprec_rows)]:
        df = pd.DataFrame(rows)
        df.to_csv(f"{OUTDIR}/{name}.csv", index=False)
        print(f"  {name:22} {len(df):>7} rows")

    print(f"\ntables written to {OUTDIR}/")


if __name__ == "__main__":
    main()
