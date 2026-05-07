# =========================
# _04_master_industry_classification.py -- Run once only, it will be a master for all ads accounts ads. Meaning, just map it with page_id.
# =========================
# pip install pandas python-dotenv openai

# =========================
# IMPORTS
# =========================

import os
import re
import pandas as pd
import boto3
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# ==========================================================
# ENV
# ==========================================================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
S3_BUCKET = os.getenv("S3_BUCKET")
AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION")

client = OpenAI(api_key=OPENAI_API_KEY)

#MODEL = "gpt-5-nano" # Cheapest - # Input: $0.05  # Cached input: $0.005   # Output: $0.40
MODEL = "gpt-5.4-nano" 
# # =========================
# # PATH
# # =========================

# BASE_DIR = os.path.dirname(__file__)
# DATA_DIR = os.path.join(BASE_DIR, "..", "data_ind_class")

# #LABELED_PATH = os.path.join(DATA_DIR, "labelled.csv")  # Unused since zero-shot no need to labelled. 
# UNLABELED_PATH = os.path.join(DATA_DIR, "unlabelled.csv")
# OUTPUT_PATH = os.path.join(DATA_DIR, "predicted.csv")

# ==========================================================
# S3 PATH
# ==========================================================
S3_INPUT = "data/3_page_mapping/meta_pages_list.csv"
S3_OUTPUT = "data/4_industry_classification/page_industry_master.csv"

# ==========================================================
# S3 CLIENT
# ==========================================================
s3 = boto3.client(
    "s3",
    region_name=AWS_DEFAULT_REGION
)


# =========================
# LABELS
# =========================
LABELS = [
    "Advertising & Communications",
    "Agriculture & Forestry/Wildlife",
    "Automotive",
    "Beauty & Body Care",
    "Consumer Services",
    "Education",
    "FMCG",
    "Fashion & Lifestyle",
    "Finance & Insurance",
    "Food & Beverages",
    "Healthcare & Life Sciences",
    "Information, Tech & Telecommunications",
    "Interior Design & Construction",
    "Leisure, Tourism & Travel",
    "Logistics & Transportation",
    "Manufacturing & Production",
    "Media & Entertainment",
    "Government",
    "Politician",
    "NGOs",
    "Natural Resources & Energy",
    "Property & Real Estate"
]

# # =========================
# # LOAD CSV
# # =========================
# def load_csv(path):
#     df = pd.read_csv(path)
#     print(f"Loaded {len(df)} rows from {path}")
#     return df

# ==========================================================
# LOAD FROM S3
# ==========================================================
obj = s3.get_object(
    Bucket=S3_BUCKET,
    Key=S3_INPUT
)

df = pd.read_csv(
    obj["Body"],
    dtype={"page_id": "string"}
)

df["page_id"] = (
    df["page_id"]
    .astype("string")
    .str.strip()
    .str.replace(r"\.0$", "", regex=True)
)

print("Loaded:", len(df))


# # =========================
# BUILD INPUT TEXT
# =========================
def build_text(row):
    parts = []

    for col in [
        "page_category",
        "page_name",
        "page_description",
        "page_about",
        "page_website"
    ]:
        val = row.get(col)

        if pd.notna(val) and str(val).strip():
            parts.append(str(val))

    return " ".join(parts).lower()

# # What's this for? Oh, it's for below. 
# def match(pattern, text):
#     return re.search(pattern, text)


""" Robust rule-based """
def rule_based(row):
    text = build_text(row)

    if not text:
        return None, None

    # custom override
    if re.search(r"\b(adnexio|decoris|meniaga|invoke)\b", text):
        return "Information, Tech & Telecommunications", 1.0

    # # high precision
    # if re.search(r"\b(ngo|non[- ]?government|government|netizen|public|rakyat|community|charity|selangor|foundation|pertubuhan|kebajikan|politics|political|politician|non profit|non-profit|nonprofit)\b", text):
    #     return "NGOs", 1.0

    # =========================
    # GOVERNMENT (FIRST)
    # =========================
    if re.search(r"\b(government|kerajaan|ministry|kementerian|jabatan)\b", text):
        return "Government", 1.0 # 1.0

    if re.search(r"\b(politics|political|politician|Politician|Political Candidate)\b", text):
        return "Politician", 1.0 # 1.0

    # =========================
    # NGOs (SECOND)
    # =========================
    if re.search(r"\b(Ayuh Malaysia|ngo|non[- ]?government|non profit|non-profit|nonprofit|charity|foundation|netizen|rakyat|community|pertubuhan|kebajikan|community organization|volunteer)\b", text):
        return "NGOs", 1.0 # 1.0

    if re.search(r"\b(clinic|hospital|medical|doctor|pharmacy|dentist|health|wellness|supplement|vitamin)\b", text):
        return "Healthcare & Life Sciences", 1.0

    if re.search(r"\b(finance|financial|insurance|takaful|investment|wealth|loan|credit)\b", text):
        return "Finance & Insurance", 0.9

    if re.search(r"\b(property|real estate|hartanah|developer|condo|apartment|realty)\b", text):
        return "Property & Real Estate", 1.0

    if re.search(r"\b(auto|car|motor|vehicle|dealership|4s|tuning)\b", text):
        return "Automotive", 1.0

    if re.search(r"\b(logistic|freight|cargo|shipping|courier|delivery|fleet)\b", text):
        return "Logistics & Transportation", 1.0

    if re.search(r"\b(energy|solar|oil|gas|power|charging)\b", text):
        return "Natural Resources & Energy", 1.0

    if re.search(r"\b(software|technology|digital|app|platform|system|wifi|data|ai|cloud|e commerce|e-commerce)\b", text):
        return "Information, Tech & Telecommunications", 0.9

    if re.search(r"\b(education|school|tuition|learning|training|university|kindergarten|course)\b", text):
        return "Education", 1.0

    # mid signal
    if re.search(r"\b(food|restaurant|cafe|kopi|bakery|pizza|steak|dim sum|coffee|beverage)\b", text):
        return "Food & Beverages", 1.0

    if re.search(r"\b(grocery|supermarket|organic|snack|consumer product)\b", text):
        return "FMCG", 1.0 #  0.9

    if re.search(r"\b(beauty|skincare|cosmetic|spa|salon|aesthetic|perfume|fragrance)\b", text):
        return "Beauty & Body Care", 1.0

    if re.search(r"\b(clothing|fashion|apparel|jewellery|boutique|wear|hijab)\b", text):
        return "Fashion & Lifestyle", 1.0

    if re.search(r"\b(construction|contractor|interior|renovation|furniture|lighting|kitchen|bathroom|home improvement)\b", text):
        return "Interior Design & Construction", 1.0

    if re.search(r"\b(manufacturing|factory|production|wholesale|supplier|industrial)\b", text):
        return "Manufacturing & Production", 0.9 #  0.9

    if re.search(r"\b(farm|agriculture|livestock|fishery|plantation)\b", text):
        return "Agriculture & Forestry/Wildlife", 0.9 #  0.9

    if re.search(r"\b(travel|tour|hotel|lodging|agency|trip|booking)\b", text):
        return "Leisure, Tourism & Travel", 1.0

    if re.search(r"\b(media|production|film|entertainment|creator|streaming|music)\b", text):
        return "Media & Entertainment", 0.9

    if re.search(r"\b(advertising|marketing|branding|pr|relations|agency)\b", text):
        return "Advertising & Communications", 0.9

    # fallback
    if re.search(r"\b(service|cleaning|repair|consultant|advisor|printing|maintenance)\b", text):
        return "Consumer Services", 0.7

    return None, None


# =========================
# OPENAI CLASSIFIER
# =========================
# def classify_text(text):
def classify_text(row):
    prompt = f"""
You are a strict industry classifier.

Classify the company into EXACTLY ONE of the following industries:

{chr(10).join(LABELS)}

Instructions (must follow):

1. USE ALL FIELDS TOGETHER:
   - Do NOT blindly trust page_category
   - Cross-check with page_name, description, and about
   - If page_category is generic (e.g. "community", "local business"), IGNORE it

2. DECISION LOGIC:
   - Use the MOST SPECIFIC and CLEAR signal across all fields
   - Prefer concrete business activity over generic labels
   - If conflict:
       → description/about > page_category > page_name

3. DISAMBIGUATION:
   - Restaurant / cafe → Food & Beverages
   - Packaged food / brand → FMCG
   - Property selling → Property & Real Estate
   - Renovation / interior → Interior Design & Construction
   - Software / digital / platform → Information, Tech & Telecommunications
   - NGO / charity → NGOs
   - Government / ministry → Government
   - Politician / political → Politician

4. OUTPUT:
   - EXACTLY one label
   - No explanation

Input:
{{
page_category: {row.get("page_category","")}
page_name: {row.get("page_name","")}
description: {row.get("page_description","")}
about: {row.get("page_about","")}
website: {row.get("page_website","")}
}}
"""
    
    label = None

    for _ in range(3):
        try:
            response = client.responses.create(
                model=MODEL,
                temperature=0,
                input=prompt
            )

            #label = response.output_text.strip()
            label = response.output[0].content[0].text.strip()

            # normalize
            label = label.replace(".", "").strip()

            # hard match fallback
            for l in LABELS:
                if l.lower() in label.lower():
                    label = l
                    break
            break
        except:
            continue

    # if label is None:
    #     return "Unknown", 0.0

    # if label not in LABELS:
    #     return "Unknown", 0.0
    if label is None or label not in LABELS:
        return "Unknown", 0.0

    return label, 0.9

# → description/about > page_name > page_category

# # =========================
# # APPLY TO DATAFRAME
# # =========================
# def classify_dataframe(df):
#     industries = []
#     scores = []

#     for _, row in df.iterrows():

#         # 1. rule-based
#         label, score = rule_based(row)

#         # 2. fallback to LLM
#         #if label is None:
#         if label is None or score < 1.0:
        
#             #text = build_text(row)
#             #label, score = classify_text(text)
#             label, score = classify_text(row)

#         industries.append(label)
#         scores.append(score)

#     df["predicted_industry"] = industries
#     df["score"] = scores
#     return df
# ==========================================================
# APPLY
# ==========================================================
industries = []
scores = []

for _, row in df.iterrows():

    label, score = rule_based(row)

    if label is None:
        label, score = classify_text(row)

    industries.append(label)
    scores.append(score)

df["predicted_industry"] = industries
df["score"] = scores

# # =========================
# # EXAMPLE USAGE
# # =========================
# if __name__ == "__main__":

#     # -- LOAD UNLABELED DATA
#     df = load_csv(UNLABELED_PATH)

#     # -- CLASSIFY --
#     df = classify_dataframe(df)

#     # -- SAVE --
#     df.to_csv(OUTPUT_PATH, index=False)

#     print(df[["page_name", "predicted_industry", "score"]])

# ==========================================================
# SAVE TO S3
# ==========================================================
csv_bytes = df.to_csv(index=False).encode("utf-8")

s3.put_object(
    Bucket=S3_BUCKET,
    Key=S3_OUTPUT,
    Body=csv_bytes
)

print("Uploaded:", S3_OUTPUT)
print(df[["page_name", "predicted_industry", "score"]].head())