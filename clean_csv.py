import pandas as pd

df = pd.read_csv("LLM_results CSV/results_qwen_small.csv")
print("qwen_small")
print(f"Original: {len(df)} rows")

# NaN drop
df_no_nan = df.dropna(subset=["DOC_TOKEN_START", "DOC_TOKEN_END"])
print(f"After NaN drop: {len(df_no_nan)} rows (lost {len(df) - len(df_no_nan)})")

df_no_nan["DOC_TOKEN_START"] = df_no_nan["DOC_TOKEN_START"].astype(int)
df_no_nan["DOC_TOKEN_END"] = df_no_nan["DOC_TOKEN_END"].astype(int)
df_no_nan["TYPE"] = df_no_nan["TYPE"].str.upper().str.replace(" ", "_")

# overlap removal
all_kept = []
for text_id in df_no_nan["TEXT_ID"].unique():
    group = df_no_nan[df_no_nan["TEXT_ID"] == text_id].sort_values("DOC_TOKEN_START")
    used = set()
    for _, row in group.iterrows():
        span = set(range(row["DOC_TOKEN_START"], row["DOC_TOKEN_END"] + 1))
        if span & used:
            continue
        used.update(span)
        all_kept.append(row)

df_clean = pd.DataFrame(all_kept).reset_index(drop=True)
print(f"After overlap removal: {len(df_clean)} rows (lost {len(df_no_nan) - len(df_clean)})")

df_clean.to_csv("cleaned_data/results_qwen_small_cleaned.csv", index=False)
print("Done — cleaned CSV saved.")

