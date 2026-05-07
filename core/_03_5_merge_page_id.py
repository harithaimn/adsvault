# _03.5_merge_client3_with_pages.py

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
# INPUT S3
# ==========================================================
S3_INGEST_CLIENT3 = "data/1_first_bulk/adacc_act_379859374796069.csv"
S3_PAGES = "data/3_page_mapping/meta_pages_list.csv"

# ==========================================================
# OUTPUT S3
# ==========================================================
S3_OUTPUT = "data/3_page_mapping/act_379859374796069_with_pages.csv"

# ==========================================================
# S3 CLIENT
# ==========================================================
s3 = boto3.client(
    "s3",
    region_name=AWS_DEFAULT_REGION
)

def main():
        
    # ==========================================================
    # LOAD CSV FROM S3
    # ==========================================================
    obj_ads = s3.get_object(
        Bucket=S3_BUCKET,
        Key=S3_INGEST_CLIENT3
    )

    obj_pages = s3.get_object(
        Bucket=S3_BUCKET,
        Key=S3_PAGES
    )

    df_ads = pd.read_csv(obj_ads["Body"])
    df_pages = pd.read_csv(obj_pages["Body"])

    # ==========================================================
    # CLEAN TYPES
    # ==========================================================
    df_ads["page_id"] = df_ads["page_id"].astype(str).str.strip()
    df_pages["page_id"] = df_pages["page_id"].astype(str).str.strip()

    # ==========================================================
    # KEEP ONLY NEEDED PAGE COLS
    # ==========================================================
    df_pages = df_pages[
        [
            "page_id",
            "page_name",
            "page_category",
            "page_description",
            "page_about",
            "page_website",
        ]
    ].drop_duplicates(subset=["page_id"])

    # ==========================================================
    # LEFT JOIN
    # ==========================================================
    df = df_ads.merge(
        df_pages,
        on="page_id",
        how="left"
    )

    # PAGE MATCH FLAGS
    # Normalized Unmatched Page Columns as Null.  And Flagged Has or Not FB Page
    df["has_facebook_page"] = df["page_id"].notna() & df["page_name"].notna()

    df["page_match_status"] = df["has_facebook_page"].map(
        {True: "matched", False: "unmatched"}
    )
    # ==========================================================
    # COLUMN ORDER
    # ==========================================================
    final_cols = [
        "ad_account_id",
        "ad_account_name",
        "ad_account_status",

        "campaign_id",
        "campaign_name",
        "campaign_status",
        "campaign_objective",
        "campaign_start_date",
        "campaign_end_date",

        "adset_id",
        "adset_name",
        "adset_status",
        "optimization_goal",
        "age_min",
        "age_max",
        "genders",
        "countries",
        "interests",
        "behaviors",

        "ad_id",
        "ad_name",
        "ad_status",

        "creative_id",
        "ad_title",
        "creative_name",
        "ad_body",

        "page_id",
        "page_name",
        "page_category",
        "page_description",
        "page_about",
        "page_website",
        "has_facebook_page",
        "page_match_status",

        "creative_image_url",
        "creative_thumbnail_url",
        "creative_cta_type",
        "creative_cta_link",
        "creative_cta_link_caption",

        # 
        "creative_video_id",
        "creative_video_title",
        "creative_video_url",
        "creative_video_thumbnail",
        "creative_image2_url",
        "ig_media_type",
        "ig_image_url",
        "ig_video_url",
        "ig_thumbnail_url",


        "date_start",
        "date_stop",

        "spend",
        "result_type",
        "results",
        "cost_per_results",
        "leads",
        "cost_per_lead",

    ]

    # keep only existing columns safely
    final_cols = [c for c in final_cols if c in df.columns]

    df = df[final_cols]

    # ==========================================================
    # SAVE TO S3
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
    matched = df["page_name"].notna().sum()
    unmatched = df["page_name"].isna().sum()

    print("Rows:", len(df))
    print("Matched page_id:", matched)
    print("Unmatched page_id:", unmatched)
    print("Uploaded:", S3_OUTPUT)


if __name__ == "__main__":
    main()