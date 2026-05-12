import pandas as pd
import os

RAW_DIR     = "LLM_results CSV"
CLEANED_DIR = "cleaned_data"

os.makedirs(CLEANED_DIR, exist_ok=True)

raw_files = [f for f in os.listdir(RAW_DIR) if f.endswith(".csv")]

if not raw_files:
    print("No CSV files found in LLM_results CSV folder.")
else:
    for filename in raw_files:
        
        base        = os.path.splitext(filename)[0]         
        cleaned_name = f"{base}_cleaned.csv"                 
        cleaned_path = os.path.join(CLEANED_DIR, cleaned_name)

        # Skip if already cleaned
        if os.path.exists(cleaned_path):
            print(f"[SKIP]  {cleaned_name} already exists.")
            continue

        print(f"\n[CLEAN] Processing: {filename}")
        raw_path = os.path.join(RAW_DIR, filename)
        df = pd.read_csv(raw_path)
        print(f"  Original: {len(df)} rows")

        # NaN drop 
        required_cols = {"DOC_TOKEN_START", "DOC_TOKEN_END"}
        present_cols  = required_cols & set(df.columns)

        if present_cols:
            df_no_nan = df.dropna(subset=list(present_cols))
        else:
            df_no_nan = df.dropna()

        print(f"  After NaN drop: {len(df_no_nan)} rows "
              f"(lost {len(df) - len(df_no_nan)})")

        
        if "DOC_TOKEN_START" in df_no_nan.columns:
            df_no_nan["DOC_TOKEN_START"] = df_no_nan["DOC_TOKEN_START"].astype(int)
        if "DOC_TOKEN_END" in df_no_nan.columns:
            df_no_nan["DOC_TOKEN_END"]   = df_no_nan["DOC_TOKEN_END"].astype(int)
        if "TYPE" in df_no_nan.columns:
            df_no_nan["TYPE"] = df_no_nan["TYPE"].str.upper().str.replace(" ", "_")

        # Overlap removal
        if {"DOC_TOKEN_START", "DOC_TOKEN_END", "TEXT_ID"}.issubset(df_no_nan.columns):
            all_kept = []
            for text_id in df_no_nan["TEXT_ID"].unique():
                group = df_no_nan[df_no_nan["TEXT_ID"] == text_id].sort_values(
                    "DOC_TOKEN_START"
                )
                used = set()
                for _, row in group.iterrows():
                    span = set(range(row["DOC_TOKEN_START"], row["DOC_TOKEN_END"] + 1))
                    if span & used:
                        continue
                    used.update(span)
                    all_kept.append(row)

            df_clean = pd.DataFrame(all_kept).reset_index(drop=True)
            print(f"  After overlap removal: {len(df_clean)} rows "
                  f"(lost {len(df_no_nan) - len(df_clean)})")
        else:
            df_clean = df_no_nan.reset_index(drop=True)
            print("  Overlap removal skipped (span columns not found).")

        df_clean.to_csv(cleaned_path, index=False)
        print(f"  Saved → {cleaned_path}")

print("\nDone — all files processed.")