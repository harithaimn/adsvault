# core/_02_data_cleaning.py

from __future__ import annotations

import os
import re
import requests
import boto3
import ast
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
BASE_URL = "https://graph.facebook.com/v24.0"

S3_BUCKET = os.getenv("S3_BUCKET")
AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION")

# ==========================================================
# S3 PATH
# ==========================================================
#S3_INPUT = "data/4_industry_classification/act_379859374796069_with_pages_final_industry.csv"

S3_INPUT = "data/2_benchmark/act_379859374796069_with_pages_final_industry_benchmarked.csv"
S3_OUTPUT = "data/5_data_cleaning/act_379859374796069_with_pages_final_industry_benchmarked_clean.csv"

# ==========================================================
# S3 CLIENT
# ==========================================================
s3 = boto3.client(
    "s3",
    region_name=os.getenv("AWS_DEFAULT_REGION")
)

# =====================================================
# STATIC MAPS
# =====================================================

# I think i do result_type_map AFTER i've done Result Type Benchmarking.
RESULT_TYPE_MAP = {
    "reach": "Reach",
    "impressions": "Impressions",
    "actions:link_click": "Link Clicks",
    #"actions:landing_page_view": "Landing Page View",
    "actions:omni_landing_page_view": "Landing Page View",
    
    #"actions:onsite_conversion.messaging_conversation_started": "Message Started",
    "actions:onsite_conversion.messaging_conversation_started_7d": "Message Conversation Started",
    "actions:video_view": "Video Views",
    
    #"video_2_sec_continuous_video_views": "Video Views",
    #"actions:video_thruplay": "ThruPlay",
    "video_thruplay_watched_actions": "Video ThruPlay",

    "actions:post_engagement": "Post Engagement",
    "actions:like": "Likes",
    "estimated_ad_recallers": "Ad Recall",
    "actions:add_to_cart": "Add To Cart",
    
    "actions:add_payment_info": "Add Payment Info",
    
    "actions:initiate_checkout": "Initiate Checkout",
    
    "actions:view_content": "View Content",
    
    #"actions:offsite_conversion.purchase": "Purchase",
    "actions:onsite_conversion.purchase": "Purchase",

    "actions:onsite_conversion.lead_grouped": "Lead Grouped",

    "actions:lead": "Leads",


    "actions:offsite_conversion.fb_pixel_purchase": "FB Pixel Purchase",

    "actions:offsite_conversion.fb_pixel_lead": "FB Pixel Lead",
    
    "actions:offsite_conversion.fb_pixel_complete_registration": "FB Pixel Complete Registration",

    "actions:offsite_conversion.fb_pixel_initiate_checkout": "FB Pixel Initiate Checkout",

    "actions:offsite_conversion.fb_pixel_view_content": "FB Pixel View Content",


    "profile_visit_view": "Profile Visit View",
    "page_visit_view": "Page Visit",

    "total_profile_visits": "Total Profile Visit",
    #"actions:mobile_app_install": "App Install",
    #"actions:subscribe_total": "Subscribe",

    "actions:submit_application_total": "Submit Application Total",

    "conversions:submit_application_website": "Submit Application Website",
    #"offsite_conversion.custom": "Custom Conversion",

    "conversion_leads:conversion_lead": "Conversion Lead",
    "conversions:customize_product_website": "Customize Product Website",

}

CTA_MAP = {
    "BOOK_TRAVEL": "Book Now",
    "LEARN_MORE": "Learn More",
    "LIKE_PAGE": "Like Page",
    "NO_BUTTON": "No Button",
    "ORDER_NOW": "Order Now",
    "SEE_MENU": "See Menu",
    "SIGN_UP": "Sign Up",
    "VIEW_INSTAGRAM_PROFILE": "View Instagram",
    "WHATSAPP_MESSAGE": "WhatsApp",
}

# ADD THIS STATIC MAP near other maps
OPTIMIZATION_GOAL_MAP = {
    "POST_ENGAGEMENT": "Post Engagement",
    "CONVERSATIONS": "Conversations",
    "LINK_CLICKS": "Link Clicks",
    "REACH": "Reach",
    "LEAD_GENERATION": "Lead Generation",
    "PROFILE_AND_PAGE_ENGAGEMENT": "Profile & Page Engagement",
    "LANDING_PAGE_VIEWS": "Landing Page Views",
    "OFFSITE_CONVERSIONS": "Offsite Conversions",
    "PROFILE_VISIT": "Profile Visit",
    "PAGE_LIKES": "Page Likes",
    "VALUE": "Value",
    "IMPRESSIONS": "Impressions",
    "AD_RECALL_LIFT": "Ad Recall Lift",
    "QUALITY_LEAD": "Quality Lead",
    "THRUPLAY": "ThruPlay",
    "MESSAGING_PURCHASE_CONVERSION": "Messaging Purchase Conversion",
    "VISIT_INSTAGRAM_PROFILE": "Visit Instagram Profile",
}


# =====================================================
# HELPERS
# =====================================================

def _first_valid(*vals):
    for v in vals:
        if pd.notna(v) and str(v).strip() != "":
            return v
    return None


def _normalize_text(x):
    if pd.isna(x):
        return None
    return str(x).strip()


def _clean_list_like(x):
    if pd.isna(x):
        return ""

    txt = str(x).strip()

    if txt in ("", "[]", "nan", "None"):
        return ""

    try:
        vals = ast.literal_eval(txt)

        if isinstance(vals, list):
            vals = [str(v).strip() for v in vals if str(v).strip()]
            return ", ".join(vals)

    except:
        pass

    return txt

def _clean_genders(x):
    txt = _clean_list_like(x)

    mapping = {
        "0": "Both",
        "1": "Male",
        "2": "Female"
    }

    vals = [mapping.get(v.strip(), v.strip()) for v in txt.split(",") if v.strip()]
    return ", ".join(vals)

# =====================================================
# CUSTOM RESULT TYPE MAPPER
# ====================================================
def extract_custom_conversion_id(result_type):
    if not isinstance(result_type, str):
        return None

    m = re.match(r"actions:offsite_conversion\.custom\.(\d+)", result_type)
    return m.group(1) if m else None


def fetch_custom_conversion_name(conv_id):
    url = f"{BASE_URL}/{conv_id}"

    params = {
        "fields": "id,name",
        "access_token": ACCESS_TOKEN
    }

    try:
        r = requests.get(url, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
        return data.get("name")
    except:
        return None
    

def apply_custom_result_type_mapping(df):
    if "result_type" not in df.columns:
        return df

    # unique actual values in dataframe
    vals = df["result_type"].dropna().unique().tolist()

    custom_vals = [
        x for x in vals
        if isinstance(x, str)
        and x.startswith("actions:offsite_conversion.custom.")
    ]

    mapping = {}

    for raw in custom_vals:
        conv_id = extract_custom_conversion_id(raw)

        if conv_id:
            name = fetch_custom_conversion_name(conv_id)

            if name:
                mapping[raw] = name
            else:
                mapping[raw] = "Custom Conversion"

    #df["result_type_raw"] = df["result_type"]
    if "result_type_raw" not in df.columns:
        df["result_type_raw"] = df["result_type"]

    df["result_type"] = df["result_type"].replace(mapping)

    return df


""" Later """
# def _objective_norm(campaign_name, campaign_objective):
#     txt = str(campaign_name).lower() if pd.notna(campaign_name) else ""

#     if re.search(r"\b(whatsapp|wa messaging|messaging|wa)\b", txt):
#         return "Messaging"

#     if re.search(r"\b(leads?|lead gen|leadgen|lead)\b", txt):
#         return "Leads"

#     if re.search(r"\b(traffic|click|visit|traf)\b", txt):
#         return "Traffic"

#     if re.search(r"\b(engagement|eng)\b", txt):
#         return "Engagement"

#     if re.search(r"\b(awareness|brand awareness)\b", txt):
#         return "Awareness"

#     if re.search(r"\b(sales|conversion)\b", txt):
#         return "Sales"

#     fallback = {
#         "OUTCOME_AWARENESS": "Awareness",
#         "OUTCOME_ENGAGEMENT": "Engagement",
#         "OUTCOME_LEADS": "Leads",
#         "OUTCOME_TRAFFIC": "Traffic",
#         "OUTCOME_SALES": "Sales",
#     }

#     return fallback.get(campaign_objective, "Other")

# =====================================================
# MEDIA (Change this to detect <ad_id> through S3)
# =====================================================

# def _detect_ad_type(row):
#     if pd.notna(row.get("creative_video_url")) and str(row.get("creative_video_url")).strip():
#         return "Video"

#     if pd.notna(row.get("creative_carousel_default_url")) and str(
#         row.get("creative_carousel_default_url")
#     ).strip():
#         return "Carousel"

#     return "Static"

def _detect_ad_type(row):
    if pd.notna(row.get("creative_video_url")) and str(row.get("creative_video_url")).strip():
        return "Video"

    if pd.notna(row.get("creative_image_url")) and str(row.get("creative_image_url")).strip():
        return "Image"

    if pd.notna(row.get("ig_image_url")) and str(row.get("ig_image_url")).strip():
        return "Image"

    return "Static"



# # This will need not be choosing from the CSV.
# # I've stored all the ads images in S3.
# def _choose_image_source(row):
#     """
#     Priority:
#     1 main image
#     2 fallback image2
#     3 carousel
#     4 video thumbnail
#     5 ig image
#     6 generic thumbnail
#     """
#     return _first_valid(
#         row.get("creative_image_url"),
#         row.get("creative_image2_url"),
#         row.get("creative_carousel_default_url"),
#         #row.get("creative_video_thumbnail"),
#         row.get("ig_image_url"),
#         row.get("creative_thumbnail_url"),
#     )

def _choose_media_s3_key(row):
    ad_id = str(row.get("ad_id", "")).strip()
    ad_account_id = str(row.get("ad_account_id", "")).strip()

    prefix = f"data/ads_images_videos/{ad_account_id}"

    if pd.notna(row.get("creative_video_url")) and str(row.get("creative_video_url")).strip():
        return f"{prefix}/videos/{ad_id}.mp4"

    if pd.notna(row.get("creative_image_url")) and str(row.get("creative_image_url")).strip():
        return f"{prefix}/images/{ad_id}.jpg"

    if pd.notna(row.get("creative_image2_url")) and str(row.get("creative_image2_url")).strip():
        return f"{prefix}/images/{ad_id}_alt.jpg"

    if pd.notna(row.get("ig_image_url")) and str(row.get("ig_image_url")).strip():
        return f"{prefix}/images/{ad_id}_ig.jpg"

    if pd.notna(row.get("creative_video_thumbnail")) and str(row.get("creative_video_thumbnail")).strip():
        return f"{prefix}/thumbnails/{ad_id}_video.jpg"

    if pd.notna(row.get("creative_thumbnail_url")) and str(row.get("creative_thumbnail_url")).strip():
        return f"{prefix}/thumbnails/{ad_id}.jpg"

    return None

# =====================================================
# MAIN
# =====================================================

def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # =============================================
    # ID COLUMNS AS STRING
    # =============================================
    id_cols = [
        "ad_account_id",
        "campaign_id",
        "adset_id",
        "ad_id",
        "creative_id",
        "page_id",
        "creative_video_id",
    ]

    for col in id_cols:
        if col in df.columns:
            df[col] = df[col].astype("string")

    # =================================================
    # DATE COLUMNS
    # =================================================
    for col in [
        "date",
        "date_start",
        "date_stop",
        "campaign_start_date",
        "campaign_end_date",
    ]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    if "date" not in df.columns and "date_stop" in df.columns:
        df["date"] = df["date_stop"]

    if "date" in df.columns:
        df["date"] = df["date"].dt.date

    for col in ["date_start", "date_stop", "campaign_start_date", "campaign_end_date"]:
        if col in df.columns:
            df[col] = df[col].dt.date

    # =================================================
    # NUMERIC COLUMNS
    # =================================================
    num_cols = [
        "spend",
        "results",
        "cost_per_results",
        "leads",
        "cost_per_lead",
        "age_min",
        "age_max",
        "score",
    ]

    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # =================================================
    # TEXT NORMALIZATION
    # =================================================
    #obj_cols = df.select_dtypes(include="object").columns
    obj_cols = df.select_dtypes(include=["object", "string"]).columns

    for col in obj_cols:
        df[col] = df[col].apply(_normalize_text)

    # =================================================
    # STANDARD RESULT TYPE
    # =================================================
    if "result_type" in df.columns:
        df = apply_custom_result_type_mapping(df) # Did I placed this right?
        #df["result_type_raw"] = df["result_type"]

        df["result_type"] = (
            df["result_type"]
            .map(RESULT_TYPE_MAP)
            .fillna(df["result_type"])
        )

    # =================================================
    # CTA NORMALIZATION
    # =================================================
    if "creative_cta_type" in df.columns:
        df["creative_cta_type"] = (
            df["creative_cta_type"]
            .map(CTA_MAP)
            .fillna(df["creative_cta_type"])
        )

    # # =================================================
    # # CAMPAIGN OBJECTIVE NORMALIZATION
    # # =================================================
    # if {"campaign_name", "campaign_objective"}.issubset(df.columns):
    #     df["campaign_objective_norm"] = df.apply(
    #         lambda r: _objective_norm(
    #             r["campaign_name"],
    #             r["campaign_objective"],
    #         ),
    #         axis=1,
    #     )

    # ADD inside clean_dataframe()

    # =================================================
    # OPTIMIZATION GOAL NORMALIZATION
    # =================================================
    if "optimization_goal" in df.columns:
        df["optimization_goal"] = (
            df["optimization_goal"]
            .map(OPTIMIZATION_GOAL_MAP)
            .fillna(df["optimization_goal"])
        )

        

    # # =================================================
    # # LEADS OVERRIDE
    # # =================================================
    # if {
    #     #"campaign_objective_norm",
    #     "leads",
    #     "cost_per_lead",
    #     "result_type",
    # }.issubset(df.columns):

    #     mask = (
    #         #(df["campaign_objective_norm"] == "Leads")
    #         (df["leads"].fillna(0) > 0)
    #         & (df["result_type"] != "Submit Application")
    #     )

    #     df.loc[mask, "results"] = df.loc[mask, "leads"]
    #     df.loc[mask, "result_type"] = "Leads"
    #     df.loc[mask, "cost_per_results"] = df.loc[mask, "cost_per_lead"]

    # =================================================
    # TARGETING CLEANUP
    # =================================================
    # for col in [
    #     "interests",
    #     "behaviors",
    #     "countries",
    #     "genders",
    #     "optimization_goal",
    # ]:
    #     if col in df.columns:
    #         df[col] = df[col].apply(_clean_list_like)

    for col in ["interests", "behaviors", "countries"]:
        if col in df.columns:
            df[col] = df[col].apply(_clean_list_like)

    if "genders" in df.columns:
        df["genders"] = df["genders"].apply(_clean_genders)

    if "optimization_goal" in df.columns:
        df["optimization_goal"] = df["optimization_goal"].apply(_clean_list_like)

    # =================================================
    # IMAGE PRIORITY COLUMN
    # =================================================
    image_cols = [
        "creative_image_url",
        "creative_image2_url",
        #"creative_carousel_default_url",
        "creative_video_thumbnail",
        "ig_image_url",
        "creative_thumbnail_url",
    ]

    for col in image_cols:
        if col not in df.columns:
            df[col] = None

    #df["image_source_url"] = df.apply(_choose_image_source, axis=1)
    df["media_s3_key"] = df.apply(_choose_media_s3_key, axis=1)

    # =============================================
    # INDUSTRY RENAME
    # =============================================
    if "predicted_industry" in df.columns:
        df["industry"] = df["predicted_industry"]
        df = df.drop(columns=["predicted_industry"])

    if "score" in df.columns:
        df["industry_score"] = df["score"]
        df = df.drop(columns=["score"])

    # =================================================
    # AD TYPE
    # =================================================
    df["ad_type"] = df.apply(_detect_ad_type, axis=1)

    # =================================================
    # NULL NUMERICS
    # =================================================
    num_existing = df.select_dtypes(include="number").columns
    df[num_existing] = df[num_existing].fillna(0)

    for col in [
        "spend",
        "results",
        "cost_per_results",
        "leads",
        "cost_per_lead",
        #"score",
        "industry_score",
    ]:
        if col in df.columns:
            df[col] = df[col].fillna(0)


    # =================================================
    # DEDUPLICATE
    # =================================================
    subset_cols = [c for c in ["ad_id", "date"] if c in df.columns]

    if subset_cols:
        df = df.drop_duplicates(subset=subset_cols, keep="last")

    # =================================================
    # SORT
    # =================================================
    sort_cols = [c for c in ["date", "campaign_id", "adset_id", "ad_id"] if c in df.columns]

    if sort_cols:
        df = df.sort_values(sort_cols).reset_index(drop=True)

    # =================================================
    # COLUMN ORDER
    # =================================================
    cols = df.columns.tolist()

    def move(col, after=None, before=None):
        if col not in cols:
            return

        cols.remove(col)

        if after and after in cols:
            cols.insert(cols.index(after) + 1, col)
        elif before and before in cols:
            cols.insert(cols.index(before), col)
        else:
            cols.append(col)

    #move("campaign_objective_norm", before="campaign_objective")
    move("result_type_raw", before="result_type")
    move("ad_type", after="creative_name")
    #move("image_source_url", after="ad_type")
    move("media_s3_key", after="ad_type")
    move("industry", before="cost_per_lead")
    move("industry_score", after="industry")

    df = df[cols]

    return df


# =====================================================
# SCRIPT MODE
# =====================================================

if __name__ == "__main__":
    # INPUT = "raw_meta.csv"
    # OUTPUT = "clean_meta.csv"

    # df = pd.read_csv(INPUT)
    # df = clean_dataframe(df)
    # df.to_csv(OUTPUT, index=False)

    # print(f"Saved -> {OUTPUT}")

    # ==========================================================
    # LOAD FROM S3
    # ==========================================================
    obj = s3.get_object(
        Bucket=S3_BUCKET,
        Key=S3_INPUT
    )

    df = pd.read_csv(obj["Body"])

    print("Loaded:", len(df))

    # ==========================================================
    # CLEAN
    # ==========================================================
    df = clean_dataframe(df)

    # ==========================================================
    # SAVE TO S3
    # ==========================================================
    csv_bytes = df.to_csv(index=False).encode("utf-8")

    s3.put_object(
        Bucket=S3_BUCKET,
        Key=S3_OUTPUT,
        Body=csv_bytes
    )

    print("Rows after clean:", len(df))
    print("Uploaded:", S3_OUTPUT)