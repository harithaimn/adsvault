import os
import requests
import pandas as pd
import boto3
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()

# ==========================================================
# ENV
# ==========================================================
ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
S3_BUCKET = os.getenv("S3_BUCKET")
AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION")

BUSINESS_ID = os.getenv("BUSINESS_ID") # INVOKE Meta Business ID
GRAPH_VERSION = "v24.0"

BASE_URL = f"https://graph.facebook.com/{GRAPH_VERSION}"

# ==========================================================
# S3 PATH
# ==========================================================
S3_OUTPUT = "data/3_page_mapping/meta_pages_list.csv"

# ==========================================================
# S3 CLIENT
# ==========================================================
s3 = boto3.client(
    "s3",
    region_name=AWS_DEFAULT_REGION
)


def main():
        
    # ==========================================================
    # 1. GET BUSINESS METADATA
    # ==========================================================
    biz_res = requests.get(
        f"{BASE_URL}/{BUSINESS_ID}",
        params={
            "fields": "name,vertical",
            "access_token": ACCESS_TOKEN
        },
        timeout=30
    )

    biz_res.raise_for_status()
    biz = biz_res.json()


    # =========================
    # 2. Helper: paginate pages
    # =========================
    def fetch_pages(edge):
        url = f"{BASE_URL}/{BUSINESS_ID}/{edge}"

        params = {
            "fields": "id,name,category,description,about,website",
            "limit": 100,
            "access_token": ACCESS_TOKEN
        }

        rows = []

        while url:
            r = requests.get(url, params=params)
            r.raise_for_status()

            data = r.json()

            rows.extend(data.get("data", []))

            url = data.get("paging", {}).get("next")
            params = {}  # important

        return rows

    # =========================
    # 3. Fetch both
    # =========================
    owned_pages = fetch_pages("owned_pages")
    client_pages = fetch_pages("client_pages")

    all_pages = [
        ("owned", p) for p in owned_pages
    ] + [
        ("client", p) for p in client_pages
    ]

    # =========================
    # 4. Flatten
    # =========================
    rows = []

    for source, p in tqdm(all_pages, desc="Processing pages", unit="page"):
        rows.append({
            "business_id": BUSINESS_ID,
            "business_name": biz.get("name"),
            "business_vertical": biz.get("vertical"),
            "source": source,  # owned vs client

            "page_id": p.get("id"),
            "page_name": p.get("name"),
            "page_category": p.get("category"),
            "page_description": p.get("description"),
            "page_about": p.get("about"),
            "page_website": p.get("website"),
        })

    df = pd.DataFrame(rows)

    # ==========================================================
    # 5. CLEAN
    # ==========================================================
    df = df.drop_duplicates(subset=["page_id"]).reset_index(drop=True)

    # ==========================================================
    # 6. SAVE TO S3
    # ==========================================================
    csv_bytes = df.to_csv(index=False).encode("utf-8")

    s3.put_object(
        Bucket=S3_BUCKET,
        Key=S3_OUTPUT,
        Body=csv_bytes,
    )

    print("Rows:", len(df))
    print("Uploaded:", S3_OUTPUT)


if __name__ == "__main__":
    main()