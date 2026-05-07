import pandas as pd
import numpy as np
# from pathlib import Path
import os
# import sys
import boto3
from dotenv import load_dotenv

# sys.path.append(os.path.dirname(os.path.dirname(__file__)))

load_dotenv()

# ==========================================================
# ENV
# ==========================================================
S3_BUCKET = os.getenv("S3_BUCKET")
AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION")

# ==========================================================
# S3 PATH
# ==========================================================
# Decoris Clients #3 first.
#S3_INGEST_CLIENT3 = "data/1_first_bulk/adacc_act_379859374796069.csv"  # First bulk, later include Updation ingestion in Combined first bulk + updation.

# Change the pipeline to load the the Final Industry Table -> Result_Type Benchmark -> Clean.
S3_INPUT = "data/4_industry_classification/act_379859374796069_with_pages_final_industry.csv"

# Output benchmark ads (rows) only, removed the rows that are below benchmark values
S3_RESULT_BENCHMARK = "data/2_benchmark/act_379859374796069_with_pages_final_industry_benchmarked.csv"

# ==========================================================
# S3 CLIENT
# ==========================================================
s3 = boto3.client("s3", region_name=AWS_DEFAULT_REGION)

# ==========================================================
# LOAD INPUT FROM S3
# ==========================================================
obj_clients = s3.get_object(
    Bucket=S3_BUCKET,
    Key=S3_INPUT
)

df_decor3 = pd.read_csv(obj_clients["Body"])


# ==========================================================
# REQUIRED COLUMNS
# ==========================================================
cols = [
    "campaign_id",
    "campaign_name",
    "adset_id",
    "adset_name",
    "ad_id",
    "ad_name",
    "results",
    "result_type",
    "spend",
    "cost_per_results"
]

df_all = df_decor3[cols].copy()

# ==========================================================
# CLEAN RESULTS
# ==========================================================
df_all["results"] = pd.to_numeric(df_all["results"], errors="coerce")
#df_all = df_all.dropna(subset=["results"])
df_all = df_all.dropna(
    subset=["results", "result_type"]
).copy()


# ==========================================================
# FIRST DEGREE FILTER
# remove zero result ads
# ==========================================================
rows_raw = len(df_all) # Rows before First Degree

df_all = df_all[df_all["results"] != 0].copy()

rows_first = len(df_all)
rows_before = rows_first

# ==========================================================
# Second degree (Adaptive thresholds)
# From 1st degree (Discounting 0 values)-
#
# Ads > 200 : p0.90
# Ads > 50 : p0.85
# The rest : p0.65
# ==========================================================
second_degree = {}

for rt in df_all["result_type"].dropna().unique():

    d = df_all[df_all["result_type"] == rt].copy()

    if d.empty:
        continue

    # ensure numeric
    d["results"] = pd.to_numeric(d["results"], errors="coerce")
    d["cost_per_results"] = pd.to_numeric(d["cost_per_results"], errors="coerce")

    d = d.dropna(subset=["results"])
    n = len(d)

    # ---------------------------------
    # RESULTS (adaptive thresholds)
    # ---------------------------------
    if n >= 200:
        p_res = d["results"].quantile(0.90)

    elif n >= 50:
        p_res = d["results"].quantile(0.85)

    else:
        p_res = d["results"].quantile(0.65)

    # ---------------------------
    # CPR DECISION LOGIC
    # ---------------------------
    d_cpr = d.dropna(subset=["cost_per_results"])

    apply_cpr = False

    if not d_cpr.empty:
        n_cpr = len(d_cpr)

        p30 = d_cpr["cost_per_results"].quantile(0.30)
        p70 = d_cpr["cost_per_results"].quantile(0.70)
        spread = np.inf if p30 == 0 else p70 / p30

        if not (n_cpr < 30 or p30 < 1 or spread < 2):
            apply_cpr = True


    # ---------------------------
    # APPLY FILTER
    # ---------------------------
    if apply_cpr:
        p_cpr = d_cpr["cost_per_results"].quantile(0.45)

        df_top = d[
            (d["results"] >= p_res) &
            (d["cost_per_results"] <= p_cpr)
        ].copy()
    else:
        df_top = d[
            (d["results"] >= p_res)
        ].copy()

    second_degree[rt] = df_top

rows_second = sum(len(x) for x in second_degree.values())

# # ==========================================================
# # THIRD DEGREE FILTERING
# # [ Third degree ] -- Conditional only
# # After 2nd degree (Adaptive thresholds) --
# #
# # Only ads > 100 : Apply third degree percentile (p0.30)
# # ==========================================================
# third_degree = {}

# for rt, df in second_degree.items():

#     if df.empty:
#         continue

#     n = len(df)

#     if n >= 100:
#         p30 = df["results"].quantile(0.30)
#         df_top_30 = df[df["results"] >= p30].copy()
#         third_degree[rt] = df_top_30

#     else:
#         third_degree[rt] = df.copy()

# rows_third = sum(len(x) for x in third_degree.values())

# ==========================================================
# BENCHMARK TABLE
# ==========================================================
benchmarks = []

#for rt, df in third_degree.items():
for rt, df in second_degree.items():

    if df.empty:
        continue

    result_benchmark = df['results'].min()
    result_median_val = df['results'].median()
    result_max_val = df['results'].max()

    #cpr_benchmark = df['cost_per_results'].min()
    cpr_benchmark = df['cost_per_results'].dropna().min()
    cpr_median_val = df['cost_per_results'].median()
    cpr_max_val = df['cost_per_results'].max()
        
    cost_benchmark = df['spend'].min()
    cost_median_val = df['spend'].median()
    cost_max_val = df['spend'].max()

    n = len(df)

    benchmarks.append({
        'result_type': rt,
        'ads_selected': n,
        
        'result_benchmark_min_pass': result_benchmark,
        'result_median_selected': result_median_val,
        'result_max_value': result_max_val,
        
        'cpr_benchmark_min_pass': cpr_benchmark,
        'cpr_median_selected': cpr_median_val,
        'cpr_max_value': cpr_max_val,

        'cost_benchmark_min_pass': cost_benchmark,
        'cost_median_selected': cost_median_val,
        'cost_max_value': cost_max_val
    })

benchmark_df = pd.DataFrame(benchmarks)

# ==========================================================
# SORT
# ==========================================================
if not benchmark_df.empty:
    benchmark_df = benchmark_df.sort_values(
        by=["ads_selected", "result_benchmark_min_pass", "cpr_benchmark_min_pass"],
        ascending=[False, False, False]
    ).reset_index(drop=True)

# # ==========================================================
# # APPLY BENCHMARK TO COUNT FINAL PASS ROWS
# # ==========================================================
# df_pass = df_decor3.copy()

# df_pass["results"] = pd.to_numeric(df_pass["results"], errors="coerce")
# df_pass["cost_per_results"] = pd.to_numeric(df_pass["cost_per_results"], errors="coerce")

# df_pass = df_pass.merge(
#     benchmark_df[["result_type", "result_benchmark_min_pass", "cpr_benchmark_min_pass"]],
#     on="result_type",
#     how="left"
# )

# df_pass = df_pass.dropna(subset=["result_benchmark_min_pass"])
# df_pass = df_pass.dropna(subset=["cpr_benchmark_min_pass"])

# df_pass = df_pass[
#     (df_pass["results"] > 0) &
#     (df_pass["results"] >= df_pass["result_benchmark_min_pass"]) &
#     (df_pass["cost_per_results"] <= df_pass["cpr_benchmark_min_pass"])
# ].copy()

# rows_after = len(df_pass)
# rows_removed = rows_before - rows_after

# ==========================================================
# PRINT
# ==========================================================
print(
    benchmark_df[
        [
            "result_type",
            "result_benchmark_min_pass",
            "result_median_selected",
            "result_max_value",
            "cpr_benchmark_min_pass",
            "cpr_median_selected",
            "cpr_max_value",
            "ads_selected"
        ]
    ].to_string(index=False)
)




# ==========================================================
# FINAL BENCHMARK TABLE
# ==========================================================
df_final = df_decor3.copy()
df_final["results"] = pd.to_numeric(df_final["results"], errors="coerce")
df_final["cost_per_results"] = pd.to_numeric(df_final["cost_per_results"], errors="coerce")

benchmark_rows = []

for rt, df in second_degree.items():
    if df.empty:
        continue

    benchmark_rows.append({
        "result_type": rt,
        "min_result": df["results"].min(),
        "max_cpr": df["cost_per_results"].max()
    })

benchmark_map = pd.DataFrame(benchmark_rows)

df_final = df_final.merge(
    benchmark_map,
    on="result_type",
    how="left"
)

df_final = df_final[
    (df_final["results"] >= df_final["min_result"]) &
    (
        df_final["cost_per_results"].isna() |
        (df_final["cost_per_results"] <= df_final["max_cpr"])
    )
].copy()


rows_final = len(df_final)


print("Rows before First Degree :", rows_raw)
print("Rows after First Degree  :", rows_first)
print("Rows after Second Degree :", rows_second)
# print("Rows after Third Degree  :", rows_third)

print("Rows before benchmark:", rows_before)
# print("Rows after benchmark :", rows_after)  # Print the last degree
# print("Rows removed         :", rows_removed)  # Before - After degree

print("Rows after Final Benchmark :", rows_final)
print("Rows removed              :", rows_before - rows_final)

# ==========================================================
# SAVE TO S3
# ==========================================================
s3.put_object(
    Bucket=S3_BUCKET,
    Key=S3_RESULT_BENCHMARK,
    Body=df_final.to_csv(index=False).encode("utf-8"),
)

print("Uploaded:", S3_RESULT_BENCHMARK)