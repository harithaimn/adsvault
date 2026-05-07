# core/_04.1_industry_classification.py
# Map page_industry_master.csv into Decoris Client #3 merged ads table

import os
import pandas as pd
import boto3
from dotenv import load_dotenv

load_dotenv()

# ==========================================================
# ENV
# ==========================================================
S3_BUCKET = os.getenv("S3_BUCKET")
AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION")

# ==========================================================
# INPUT
# ==========================================================
S3_ADS = "data/3_page_mapping/act_379859374796069_with_pages.csv"
S3_MASTER = "data/4_industry_classification/page_industry_master.csv"

# ==========================================================
# OUTPUT
# ==========================================================
S3_OUTPUT = "data/4_industry_classification/act_379859374796069_with_pages_industry.csv"

# ==========================================================
# S3 CLIENT
# ==========================================================
s3 = boto3.client(
    "s3",
    region_name=AWS_DEFAULT_REGION
)

# ==========================================================
# LOAD
# ==========================================================
obj_ads = s3.get_object(Bucket=S3_BUCKET, Key=S3_ADS)
obj_master = s3.get_object(Bucket=S3_BUCKET, Key=S3_MASTER)

df_ads = pd.read_csv(
    obj_ads["Body"],
    dtype={"page_id": "string"}
)

df_master = pd.read_csv(
    obj_master["Body"],
    dtype={"page_id": "string"}
)
# ==========================================================
# CLEAN TYPES
# ==========================================================
def clean_page_id(series):
    return (
        series.astype("string")
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
        .replace({"nan": pd.NA, "<NA>": pd.NA, "None": pd.NA})
    )

df_ads["page_id"] = clean_page_id(df_ads["page_id"])
df_master["page_id"] = clean_page_id(df_master["page_id"])

print(df_master.columns.tolist())
print(df_master.head())

# ==========================================================
# MASTER KEEP ONLY NEEDED COLS
# ==========================================================
keep_cols = [
    "page_id",
    "predicted_industry",
    "score"
]

keep_cols = [c for c in keep_cols if c in df_master.columns]

df_master = (
    df_master[keep_cols]
    .drop_duplicates(subset=["page_id"])
)

# ==========================================================
# MERGE
# ==========================================================
df = df_ads.merge(
    df_master,
    on="page_id",
    how="left"
)

# ==========================================================
# FLAGS
# ==========================================================
df["industry_source"] = df["predicted_industry"].notna().map(
    {True: "page_master", False: None}
)

# ==========================================================
# SAVE
# ==========================================================
csv_bytes = df.to_csv(index=False).encode("utf-8")

s3.put_object(
    Bucket=S3_BUCKET,
    Key=S3_OUTPUT,
    Body=csv_bytes
)

# ==========================================================
# LOG
# ==========================================================
mapped = df["predicted_industry"].notna().sum()
unmapped = df["predicted_industry"].isna().sum()

print("Rows:", len(df))
print("Mapped industry:", mapped)
print("Unmapped industry:", unmapped)
print("Uploaded:", S3_OUTPUT)