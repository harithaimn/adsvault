# core/_04.2_industry_class_nonpaged_ads.py
# Fill industry for non-facebook-page ads using:
# 1) rule-based
# 2) batched LLM fallback
# 3) deduplicated proxy rows first

import os
import re
import math
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

MODEL = "gpt-5.4-nano"

# ==========================================================
# INPUT / OUTPUT
# ==========================================================
S3_INPUT = "data/4_industry_classification/act_379859374796069_with_pages_industry.csv"
S3_OUTPUT = "data/4_industry_classification/act_379859374796069_with_pages_final_industry.csv"

# ==========================================================
# SETTINGS
# ==========================================================
BATCH_SIZE = 25

# ==========================================================
# S3 CLIENT
# ==========================================================
s3 = boto3.client(
    "s3",
    region_name=AWS_DEFAULT_REGION
)

# ==========================================================
# LABELS
# ==========================================================
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

# ==========================================================
# LOAD
# ==========================================================
obj = s3.get_object(
    Bucket=S3_BUCKET,
    Key=S3_INPUT
)

df = pd.read_csv(obj["Body"])

print("Loaded:", len(df))

# ==========================================================
# TARGET ONLY NON PAGE ADS
# ==========================================================
mask = df["has_facebook_page"] == False
target = df.loc[mask].copy()

print("Need classify:", len(target))


# ==========================================================
# BUILD TEXT
# ==========================================================
def build_text(row):
    parts = []

    for col in [
        "ad_body",
        "creative_name",
        "ad_name",
        "ad_title",
        "interests",
        "behaviors",
        "campaign_name",
        "adset_name",
    ]:
        val = row.get(col)

        if pd.notna(val) and str(val).strip():
            parts.append(str(val))

    return " ".join(parts).lower()


# ==========================================================
# RULE BASED
# ==========================================================
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

# ==========================================================
# PROXY KEY (dedupe repeated rows)
# ==========================================================
target["proxy_key"] = (
    target["campaign_name"].fillna("") + "|" +
    target["ad_body"].fillna("")
)

# ==========================================================
# BATCH LLM
# ==========================================================
def classify_batch(chunk):
    rows_txt = []

    for i, (_, row) in enumerate(chunk.iterrows(), start=1):
        rows_txt.append(
            f"""{i}
ad_body: {row.get("ad_body","")}
creative_name: {row.get("creative_name","")}
ad_title: {row.get("ad_title","")}
interests: {row.get("interests","")}
behaviors: {row.get("behaviors","")}
campaign_name: {row.get("campaign_name","")}
"""
        )

    prompt = f"""
Classify each item into EXACTLY ONE label from:

{chr(10).join(LABELS)}

Return ONLY lines in this format:
1|Label
2|Label
3|Label

Items:
{chr(10).join(rows_txt)}
"""

    try:
        r = client.responses.create(
            model=MODEL,
            temperature=0,
            input=prompt
        )

        txt = r.output[0].content[0].text.strip()
        return txt

    except:
        return ""


def parse_result(txt):
    out = {}

    for line in txt.splitlines():
        if "|" not in line:
            continue

        left, right = line.split("|", 1)

        left = left.strip()
        label = right.strip()

        if left.isdigit():
            idx = int(left)

            final_label = "Unknown"

            for x in LABELS:
                if x.lower() in label.lower():
                    final_label = x
                    break

            out[idx] = final_label

    return out


# ==========================================================
# RULE BASED FIRST
# ==========================================================
labels = []
scores = []

for _, row in target.iterrows():
    label, score = rule_based(row)
    labels.append(label)
    scores.append(score)

target["predicted_industry"] = labels
target["score"] = scores

# ==========================================================
# LLM ONLY UNRESOLVED
# ==========================================================
need_llm = target[target["predicted_industry"].isna()].copy()

print("Need LLM:", len(need_llm))

n = len(need_llm)
num_batches = math.ceil(n / BATCH_SIZE)

for b in range(num_batches):
    start = b * BATCH_SIZE
    end = start + BATCH_SIZE

    chunk = need_llm.iloc[start:end]

    print(f"Batch {b+1}/{num_batches}")

    raw = classify_batch(chunk)
    parsed = parse_result(raw)

    for i, idx in enumerate(chunk.index, start=1):
        label = parsed.get(i, "Unknown")
        score = 0.9 if label != "Unknown" else 0.0

        target.loc[idx, "predicted_industry"] = label
        target.loc[idx, "score"] = score

# ==========================================================
# WRITE BACK (same row order preserved)
# ==========================================================
df.loc[target.index, "predicted_industry"] = target["predicted_industry"]
df.loc[target.index, "score"] = target["score"]
df.loc[target.index, "industry_source"] = "ad_proxy"

# ==========================================================
# SAVE
# ==========================================================
csv_bytes = df.to_csv(index=False).encode("utf-8")

s3.put_object(
    Bucket=S3_BUCKET,
    Key=S3_OUTPUT,
    Body=csv_bytes
)

print("Filled rows:", len(target))
print("Uploaded:", S3_OUTPUT)